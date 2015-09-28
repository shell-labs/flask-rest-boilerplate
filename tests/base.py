from __future__ import absolute_import
from __future__ import unicode_literals

from flask import json
from app import app, db
from app.auth.models import GrantTypes, User, UserDetails, Application, Client

import unittest

try:
    # Python 3
    import urllib.parse as urllib
except:
    # Python 2.7
    import urllib


class BaseTestCase(unittest.TestCase):
    __test__ = False

    user = {
        'email': 'juan.perez@gmail.com',
        'name': 'Juan Perez',
        'password': '123456'
    }

    owner = {
        'email': 'pablo.gonzalez@hotmail.com',
        'name': 'Pablo Gonzalez',
        'password': 'uvxyz'
    }

    admin = {
        'email': 'admin@becity.cl',
        'name': 'Administrator',
        'password': 'abcde'
    }

    application = {
        'name': 'Test App'
    }

    client = {
        'name': 'Test App REST client'
    }

    def setUp(self, populate=True):
        # Load testing configuration
        app.config.from_object('config.TestingConfig')
        self.app = app.test_client()
        db.create_all()

        # Initialize the request context
        self.context = app.test_request_context()
        self.context.push()

        # load data
        if (populate):
            self.populate()

    def populate(self):
        """Populate the model with test data"""

        # Create the default user
        user = User(email=self.user.get('email'), password=self.user.get('password'))
        user.details = UserDetails(name=self.user.get('name'), user=user)
        db.session.add(user)

        # Create administrator
        admin = User(email=self.admin.get('email'), password=self.admin.get('password'), is_admin=True)
        admin.details = UserDetails(name=self.admin.get('name'), user=admin)
        db.session.add(admin)

        # Create application owner
        owner = User(email=self.owner.get('email'), password=self.owner.get('password'))
        owner.details = UserDetails(name=self.owner.get('name'), user=owner)
        db.session.add(owner)

        app = Application(owner=owner, name=self.application.get('name'))
        db.session.add(app)

        # Create a client
        client = Client(app=app, name=self.client.get('name'),
                        allowed_grant_types=[GrantTypes.PASSWORD, GrantTypes.REFRESH_TOKEN],
                        _default_scopes='user other',
                        _redirect_uris='http://localhost')
        db.session.add(client)
        db.session.commit()

        # Remember the values
        self.user['id'] = user.username
        self.admin['id'] = admin.username
        self.owner['id'] = owner.username
        self.application['id'] = app.id
        self.client['id'] = client.client_id

    def tearDown(self):
        db.drop_all(bind=None)
        self.context.pop()

    def login(self, client_id, username, password, scopes=[]):
        """Login using OAUTH 2.0 password grant"""

        data = dict(
            client_id=client_id,
            username=username,
            password=password,
            grant_type='password'
        )
        if len(scopes) > 0:
            data['scope'] = ' '.join(scopes)
        rv = self.app.post('/v1/oauth2/token?' + urllib.urlencode(data), follow_redirects=True)

        if rv.status_code >= 200 and rv.status_code < 300:
            return rv.status_code, json.loads(rv.data)

        try:
            return rv.status_code, json.loads(rv.data)
        except ValueError:
            return rv.status_code, rv.data

    def _prepare(self, access_token, **params):
        if 'headers' not in params:
            params['headers'] = {}

        if 'follow_redirects' not in params:
            params['follow_redirects'] = True

        params.get('headers').update({"Authorization": "Bearer %s" % access_token})

        return params

    def get(self, uri, access_token, **params):
        """Perform an authenticated GET request using the given access_token"""
        return self.app.get(uri, **self._prepare(access_token, **params))

    def post(self, uri, access_token, **params):
        """Perform an authenticated POST request using the given access_token"""
        return self.app.post(uri, **self._prepare(access_token, **params))

    def put(self, uri, access_token, **params):
        """Perform an authenticated PUT request using the given access_token"""
        return self.app.put(uri, **self._prepare(access_token, **params))

    def delete(self, uri, access_token, **params):
        """Perform an authenticated DELETE request using the given access_token"""
        return self.app.delete(uri, **self._prepare(access_token, **params))
