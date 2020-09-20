import datetime

# This file is a collection of simple Python convenience functions.

def xor(b1, b2):
    xordict = {True: 1, False: 0}
    return 1 == xordict[b1] + xordict[b2]

def xor_none(v1, v2):
    xordict = {True: 1, False: 0}
    return 1 == xordict[v1 == None] + xordict[v2 == None]

def coalesce(*args):
    """
    This emulates the SQL coalesce function with Python None in analogy to SQL
    null.

    >>> coalesce(None, 'Fred')
    'Fred'
    >>> coalesce(23, 24)
    23
    >>> coalesce(None)
    >>> coalesce(None, None, 1)
    1
    """
    for a in args:
        if a != None:
            return a
    return None

def the_first(d):
    """
    >>> the_first(datetime.date(2015, 5, 6))
    datetime.date(2015, 5, 1)
    """
    return d-datetime.timedelta(d.day-1)

def month_end(year_or_date, month=None):
    if isinstance(year_or_date, int):
        year = year_or_date
        next1 = the_first(datetime.date(year, month, 1)+datetime.timedelta(35))
        return next1-datetime.timedelta(1)
    else:
        assert month == None
        d = year_or_date
        next = d+datetime.timedelta(35-d.day)
        return next-datetime.timedelta(next.day)

def n_months_earlier(d, n):
    """
    >>> n_months_earlier(datetime.date(2015, 5, 1), 2)
    datetime.date(2015, 3, 1)
    >>> n_months_earlier(datetime.date(2015, 5, 1), 6)
    datetime.date(2014, 11, 1)
    >>> n_months_earlier(datetime.date(2015, 5, 1), 8)
    datetime.date(2014, 9, 1)
    >>> n_months_earlier(datetime.date(2015, 5, 1), 12)
    datetime.date(2014, 5, 1)
    >>> n_months_earlier(datetime.date(2015, 5, 1), 24)
    datetime.date(2013, 5, 1)
    >>> n_months_earlier(datetime.date(2015, 5, 1), 5*12)
    datetime.date(2010, 5, 1)
    """
    assert d.day == 1
    if n < 4:
        offset = n*28
    elif n < 8:
        offset = n*29
    elif n < 16:
        offset = n*30
    else:
        years, months = n // 12, n % 12
        years, months = years - 1, months + 12
        offset = 365*years + months*30
    return the_first(d-datetime.timedelta(offset))

def add_business_days(base, n):
    """
    This emulates the Fido SQL add_business_days function for Python datetime.date objects.

    >>> d = datetime.date(2017, 9, 7) # thursday
    >>> add_business_days(d, 1)
    datetime.date(2017, 9, 8)
    >>> add_business_days(d, 2)
    datetime.date(2017, 9, 11)
    >>> add_business_days(d, -3)
    datetime.date(2017, 9, 4)
    >>> add_business_days(d, -4)
    datetime.date(2017, 9, 1)

    >>> d = datetime.date(2017, 9, 2) # saturday
    >>> add_business_days(d, 2)
    datetime.date(2017, 9, 5)
    >>> d = datetime.date(2017, 9, 1) # friday
    >>> add_business_days(d, 2)
    datetime.date(2017, 9, 5)
    """
    weeks, days = n // 5, n % 5
    base = base + datetime.timedelta(weeks*7)
    if days != 0 and base.weekday() >= 5:
        days += (6-base.weekday())
    elif days != 0 and base.weekday() + days >= 5:
        days += 2
    return base + datetime.timedelta(days)

def parse_iso_time(tstr):
    # see also convert_datetime
    if tstr.find('.') >= 0:
        return datetime.datetime.strptime(tstr, "%Y-%m-%dT%H:%M:%S.%f")
    else:
        return datetime.datetime.strptime(tstr, "%Y-%m-%dT%H:%M:%S")

def baseconvert(n, base):
    """
    Convert positive decimal integer n to equivalent in another base (2-36)

    >>> baseconvert(12, 16)
    'C'
    >>> baseconvert(127, 32)
    '3V'
    """

    digits = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'

    n = int(n)
    base = int(base)

    if not 2 <= base <= 36:
        raise ValueError('base must be between 2 & 36')
    if n < 0:
        raise ValueError('n must be zero or positive')

    s = ''
    while 1:
        r = n % base
        s = digits[r] + s
        n = n // base
        if n == 0:
            break

    return s

class Inline:
    def __repr__(self):
        keys = [x for x in dir(self) if not x.startswith('_')]
        values = [f'{k}={repr(getattr(self, k))}' for k in keys]
        return f"{self.__class__.__name__}({', '.join(values)})"

def inline_object(**kwargs):
    r = Inline()
    for k, v in kwargs.items():
        setattr(r, k, v)
    return r
