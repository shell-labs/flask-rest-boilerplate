import os

from flask import json
from flask.ext.sqlalchemy import SQLAlchemy
from app import app, db, auth
from app.user.models import User
from app.auth.models import Application, Grant, Client
import unittest


class BasicTestCase(unittest.TestCase):
    username = "test@tests.com"
    password = "123456"

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

        app = Application(owner=user, name="Test App")
        db.session.add(app)
        db.session.add(Grant(user=user, role=Grant.APP))

        client = Client(app=app, name="Mobile Client")
        db.session.add(client)

        db.session.commit()

        self.user_id = user.id
        self.application_id = app.id
        self.client_id = client.id


    def tearDown(self):
        db.drop_all(bind=None)

    def login(self, client_id):
        rv = self.app.post('/v1/oauth2/token', data=json.dumps(dict(
            client_id=client_id,
            username=self.username,
            password=self.password,
            grant_type='password'
        )), follow_redirects=True, content_type='application/json')

        return json.loads(rv.data)

    def test_login(self):
        token = self.login(self.client_id)

        assert token.get('access_token', None)
        assert token.get('refresh_token', None)

        # Check that the newly requested token has the same credentials
        # as the old token
        new_token = self.login(self.client_id)
        assert new_token.get('access_token') != token.get('access_token') and \
            new_token.get('refresh_token') != token.get('refresh_token')

if __name__ == '__main__':
    unittest.main()
