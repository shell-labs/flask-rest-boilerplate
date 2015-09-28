from __future__ import absolute_import
from __future__ import unicode_literals

from .base import BaseTestCase


class OAuthTestCase(BaseTestCase):
    __test__ = True

    def test_oauth_login(self):
        """Test login using oauth request"""
        status, data = self.login(self.client.get('id'), self.user.get('email'), self.user.get('password'), scopes=['user'])

        # A 2xx response was given
        assert status >= 200 and status < 300

        # The access and refresh tokens are valid
        assert data.get('access_token', None)
        assert data.get('refresh_token', None)

        # Check that the newly requested token has the same credentials
        # as the old token
        new_status, new_token = self.login(self.client.get('id'), self.user.get('email'), self.user.get('password'))
        assert new_token.get('access_token') != data.get('access_token') and \
            new_token.get('refresh_token') != data.get('refresh_token')

    def test_wrong_credentials(self):
        """Test login with wrong credentials"""
        status, data = self.login(self.client.get('id'), self.user.get('email'), "this is not the password")

        # A 4xx response was given
        assert status == 401

        # Data is a valid json error
        assert data.get('error', None)

        # Check correct error message
        assert data.get('error') == 'invalid_grant'
