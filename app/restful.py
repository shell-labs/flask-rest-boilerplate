from __future__ import absolute_import
from __future__ import unicode_literals
import types
import re
import functools

from flask import make_response, json
from restless.fl import FlaskResource
from restless.preparers import FieldsPreparer
from restless.exceptions import BadRequest, NotFound, Unauthorized
from .http_errors import PreconditionFailed, PreconditionRequired
from .constants import NOT_MODIFIED
import six

from .cache import etag

# Abstract the exceptions
BadRequest = BadRequest
NotFound = NotFound
Unauthorized = Unauthorized
PreconditionRequired = PreconditionRequired
PreconditionFailed = PreconditionFailed


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

    def prepare(self, data):
        # ``data`` is the object/dict to be exposed.
        # We'll call ``super`` to prep the data, then we'll mask the email.
        prepped = super(Resource, self).prepare(data)

        # Remove empty values from response
        not_null_data = dict()
        for k, v in six.iteritems(prepped):
            if v:
                not_null_data[k] = v

        return not_null_data

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

    def handle(self, endpoint, *args, **kwargs):
        '''
        Overrides method handle of restless to handle etags.
        For now only handles etag for conditional gets (http://fideloper.com/api-etag-conditional-get)
        (with strong etags) and concurrency control (http://fideloper.com/etags-and-optimistic-concurrency-control).
        Based on http://flask.pocoo.org/snippets/95/.
        '''
        local_etag = None

        # First case is the request for a single resource, ex: '/blog/post/1'
        if endpoint == 'detail':
            # See if there is an etag stored from the URI
            local_etag = etag.get_etag(self.request.path)

            if self.request.method in ('PUT', 'DELETE'):
                # for put and delete methods, it must have an if if_match header
                # for concurrency control and to avoid lost updates
                if not self.request.if_match.as_set():
                    raise PreconditionRequired

                # If the stored etag is not the same in the if_match header,
                # then the content has changed and we fail the update with a 412
                if local_etag not in self.request.if_match:
                    raise PreconditionFailed

            elif self.request.method == 'GET' and self.request.if_none_match and \
                    local_etag in self.request.if_none_match:
                # if the method is get, if it have a header if_none_match end the etag is the same one stored,
                # do nothing and return the same etag
                response = make_response()
                response.status_code = NOT_MODIFIED
                response.set_etag(local_etag)

                return response

        # Obtain the real response for the method
        response = super(Resource, self).handle(endpoint, *args, **kwargs)
        if endpoint == 'list':
            #  for a list, the etag is checked after the request, to check if a resource of the list has changed
            local_etag = etag.get_etag(self.request.path)

            # Calculate the etag for the response
            new_etag = etag.calculate_etag_from_data(str(response.data))

            if self.request.method == 'GET' and self.request.if_none_match and \
                    local_etag in self.request.if_none_match and local_etag == new_etag:
                # for a list, if the method is get, we check that the sent etag is the same as the one stored
                # and the stored one is equal to the one generated by the query
                response = make_response()
                response.status_code = NOT_MODIFIED
                response.set_etag(local_etag)
                return response
            else:
                local_etag = new_etag

        # at the end of the request, create or update the etag if necessary, and add it to the headers
        uri = self.request.path
        if self.request.method in ['POST', 'PUT']:
            # If the request was a post or a put, the data has definitely changed
            local_etag = etag.calculate_etag_from_data(str(response.data))
            if self.request.method == 'POST':
                # If the resource is being created, we need to add the resource id to the
                # URI
                uri += json.loads(response.data).get('id', None) + '/'
        elif self.request.method in ['GET'] and local_etag is None:
            # If the request is a GET, but the etag does not exist, we need to create it
            # we will only fall here if the resource was created manually
            local_etag = etag.calculate_etag_from_data(str(response.data))

        # Store the etag
        etag.set_etag(uri, local_etag)

        # Update the response
        response.set_etag(local_etag)

        return response


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
