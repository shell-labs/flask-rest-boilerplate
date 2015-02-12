import types
import re

from restless.fl import FlaskResource
from restless.preparers import FieldsPreparer
from restless.exceptions import BadRequest, NotFound, Unauthorized

# Abstract the exceptions
BadRequest = BadRequest
NotFound = NotFound


class Resource(FlaskResource):
    def __init__(self, api):
        self.api = api
        self.app = api.app
        self.auth = api.auth
        self.user = None

    def is_debug(self):
        return self.app.debug

    def is_authenticated(self):
        if not self.auth:
            return True

        reg = re.compile('^Bearer *([^ ]+) *$')

        authorization = self.request.headers.get('Authorization')
        if not authorization:
            raise BadRequest("invalid_request")

        access_token = reg.findall(authorization)
        if not access_token:
            raise Unauthorized("invalid_client")
        access_token = access_token[0]

        # Get the user
        user = self.auth.from_access_token(access_token)

        if user is None:
            raise Unauthorized("invalid_client")

        self.user = user

        return True


class Api:
    """Provides an abstraction from the rest API framework being used"""

    def __init__(self, app=None, auth=None):
        if app:
            self.init_app(app, auth)

    def init_app(self, app, auth=None):
        self.app = app
        self.auth = auth

    def resource(self, prefix):
        """Decorator to simplify API creation.

        The same rules as in restless apply (see http://restless.readthedocs.org/en/latest/tutorial.html)

        However to define a resource it suffices with using the decorator to specify it

        @api.resource('/api/posts')
        class PostResource:
            aliases = {
                'id': 'id',
                'title': 'title',
                'author': 'user.username',
                'body': 'content',
                'posted_on': 'posted_on',
            }

            def detail(self, pk):
                return Post.objects.get(id=pk)
        """
        def wrapper(cls):
            # Save the original init
            clsinit = getattr(cls, '__init__', lambda self: None)

            # Dirty trick, make the class belong to the type restful.Resource
            cls = type(cls.__name__, (Resource,), dict(cls.__dict__))

            aliases = getattr(cls, 'aliases', None)
            if type(aliases) is types.DictType and len(aliases) > 0:
                cls.preparer = FieldsPreparer(fields=aliases)

            this = self
            def __init__(self, *args, **kwargs):
                super(cls, self).__init__(this)
                clsinit(self, *args, **kwargs)

            cls.__init__ = __init__

            # Add the resource to the API
            cls.add_url_rules(self.app, prefix)

            return cls

        return wrapper
