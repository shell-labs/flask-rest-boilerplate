from __future__ import absolute_import
from __future__ import unicode_literals

from .base import BaseTestCase
from flask import json
from app.restful import PreconditionFailed, PreconditionRequired


class CacheTestCase(BaseTestCase):
    """Unit tests for cache module, including ETag generation"""

    __test__ = True

    def test_user_detail(self):
        status, token = self.login(self.client.get('id'), self.user.get('email'), self.user.get('password'))
        assert token.get('access_token', None)

        rv = self.get('/v1/user/%s/' % self.user.get('id'), token.get('access_token'))
        assert rv.status_code == 200

        new_etag = rv.headers['ETag']

        rv = self.get('/v1/user/%s/' % self.user.get('id'), token.get('access_token'),
                      headers={"If-None-Match": "%s" % new_etag})
        assert rv.status_code == 304

    def test_user_create(self):
        status, token = self.login(self.client.get('id'), self.admin.get('email'), self.admin.get('password'))
        assert token.get('access_token', None)

        # Create a new user
        rv = self.post('/v1/user/', token.get('access_token'),
                       data=json.dumps(dict(email='email@test.com',
                                            password='abc', name='Created user',
                                            gender='Male')))

        assert rv.status_code == 201
        assert rv.headers.get('ETag', None)

        new_etag = rv.headers['ETag']

        data = json.loads(rv.data)

        rv = self.get('v1/user/%s/' % data.get('id', None), token.get('access_token'),
                      headers={"If-None-Match": "%s" % new_etag})

        assert rv.status_code == 304

    def test_query_list(self):
        status, token = self.login(self.client.get('id'),
                                   self.admin.get('email'),
                                   self.admin.get('password'))

        rv = self.get('/v1/user/', token.get('access_token'))

        assert rv.status_code == 200

        new_tag = rv.headers["ETag"]
        rv = self.app.get('/v1/user/', follow_redirects=True,
                          headers={"Authorization": "Bearer %s" % token.get('access_token'),
                                   "If-None-Match": "%s" % new_tag})
        assert rv.status_code == 304

    def test_user_update(self):
        status, token = self.login(self.client.get('id'),
                                   self.user.get('email'),
                                   self.user.get('password'))
        assert token.get('access_token', None)

        # Get the user data
        rv = self.get('v1/user/%s/' % self.user.get('id'), token.get('access_token'))

        assert rv.headers.get('Etag', None)
        etag = rv.headers.get('Etag')

        try:
            rv = self.put('/v1/user/%s/' % self.user.get('id'), token.get('access_token'),
                          data=json.dumps(dict(password='abc')))
            assert False
        except PreconditionRequired:
            # In every put request must be a if match header
            assert True

        try:
            rv = self.put('/v1/user/%s/' % self.user.get('id'), token.get('access_token'),
                          data=json.dumps(dict(password='abc')),
                          headers={"If-Match": "%s" % "bad_etag"})
            assert False
        except PreconditionFailed:
            # If the etags don't match, then the update cannot be executed
            assert True

        rv = self.put('/v1/user/%s/' % self.user.get('id'), token.get('access_token'),
                      data=json.dumps(dict(password='abc')),
                      headers={"If-Match": "%s" % etag})

        assert rv.status_code == 202

        data = json.loads(rv.data)
        assert data.get('email', None) == self.user.get('email')
