from __future__ import absolute_import
from __future__ import unicode_literals
import os

from flask import json
from flask.ext.sqlalchemy import SQLAlchemy
from app import app, db, auth
from app.auth.oauth import GrantTypes
from app.user.models import User, UserDetails
from app.auth.models import Application, Grant, Client
from app.etag.models import Etag
from app.restful import Unauthorized, PreconditionFailed, PreconditionRequired
from app.constants import Roles
import unittest

from passlib.hash import sha256_crypt


class BasicTestCase(unittest.TestCase):
    username = "test@tests.com"
    password = "123456"
    admin_user = "admin@tests.com"
    admin_pass = "123456"

    def setUp(self):
        app.config.from_object('config.TestingConfig')
        self.app = app.test_client()
        db.create_all()

        # Initialize the request context
        app.test_request_context().push()

        self.setUpInitialData()

    def setUpInitialData(self):
        # Create the default user
        user = User(email=self.username)
        user.password = self.password
        user.details = UserDetails(name="Test User", user=user)
        db.session.add(user)

        db.session.add(Grant(user=user, role=Roles.USER))

        # Create admin
        admin = User(email=self.admin_user)
        admin.password = self.admin_pass
        admin.details = UserDetails(name="Test Admin", user=admin)
        db.session.add(admin)

        db.session.add(Grant(user=admin, role=Roles.ADMIN))

        app = Application(owner=user, name="Test App")
        db.session.add(app)
        db.session.add(Grant(user=user, role=Roles.APP))

        client = Client(app=app, name="Mobile Client",
                        allowed_grant_types=[GrantTypes.PASSWORD, GrantTypes.REFRESH_TOKEN])
        db.session.add(client)

        db.session.commit()
        etag = Etag(pk=user.username, etag=Etag.create_etag(str(user.id)))
        db.session.add(etag)
        db.session.commit()

        self.user_id = user.username
        self.admin_id = admin.id
        self.application_id = app.id
        self.client_id = client.id
        self.user_etag = etag.etag

    def tearDown(self):
        db.drop_all(bind=None)

    def login(self, client_id, username, password):
        rv = self.app.post('/v1/oauth2/token', data=json.dumps(dict(
            client_id=client_id,
            username=username,
            password=password,
            grant_type='password'
        )), follow_redirects=True, content_type='application/json')

        assert rv.status_code == 200
        return json.loads(rv.data)

    def test_login(self):
        token = self.login(self.client_id, self.username, self.password)

        assert token.get('access_token', None)
        assert token.get('refresh_token', None)

        # Check that the newly requested token has the same credentials
        # as the old token
        new_token = self.login(self.client_id, self.username, self.password)
        assert new_token.get('access_token') != token.get('access_token') and \
            new_token.get('refresh_token') != token.get('refresh_token')

    def test_list_users(self):
        token = self.login(self.client_id, self.username, self.password)
        assert token.get('access_token', None)

        try:
            rv = self.app.get('/v1/user/', follow_redirects=True,
                              headers={"Authorization": "Bearer %s" % token.get('access_token')})
            assert False
        except Unauthorized:
            # Non admin users cannot get the user list
            assert True

        admin_token = self.login(self.client_id, self.admin_user, self.admin_pass)
        rv = self.app.get('/v1/user/', follow_redirects=True,
                          headers={"Authorization": "Bearer %s" % admin_token.get('access_token')})

        assert rv.status_code == 200

        data = json.loads(rv.data)
        assert data.get('objects', None)

        user_in_data = False
        for user in data.get('objects'):
            if user.get('email') == self.username:
                user_in_data = True

        assert user_in_data

    def test_user_detail(self):
        token = self.login(self.client_id, self.username, self.password)
        assert token.get('access_token', None)

        rv = self.app.get('/v1/user/%s/' % self.user_id, follow_redirects=True,
                          headers={"Authorization": "Bearer %s" % token.get('access_token')})

        assert rv.status_code == 200

        data = json.loads(rv.data)
        assert data.get('email', None) == self.username

        rv = self.app.get('/v1/user/%s/' % self.user_id, follow_redirects=True,
                          headers={"Authorization": "Bearer %s" % token.get('access_token'),
                                   "If-None-Match": "%s" % "bad_etag"})

        assert rv.status_code == 200

        new_etag = rv.headers['ETag']

        rv = self.app.get('/v1/user/%s/' % self.user_id, follow_redirects=True,
                          headers={"Authorization": "Bearer %s" % token.get('access_token'),
                                   "If-None-Match": "%s" % new_etag})
        assert rv.status_code == 304

    def test_user_create(self):
        token = self.login(self.client_id, self.admin_user, self.admin_pass)
        assert token.get('access_token', None)

        rv = self.app.post('/v1/user/', follow_redirects=True,
                           data=json.dumps(dict(email='email@test.com', password='abc', name='Created user', gender='Male')),
                           headers={"Authorization": "Bearer %s" % token.get('access_token')})

        assert rv.status_code == 201

        data = json.loads(rv.data)
        assert data.get('email', None) == 'email@test.com'

    def test_user_update(self):
        token = self.login(self.client_id, self.username, self.password)
        assert token.get('access_token', None)

        try:
            rv = self.app.put('/v1/user/%s/' % self.user_id, follow_redirects=True,
                              data=json.dumps(dict(password='abc')),
                              headers={"Authorization": "Bearer %s" % token.get('access_token')})
            assert False
        except PreconditionRequired:
            # In every put request must be a if match header
            assert True

        try:
            rv = self.app.put('/v1/user/%s/' % self.user_id, follow_redirects=True,
                              data=json.dumps(dict(password='abc')),
                              headers={"Authorization": "Bearer %s" % token.get('access_token'),
                                       "If-Match": "%s" % "bad_etag"})
            assert False
        except PreconditionFailed:
            # If the etags don't match, then the update cannot be executed
            assert True

        rv = self.app.put('/v1/user/%s/' % self.user_id, follow_redirects=True,
                          data=json.dumps(dict(password='abc')),
                          headers={"Authorization": "Bearer %s" % token.get('access_token'),
                                   "If-Match": "%s" % self.user_etag})

        assert rv.status_code == 202

        data = json.loads(rv.data)
        assert data.get('email', None) == self.username

if __name__ == '__main__':
    unittest.main()
