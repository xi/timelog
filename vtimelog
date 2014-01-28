#!/usr/bin/env python3

#	Parse timelog files, filter the lines and output interesting data
#	Copyright (C) 2014 Tobias Bengfort <tobias.bengfort@gmx.net>
#
#	This program is free software: you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation, either version 3 of the License, or
#	(at your option) any later version.
#
#	This program is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU General Public License for more details.
#
#	You should have received a copy of the GNU General Public License
#	along with this program.  If not, see <http://www.gnu.org/licenses/>.

import argparse
from os.path import expanduser
from datetime import datetime, timedelta

EMPTY_LINE = object()
DT_FORMAT = '%Y-%m-%d %H:%M'


"""parse"""
class ParseError(Exception):
	def __init__(self, line, msg=''):
		self.line = line
		self.msg = msg

	def __str__(self):
		return 'ParseError in line %i: %s' % (self.line, self.msg)


class LazyTuple(tuple):
	def __init__(self, src):
		self._src = tuple(src)
		self._data = []
		for line in self._src:
			self._data.append(None)

	def __len__(self):
		return len(self._src)

	def __iter__(self):
		for i in range(len(self)):
			yield self[i]

	def __getitem__(self, i):
		if self._data[i] is None:
			self._data[i] = self.parse(i)
		return self._data[i]

	def parse(self, i):
		raise NotImplementedError()


class LazyTimelog(LazyTuple):
	def parse(self, i):
		try:
			s = self._src[i]
			if s == '':
				return EMPTY_LINE
			dt, comment = s.split(': ', 1)
			return {
				'dt': datetime.strptime(dt, DT_FORMAT),
				'comment': comment
			}
		except Exception as e:
			raise ParseError(i, str(e))


"""filter"""
def datetime_add(dt, years=0, months=0, weeks=0, days=0, hours=0, minutes=0,
		seconds=0, microseconds=0):
	dt += timedelta(
		weeks=weeks,
		days=days,
		hours=hours,
		minutes=minutes,
		seconds=seconds,
		microseconds=microseconds)

	month = dt.month + months
	div, month = divmod(month - 1, 12)
	month += 1
	year = dt.year + years + div

	return datetime(year, month, dt.day, dt.hour, dt.minute, dt.second,
		dt.microsecond)


def timedelta2str(delta):
	seconds = delta.total_seconds()
	minutes, seconds = divmod(seconds, 60)
	hours, minutes = divmod(minutes, 60)
	return "{: =3}:{:0=2}".format(int(hours), int(minutes))


class Query:
	def __init__(self, timelog):
		self.data = range(len(timelog))
		self.timelog = timelog

	def split(self, dt, after):
		low = 0
		high = len(self.data) - 1

		def get(i):
			return self.timelog[self.data[i]]['dt']

		if (after and get(low) > dt) or (not after and get(high) < dt):
			return

		while high - low > 1:
			new = int((low + high) / 2)
			if get(new) <= dt:
				low = new
			else:
				high = new

		if after:
			self.data = self.data[high:]
		else:
			self.data = self.data[:high]

	def before(self, dt):
		self.split(dt, False)

	def after(self, dt):
		self.split(dt, True)

	def day(self, offset=0):
		now = datetime.now()
		start = datetime(now.year, now.month, now.day)
		self.after(datetime_add(start, days=offset))
		self.before(datetime_add(start, days=offset + 1))

	def week(self, offset=0):
		now = datetime.now()
		start = datetime(now.year, now.month, now.day)
		self.after(datetime_add(start, weeks=offset, days=-now.weekday()))
		self.before(datetime_add(start, weeks=offset + 1, days=-now.weekday()))

	def month(self, offset=0):
		now = datetime.now()
		start = datetime(now.year, now.month, 1)
		self.after(datetime_add(start, months=offset))
		self.before(datetime_add(start, months=offset + 1))

	def year(self, offset=0):
		now = datetime.now()
		start = datetime(now.year, 1, 1)
		self.after(datetime_add(start, years=offset))
		self.before(datetime_add(start, years=offset + 1))

	def all(self):
		return tuple(self.timelog[i] for i in self.data)


"""extract information"""
class Extractor:
	def __init__(self, data):
		self.data = tuple(data)

	def sum(self):
		x = timedelta()
		last = None
		for entry in self.data:
			if last is not None:
				if '**' not in entry['comment']:
					x += entry['dt'] - last['dt']
			last = entry
		return x

	def by_comment(self):
		d = {}
		last = None
		for entry in self.data:
			if last is not None:
				if '**' not in entry['comment']:
					delta = entry['dt'] - last['dt']
					if entry['comment'] in d:
						d[entry['comment']] += delta
					else:
						d[entry['comment']] = delta
			last = entry
		return d


"""Holidays"""
class ExpectedHoursPer:
	WORKDAYS_PER_WEEK = 5
	WORKHOURS_PER_WEEK = 35
	HOLIDAYS_PER_YEAR = 9
	VACATION_DAYS_PER_YEAR = 30

	@classmethod
	def day(cls):
		return int(cls.WORKHOURS_PER_WEEK / cls.WORKDAYS_PER_WEEK)

	@classmethod
	def week(cls):
		return int(cls.WORKHOURS_PER_WEEK)

	@classmethod
	def month(cls):
		return int(cls.year() / 12)

	@classmethod
	def year(cls):
		return int(cls.day() * cls._workdays_per_year())

	@classmethod
	def days(cls, n):
		"""interpolation between day and year"""
		from math import exp
		f = lambda x: 2 / (1 + exp(-x / 7) / exp(-1 / 7)) - 1
		d1 = cls.day()
		d2 = cls.year() / 365
		fn = f(n)
		d = (1-fn) * d1 + fn * d2
		return d * n

	@classmethod
	def _workdays_per_year(cls):
		return ((365 - cls.HOLIDAYS_PER_YEAR) * cls.WORKDAYS_PER_WEEK / 7
			- cls.VACATION_DAYS_PER_YEAR)


"""cli"""
#def timelog2csv():
#	f = open('timelog.txt')
#	l = [line.strip() for line in f.readlines() if line.strip()]
#	data = LazyTimelog(l)
#	f.close()
#
#	def day(entry):
#		return entry['dt'].strftime('%Y-%m-%d')
#
#	x = timedelta()
#	last = None
#	for entry in data:
#		if last is not None:
#			if day(last) != day(entry):
#				print('"%s","%s"' % (day(last), int(x.total_seconds() / 3600)))
#				x = timedelta()
#
#			if '**' not in entry['comment']:
#				x += entry['dt'] - last['dt']
#		last = entry


if __name__ == '__main__':
	parser = argparse.ArgumentParser(
		description='extract interesting data from timelogs')
	parser.add_argument('--file',
		default=expanduser("~/.gtimelog/timelog.txt"))
	parser.add_argument('-d', '--day', nargs='?', const=0, type=int,
		help="show entries from today or DAY days ago")
	parser.add_argument('-w', '--week', nargs='?', const=0, type=int,
		help="show entries from this week or WEEK weeks ago")
	parser.add_argument('-m', '--month', nargs='?', const=0, type=int,
		help="show entries from this month or MONTH months ago")
	parser.add_argument('-y', '--year', nargs='?', const=0, type=int,
		help="show entries from this year or YEAR years ago")
	args = parser.parse_args()

	# load data from file
	f = open(args.file)
	l = [line.strip() for line in f.readlines() if line.strip()]
	data = LazyTimelog(l)
	f.close()

	# filter
	q = Query(data)
	if args.day is not None:
		q.day(offset=-args.day)
		expected = ExpectedHoursPer.day()
	elif args.week is not None:
		q.week(offset=-args.week)
		expected = ExpectedHoursPer.week()
	elif args.month is not None:
		q.month(offset=-args.month)
		expected = ExpectedHoursPer.month()
	elif args.year is not None:
		q.year(offset=-args.year)
		expected = ExpectedHoursPer.year()
	else:
		expected = ExpectedHoursPer.days(
			(data[-1]['dt'] - data[0]['dt']).total_seconds() / 3600 / 24)
	data = q.all()

	ex = Extractor(data)

	# output by comment
	by_comment = ex.by_comment()
	if len(by_comment) > 0:
		l = max(len(k) for k in by_comment.keys())
		for comment, delta in sorted(by_comment.items(), key=lambda a: a[1]):
			print(comment + (l + 1 - len(comment)) * ' ' + timedelta2str(delta))
		print()

	# output total workhours
	done = int(ex.sum().total_seconds() / 3600)
	print("Total workhours done: %i (%i extra)" % (done, done - expected))
