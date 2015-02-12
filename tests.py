import os

from flask import json
from flask.ext.sqlalchemy import SQLAlchemy
from app import app, db, auth
from app.auth.models import User, Application, Role
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

        db.session.add(Role(user=user, role=Role.CLIENT))

        app = Application(owner=user, name="Test App")
        db.session.add(app)
        db.session.add(Role(user=user, role=Role.OWNER))

        self.user = user
        self.application = app

        db.session.commit()

    def tearDown(self):
        db.drop_all(bind=None)

    def register_client(self):
        rv = self.app.post('/v1/client/', data=json.dumps(dict(
            app_key=self.application.id
        )), follow_redirects=True, content_type='application/json')

        return json.loads(rv.data)

    def login(self, client_id):
        rv = self.app.post('/v1/oauth2/token', data=json.dumps(dict(
            client_id=client_id,
            username=self.username,
            password=self.password,
            grant_type='password'
        )), follow_redirects=True, content_type='application/json')

        return json.loads(rv.data)

    def test_register_client(self):
        """Test correct registration of a client"""
        client = self.register_client()
        assert client.get('client_id', None)
        assert client.get('client_secret', None)

    def test_login(self):
        client = self.register_client()

        assert client.get('client_id', None)

        assert token.get('access_token', None)
        assert token.get('refresh_token', None)


if __name__ == '__main__':
    unittest.main()
