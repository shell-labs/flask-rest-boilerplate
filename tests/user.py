from __future__ import absolute_import
from __future__ import unicode_literals

from .base import BaseTestCase
from flask import json

from app.restful import Unauthorized


class UserTestCase(BaseTestCase):
    """Unit tests for user REST operation"""

    def test_list_users(self):
        """Check the method to get the list of users"""
        status, token = self.login(self.client.get('id'),
                                   self.user.get('email'),
                                   self.user.get('password'))
        assert token.get('access_token', None)

        try:
            rv = self.get('/v1/user/', token.get('access_token'))
            assert False
        except Unauthorized:
            # Non admin users cannot get the user list
            assert True

        status, token = self.login(self.client.get('id'),
                                   self.admin.get('email'),
                                   self.admin.get('password'))

        rv = self.get('/v1/user/', token.get('access_token'))

        assert rv.status_code == 200

        data = json.loads(rv.data)
        assert data.get('objects', None)

        user_in_data = False
        for user in data.get('objects'):
            if user.get('email') == self.user.get('email'):
                user_in_data = True

        assert user_in_data

    def test_user_detail(self):
        status, token = self.login(self.client.get('id'),
                                   self.user.get('email'),
                                   self.user.get('password'))
        assert token.get('access_token', None)

        rv = self.get('/v1/user/%s/' % self.user.get('id'), token.get('access_token'))

        assert rv.status_code == 200

        data = json.loads(rv.data)
        assert data.get('email', None) == self.user.get('email')

    def test_user_creation_by_user(self):
        status, token = self.login(self.client.get('id'),
                                   self.user.get('email'),
                                   self.user.get('password'))
        assert token.get('access_token', None)

        try:
            rv = self.post('/v1/user/', token.get('access_token'),
                           data=json.dumps(dict(email='email@test.com',
                                                password='abc', name='Created user',
                                                gender='Male')))
            assert False
        except Unauthorized:
            assert True

    def test_user_creation_by_admin(self):
        status, token = self.login(self.client.get('id'),
                                   self.admin.get('email'),
                                   self.admin.get('password'))
        assert token.get('access_token', None)

        rv = self.post('/v1/user/', token.get('access_token'),
                       data=json.dumps(dict(email='email@test.com',
                                            password='abc', name='Created user',
                                            gender='Male')))

        assert rv.status_code == 201

        data = json.loads(rv.data)
        assert data.get('email', None) == 'email@test.com'

    def test_user_creation_by_owner(self):
        status, token = self.login(self.client.get('id'),
                                   self.owner.get('email'),
                                   self.owner.get('password'))
        assert token.get('access_token', None)

        try:
            rv = self.post('/v1/user/', token.get('access_token'),
                           data=json.dumps(dict(email='email@test.com',
                                                password='abc', name='Created user',
                                                gender='Male')))
            assert False
        except Unauthorized:
            assert True

    def test_user_update(self):
        status, token = self.login(self.client.get('id'),
                                   self.user.get('email'),
                                   self.user.get('password'))
        assert token.get('access_token', None)

        # Get the user data
        rv = self.get('v1/user/%s/' % self.user.get('id'), token.get('access_token'))

        assert rv.headers.get('Etag', None)
        etag = rv.headers.get('Etag')

        rv = self.put('/v1/user/%s/' % self.user.get('id'), token.get('access_token'),
                      data=json.dumps(dict(password='abc')),
                      headers={"If-Match": "%s" % etag})

        assert rv.status_code == 202

        data = json.loads(rv.data)
        assert data.get('email', None) == self.user.get('email')

        # try to login with the new password
        status, token = self.login(self.client.get('id'),
                                   self.user.get('email'),
                                   'abc')
        assert status == 200
