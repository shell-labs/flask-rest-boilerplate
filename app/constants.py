from __future__ import absolute_import
from __future__ import unicode_literals
from .util import enum

Genders = enum(M='Male', F='Female')
Roles = enum(USER='User', ADMIN='Administrator', APP='Application Owner')

NOT_MODIFIED = 304
PRECONDITION_REQUIRED = 428
PRECONDITION_FAILED = 412