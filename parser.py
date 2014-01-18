"""Parse  timelog files, filter the lines and output interesting data"""

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
	return "{}:{:0=2}:{:0=2}".format(int(hours), int(minutes), int(seconds))


class Query:
	def __init__(self, timelog):
		self.data = range(len(timelog))
		self.timelog = timelog

	def split(self, dt, after):
		low = 0
		high = len(self.data) - 1

		def get(i):
			return self.timelog[self.data[i]]['dt']

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
		return (self.timelog[i] for i in self.data)


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


"""Feiertage"""
class ExpectedHoursPer:
	WORKDAYS_PER_WEEK = 5
	HOLIDAYS_PER_YEAR = 9
	VACATION_DAYS_PER_YEAR = 30
	WORKHOURS_PER_WEEK = 35

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
	def _workdays_per_year(cls):
		return ((365 - cls.HOLIDAYS_PER_YEAR) * cls.WORKDAYS_PER_WEEK / 7
			- cls.VACATION_DAYS_PER_YEAR)


"""cli"""
def timelog2csv():
	f = open('timelog.txt')
	l = [line.strip() for line in f.readlines() if line.strip()]
	ll = LazyTimelog(l)
	f.close()

	def day(entry):
		return entry['dt'].strftime('%Y-%m-%d')

	x = timedelta()
	last = None
	for entry in ll:
		if last is not None:
			if day(last) != day(entry):
				print('"%s","%s"' % (day(last), int(x.total_seconds() / 3600)))
				x = timedelta()

			if '**' not in entry['comment']:
				x += entry['dt'] - last['dt']
		last = entry


if __name__ == '__main__':
	"""
	f = open('timelog.txt')
	l = [line.strip() for line in f.readlines() if line.strip()]
	ll = LazyTimelog(l)
	f.close()

	q = Query(ll)
	q.month(offset=-3)

	for line in q.all():
		print(line)

	ex = Extractor(q.all())

	by_comment = ex.by_comment()
	l = max(len(k) for k in by_comment.keys())
	for comment, delta in by_comment.items():
		print(comment + (l + 2 - len(comment)) * ' ' + timedelta2str(delta))
	print(timedelta2str(ex.sum()))

	print(ExpectedHoursPer.month())
	"""
	timelog2csv()
