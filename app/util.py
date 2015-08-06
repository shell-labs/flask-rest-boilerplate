from __future__ import absolute_import
from __future__ import unicode_literals
import os
import calendar
import uuid as _uuid
import binascii
import urllib
import urlparse

from datetime import datetime, timedelta
from collections import OrderedDict
from six.moves import map
from six.moves import range
from six.moves import zip


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
    return str(binascii.hexlify(os.urandom(size // 2)))


def uuid():
    return str(_uuid.uuid4()).replace('-', '')


class NamedTuple(tuple):
    """
    Defines a NamedTuple (tuple with names for objects) according to the
    definition in the gist https://gist.github.com/bennoleslie/27aeb9065e81199f8af1

    The main difference in this version is that objects that inherit from NamedTuple here
    can be treated as tuples and mappings, therefore the functions dict() and tuple() can
    be invoked on instances. This makes the object particularly useful to be used as constants
    """

    __slots__ = ()

    _fields = None  # Subclass must provide this

    def __new__(_cls, *args, **kwargs):
        if len(args) > len(_cls._fields):
            raise TypeError("__new__ takes {} positional arguments but {} were given".format(len(_cls._fields) + 1, len(args) + 1))

        missing_args = tuple(fld for fld in _cls._fields[len(args):] if fld not in kwargs)
        if len(missing_args):
            raise TypeError("__new__ missing {} required positional arguments".format(len(missing_args)))
        extra_args = tuple(kwargs.pop(fld) for fld in _cls._fields[len(args):] if fld in kwargs)
        if len(kwargs) > 0:
            raise TypeError("__new__ got an unexpected keyword argument '{}'".format(list(kwargs.keys())[0]))

        return tuple.__new__(_cls, tuple(args + extra_args))

    def _make(self, iterable, new=tuple.__new__, len=len):
        'Make a new Bar object from a sequence or iterable'
        cls = self.__class__
        result = new(cls, iterable)
        if len(result) != len(cls._fields):
            raise TypeError('Expected {} arguments, got {}'.format(len(self._fields), len(result)))
        return result

    def __repr__(self):
        'Return a nicely formatted representation string'
        fmt = '(' + ', '.join('%s=%%r' % x for x in self._fields) + ')'
        return self.__class__.__name__ + fmt % self

    def _asdict(self):
        'Return a new OrderedDict which maps field names to their values'
        return OrderedDict(list(zip(self._fields, self)))

    __dict__ = property(_asdict)

    def _replace(_self, **kwds):
        'Return a new Bar object replacing specified fields with new values'
        result = _self._make(list(map(kwds.pop, _self._fields, _self)))
        if kwds:
            raise ValueError('Got unexpected field names: %r' % list(kwds))
        return result

    def __getnewargs__(self):
        'Return self as a plain tuple.  Used by copy and pickle.'
        return tuple(self)

    def __getstate__(self):
        'Exclude the OrderedDict from pickling'
        return None

    def __getattr__(self, field):
        try:
            idx = self._fields.index(field)
        except ValueError:
            raise AttributeError("'{}' NamedTuple has no attribute '{}'".format(self.__class__.__name__, field))

        for i, v in zip(list(range(len(self))), self):
            if i == idx:
                return v

    def __getitem__(self, key):
        try:
            idx = self._fields.index(key)
        except ValueError:
            raise AttributeError("'{}' NamedTuple has no attribute '{}'".format(self.__class__.__name__, key))

        for i, v in zip(list(range(len(self))), self):
            if i == idx:
                return v

    def keys(self):
        return self._fields


def enum(*sequential, **kwargs):
    """Define an iterable enum"""
    class Enum(NamedTuple):
        __slots__ = ()
        _fields = tuple(v for l in [sequential, list(kwargs.keys())] for v in l)

    return Enum(*[v for l in [list(range(len(sequential))), list(kwargs.values())] for v in l])


def build_url(base, query_params={}, fragment={}):
    """Construct a URL based off of base containing all parameters in
    the query portion of base plus any additional parameters.
    Taken from https://github.com/NateFerrero/oauth2lib/blob/master/oauth2lib/utils.py and extended to allow
    paramenters as fragment
    :param base: Base URL
    :type base: str
    ::param query_params: Additional query parameters to include.
    :type query_params: dict
    ::param fragment: Additional parameters to include in the fragment section of the url
    :type fragment: dict
    :rtype: str
    """
    url = urlparse.urlparse(base)
    query_params.update(urlparse.parse_qsl(url.query, True))
    query_params = {k: v for k, v in query_params.iteritems() if v is not None}

    fragment.update(urlparse.parse_qsl(url.fragment, True))
    fragment = {k: v for k, v in fragment.iteritems() if v is not None}

    return urlparse.urlunparse((url.scheme,
                                url.netloc,
                                url.path,
                                url.params,
                                urllib.urlencode(query_params),
                                urllib.urlencode(fragment)))


from flask import request, url_for


def is_safe_url(target):
    """
    A function that ensures that a redirect target will lead to the same server

    A common pattern with form processing is to automatically redirect back to
    the user. There are usually two ways this is done: by inspecting a next URL
    parameter or by looking at the HTTP referrer. Unfortunately you also have to
    make sure that users are not redirected to malicious attacker's pages and
    just to the same host.

    Source: http://flask.pocoo.org/snippets/62/
    """
    ref_url = urlparse.urlparse(request.host_url)
    test_url = urlparse.urlparse(urlparse.urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and \
        ref_url.netloc == test_url.netloc
