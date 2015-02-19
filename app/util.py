import os
import calendar
import uuid as _uuid

from datetime import datetime, timedelta
from collections import namedtuple


def now(as_timestamp=False, in_millis=False):
    """Returns a datetime object with
    the current UTC time. The datetime
    does not include timezone information"""

    time = datetime.utcnow()
    if as_timestamp:
        timestamp = calendar.timegm(time.utctimetuple())
        if in_millis:
            return timestamp * 1000
        return timestamp
    return time


def secret(size=16):
    return os.urandom(size).encode('hex')


def uuid():
    return str(_uuid.uuid4()).replace('-', '')


def enum(*sequential, **kwargs):
    """Define an iterable enum"""
    return namedtuple('Enum', [v for l in [sequential, kwargs.keys()] for v in l], rename=True)(*[v for l in [range(len(sequential)), kwargs.values()] for v in l])
