from restless.exceptions import HttpError
from .constants import PRECONDITION_FAILED, PRECONDITION_REQUIRED


class PreconditionRequired(HttpError):
    status = PRECONDITION_REQUIRED
    msg = "Precondition required."


class PreconditionFailed(HttpError):
    status = PRECONDITION_FAILED
    msg = "Precondition failed."