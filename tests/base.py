from __future__ import absolute_import
from __future__ import unicode_literals

from flask import json
from app import app, db
from app.auth.oauth import GrantTypes
from app.user.models import User, UserDetails, Grant
from app.auth.models import Application, Client
from app.constants import Roles

import unittest


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

        # Give the test user, basic user rights
        db.session.add(Grant(user=user, role=Roles.USER))

        # Create administrator
        admin = User(email=self.admin.get('email'), password=self.admin.get('password'))
        admin.details = UserDetails(name=self.admin.get('name'), user=admin)
        db.session.add(admin)

        # Give administrative role to the administrator
        db.session.add(Grant(user=admin, role=Roles.ADMIN))

        # Create application owner
        owner = User(email=self.owner.get('email'), password=self.owner.get('password'))
        owner.details = UserDetails(name=self.owner.get('name'), user=owner)
        db.session.add(owner)

        app = Application(owner=owner, name=self.application.get('name'))
        db.session.add(app)

        # Give the user application administration rights
        db.session.add(Grant(user=owner, role=Roles.APP))

        # Create a client
        client = Client(app=app, name=self.client.get('name'),
                        allowed_grant_types=[GrantTypes.PASSWORD, GrantTypes.REFRESH_TOKEN])
        db.session.add(client)
        db.session.commit()

        # Remember the values
        self.user['id'] = user.username
        self.admin['id'] = admin.username
        self.owner['id'] = owner.username
        self.application['id'] = app.id
        self.client['id'] = client.id

    def tearDown(self):
        db.drop_all(bind=None)
        self.context.pop()

    def login(self, client_id, username, password):
        """Login using OAUTH 2.0 password grant"""

        rv = self.app.post('/v1/oauth2/token', data=json.dumps(dict(
            client_id=client_id,
            username=username,
            password=password,
            grant_type='password'
        )), follow_redirects=True, content_type='application/json')

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
