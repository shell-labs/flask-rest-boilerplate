import types
import re
import functools

from restless.fl import FlaskResource
from restless.preparers import FieldsPreparer
from restless.exceptions import BadRequest, NotFound, Unauthorized

# Abstract the exceptions
BadRequest = BadRequest
NotFound = NotFound
Unauthorized = Unauthorized


class Resource(FlaskResource):
    def __init__(self, api):
        self.api = api
        self.app = api.app
        self.auth = api.auth
        self.user = None
        self.client = None

    def is_debug(self):
        return self.app.debug

    def bubble_exceptions(self):
        return self.app.config.get('TESTING')

    def is_authenticated(self):
        if not self.auth:
            return True

        # Get the method name for the endpoint and request method
        method = self.http_methods.get(self.endpoint).get(self.request.method)

        # If the callback has the attribute public, return true immediately
        callback = getattr(self, method)

        if hasattr(callback, 'public') and callback.public:
            return True

        roles = []
        if hasattr(callback, 'roles'):
            roles = callback.roles

        reg = re.compile('^Bearer *([^ ]+) *$')

        authorization = self.request.headers.get('Authorization')
        if not authorization:
            # TODO: return bad request or unauthorized here?
            return False

        access_token = reg.findall(authorization)
        if not access_token:
            # TODO: return bad request or unauthorized here?
            return False
        access_token = access_token[0]

        # Get the user
        user, client = self.auth.from_access_token(access_token)

        if user is None:
            return False

        # Check user roles
        if not self.auth.validate_user_roles(user, roles):
            return False

        self.user = user
        self.client = client

        return True


class Api:
    """Provides an abstraction from the rest API framework being used"""

    def __init__(self, app=None, auth=None):
        if app:
            self.init_app(app, auth)

    def init_app(self, app, auth=None):
        self.app = app
        self.auth = auth

    def public(self, view):
        """Define the class method as public.

        Otherwise, if auth is defined all methods require
        the user to be authenticated
        """
        view.public = True
        return view

    def grant(self, *roles):
        """Grant method authorization to the specified roles"""
        def view(fn):
            fn.roles = roles
            return fn

        return view

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
            if isinstance(aliases, dict) and len(aliases) > 0:
                cls.preparer = FieldsPreparer(fields=aliases)

            # Rename self for using inside __init__
            api = self

            def __init__(self, *args, **kwargs):
                # Call Resource constructor
                super(cls, self).__init__(api)

                # Initialize the instance
                clsinit(self, *args, **kwargs)

            cls.__init__ = __init__

            # Add the resource to the API
            cls.add_url_rules(self.app, prefix)

            return cls

        return wrapper
