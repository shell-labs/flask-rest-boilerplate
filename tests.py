import os

from flask import json
from flask.ext.sqlalchemy import SQLAlchemy
from app import app, db, auth
from app.auth.oauth import GrantTypes
from app.user.models import User
from app.auth.models import Application, Grant, Client
import unittest


class BasicTestCase(unittest.TestCase):
    username = "test@tests.com"
    password = "123456"
    admin_user = "admin@tests.com"
    admin_pass = "123456"

    def setUp(self):
        app.config.from_object('config.TestingConfig')
        self.app = app.test_client()
        db.create_all()

        self.setUpInitialData()

    def setUpInitialData(self):
        # Create the default user
        user = User(email=self.username)
        user.password = self.password
        db.session.add(user)

        db.session.add(Grant(user=user, role=Grant.USER))

        # Create admin
        admin = User(email=self.admin_user)
        admin.password = self.admin_pass
        db.session.add(admin)

        db.session.add(Grant(user=admin, role=Grant.ADMIN))

        app = Application(owner=user, name="Test App")
        db.session.add(app)
        db.session.add(Grant(user=user, role=Grant.APP))

        client = Client(app=app, name="Mobile Client",
                        allowed_grant_types=[GrantTypes.PASSWORD, GrantTypes.REFRESH_TOKEN])
        db.session.add(client)

        db.session.commit()

        self.user_id = user.id
        self.admin_id = admin.id
        self.application_id = app.id
        self.client_id = client.id

    def tearDown(self):
        db.drop_all(bind=None)

    def login(self, client_id, username, password):
        rv = self.app.post('/v1/oauth2/token', data=json.dumps(dict(
            client_id=client_id,
            username=username,
            password=password,
            grant_type='password'
        )), follow_redirects=True, content_type='application/json')

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
        rv = self.app.get('/v1/user/', follow_redirects=True,
                          headers={"Authorization": "Bearer %s" % token.get('access_token')})

        # Non admin users cannot get the user list
        assert rv.status_code == 401

        admin_token = self.login(self.client_id, self.admin_user, self.admin_pass)
        rv = self.app.get('/v1/user/', follow_redirects=True,
                          headers={"Authorization": "Bearer %s" % admin_token.get('access_token')})


        data = json.loads(rv.data)
        assert data.get('objects', None)

        user_in_data = False
        for user in data.get('objects'):
            if user.get('email') == self.username:
                user_in_data = True

        assert user_in_data



if __name__ == '__main__':
    unittest.main()
