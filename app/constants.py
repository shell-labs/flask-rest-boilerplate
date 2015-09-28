from __future__ import absolute_import
from __future__ import unicode_literals
from .util import enum

Genders = enum(M='Male', F='Female')
GrantTypes = enum(PASSWORD='password', REFRESH_TOKEN='refresh_token')
ResponseTypes = enum(CODE='code', TOKEN='token')

NOT_MODIFIED = 304
PRECONDITION_REQUIRED = 428
PRECONDITION_FAILED = 412
