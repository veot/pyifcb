"""
Support for parsing IFCB permanent identifiers (a.k.a., pids).
"""

import re

from functools32 import lru_cache
import pandas as pd

### parsing

# supports time-like regexes e.g., IFCB9_yyyy_YYY_HHMMSS
def timestamp2regex(pattern):
    """
    Convert a special "timestamp" expression into a regex pattern.
    The expression is treated as an ordinary regex except that special
    patterns are used to define groups that match typical patterns that
    are found in timestamps and timestamp-related formats.

    Special patterns that define groups that are supported:

    * ``0-9`` - where n is any number of digits (e.g., ``111``, ``88``) fixed-length
      decimal number
    * ``s`` - any number of ``s``'s indicating milliseconds (e.g., ``sss``)
    * ``yyyy`` - four-digit year
    * ``mm`` - two-digit (left-zero-padded) month
    * ``dd`` - two-digit (left-zero-padded) day of month
    * ``DDD`` - three-digit (left-zero-padded) day of year
    * ``HH`` - two-digit (left-zero-padded) hour of day
    * ``MM`` - two-digit (left-zero-padded) minute of hour
    * ``SS`` - two-digit (left-zero-padded) second of minute
    * ``#`` - any string of digits (non-capturing)
    * ``i`` - an "identifier" (e.g., ``jpg2000``) (non-capturing)
    * ``.ext`` - a file extension
    * ``.`` - a literal dot
    * ``\.`` - a regex dot (matches any character)
    * ``any`` - a regex ``.*``

    Example patterns:

    * ``yyyy-mm-ddTHH:MM:SSZ`` - a UTC ISO8601 timestamp
    * ``yyyyDDD`` - year and day of year

    :Example:

    >>> timestamp2regex('Dyyyymm')
    'D(?P<yyyy>[0-9]{4})(?P<mm>0[1-9]|1[0-2])'

    """
    # FIXME handle unfortunate formats such as
    # - non-zero-padded numbers
    # - full and abbreviated month names
    pattern = re.sub(r'(([0-9])\2*)',r'(?P<n\2>[0-9]+)',pattern) # fixed-length number eg 111 88
    pattern = re.sub(r's+','(?P<sss>[0-9]+)',pattern) # milliseconds
    pattern = re.sub(r'yyyy','(?P<yyyy>[0-9]{4})',pattern) # four-digit year
    pattern = re.sub(r'mm','(?P<mm>0[1-9]|1[0-2])',pattern) # two-digit month
    pattern = re.sub(r'dd','(?P<dd>0[1-9]|[1-2][0-9]|3[0-1])',pattern) # two-digit day of month
    pattern = re.sub(r'DDD','(?P<DDD>[0-3][0-9][0-9])',pattern) # three-digit day of year
    pattern = re.sub(r'HH','(?P<HH>[0-1][0-9]|2[0-3])',pattern) # two-digit hour
    pattern = re.sub(r'MM','(?P<MM>[0-5][0-9])',pattern) # two-digit minute
    pattern = re.sub(r'SS','(?P<SS>[0-5][0-9])',pattern) # two-digit second
    pattern = re.sub(r'#','[0-9]+',pattern) # any string of digits (non-capturing)
    pattern = re.sub(r'i','[a-zA-Z][a-zA-Z0-9_]*',pattern) # an identifier (e.g., jpg2000) (non-capturing)
    pattern = re.sub(r'\.ext',r'(?:.(?P<ext>[a-zA-Z][a-zA-Z0-9_]*))',pattern) # a file extension
    pattern = re.sub(r'\.',r'\.',pattern) # a literal '.'
    pattern = re.sub(r'\\.','.',pattern) # a regex '.'
    pattern = re.sub(r'any','.*',pattern) # a regex .*
    return pattern
    
@lru_cache()
def c(pattern):
    """
    Compile a regex pattern (with caching)

    :param pattern: the pattern
    :returns: the compiled pattern
    """
    return re.compile(pattern)

@lru_cache()
def m(pattern, string):
    """
    Match a pattern against a string and return the
    matching groups. Provides several convenience
    features that differ from ``re.match``:

    * If the pattern does not match the string, or the
      string is None, return a tuple of Nones the length
      of the number of capturing groups.
    * If there is only one pattern, return a single
      value instead of a one-element tuple.

    :param pattern: the pattern (as string)
    :param string: the string to match
    :returns: a value or tuple of captured groups
    """
    def col_or_scalar(o):
        if len(o) == 1:
            return o[0]
        else:
            return o
    def nones(n):
        return col_or_scalar([None for _ in range(n)])
    r = c(pattern)
    n = r.groups
    if string is None:
        return nones(n)
    m = r.match(string)
    if m is None:
        return nones(n)
    return col_or_scalar(tuple(m.groups()))

def parse(pid):
    """
    Parse an IFCB permanent identifier (a.k.a., "pid"). The
    passed-in pid may contain either a pathname prefix or
    a URL prefix, and may include a product identifier and/or
    extension. It can also include a target number.
    The pid syntax is specified elsewhere. Extracted fields
    are returned as a dict.

    :param pid: the pid as a string

    Example pids:

    * ``D20160714T023910_IFCB101``
    * ``IFCB3_2008_013423.adc``
    * ``http://mysite.org/data/D20150321T124431_IFCB103``
    * ``D20160714T023910_IFCB101_00014.png``
    * ``/my/directory/D20160603T002950_IFCB101_blob.zip``

    Fields extracted include:

    * pid - the pid, minus any leading path/URL prefix
    * lid - the pid, minus all prefixes and suffixes
    * namespace - any leading path/URL prefix
    * ts_label - for URL patterns, the time series label
    * year, month, day - the date
    * hour, minute, second - the time
    * instrument - the instrument number
    * timestamp - the complete timestamp
    * timestamp_format - the format specifier of the timestamp
    * schema_version - which revision of the instrument
      (1 for ``IFCB...`` pids, 2 for ``D...`` pids)
    * yearday - the year and day, concatenated
    * target - the target number (if any)
    * extension - the extension, not including the leading ``.``
    * product - the product type identifier, or 'raw' if
      not specified

    :param pid: the pid
    :returns dict: fields extraced from the pid
    """
    pid = c(r'^.*\\').sub('',pid) # strip Windows dirs
    namespace, suffix = m('(.*/)?(.*)',pid)
    ts_label = m('(?:.*/)?(.*)/$',namespace)
    # try v2 identifier pattern
    bin_lid, timestamp, year, month, day, hour, minute, second, instrument, tpe = m(timestamp2regex('(D(yyyymmddTHHMMSS)_IFCB111)(any)'),suffix)
    # try v1 identifier pattern
    if bin_lid is None:
        bin_lid, instrument, timestamp, year, day, hour, minute, second, tpe = m(timestamp2regex('(IFCB1_(yyyy_DDD_HHMMSS))(any)'),suffix)
        schema_version = 1
        timestamp_format = '%Y_%j_%H%M%S'
        yearday = '_'.join([year, day])
    else:
        schema_version = 2
        timestamp_format = '%Y%m%dT%H%M%S'
        yearday = ''.join([year, month, day])
    if bin_lid is None: # syntax error
        raise ValueError('invalid pid: %s' % pid)
    # now parse target, product, and extension (tpe)
    target, product, extension = m(r'(?:_([0-9]+))?(?:_([a-zA-Z][a-zA-Z0-9_]*))?(?:\.([a-zA-Z][a-zA-Z0-9]*))?',tpe)
    if product is None:
        product = 'raw'
    if target is not None:
        lid = '_'.join([bin_lid, target])
    else:
        lid = bin_lid # make sure both are present
    # now del non-desired locals
    del tpe
    # this might actually be an acceptable use of locals()
    return locals()

class Pid(object):
    """
    Represents the permanent identifier of an IFCB bin.
    Provides a dict-like interface for access to the parsed
    fields of a pid.
    """
    def __init__(self, pid, parse=True):
        """
        Construct a Pid object from a string.
        Parsing is optional in case it needs
        to be deferred.

        Pid objects sort by alpha.

        :param pid: the pid
        :param parse: whether to parse
        """
        self.pid = pid
        if parse:
            self.parsed
    def isvalid(self):
        """
        Is this a valid pid?
        """
        try:
            self.parsed
            return True
        except ValueError:
            pass
        return False
    def __cmp__(self, other):
        if self.pid < other.pid:
            return -1
        elif self.pid > other.pid:
            return 1
        else:
            return 0
    @property
    @lru_cache()
    def parsed(self):
        """
        :returns dict: the parsed PID.
        """
        return parse(self.pid)
    @property
    def timestamp(self):
        """
        :returns: the timestamp of the bin as a datetime
        """
        return pd.to_datetime(self.parsed['timestamp'], format=self.parsed['timestamp_format'], utc=True)
    def __getattr__(self, name):
        if name in ['bin_lid', 'lid', 'instrument', 'namespace', 'product', 'target', 'ts_label', 'schema_version']:
            return self.parsed[name]
        else:
            return self.__getattribute__(name)
    def __repr__(self):
        return '<pid %s>' % self.pid
    def __str__(self):
        return self.pid
