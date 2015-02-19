import logging
import re

from flask import request
from app import util

# Supported grant types
GrantTypes = util.enum(PASSWORD='password',
                        REFRESH_TOKEN='refresh_token')
GrantTypeChoices = GrantTypes._asdict()


class OAuth2Provider:
    """OAuth 2.0 authorization provider. This class manages authorization
    codes and access tokens. Certain methods MUST be overridden in a
    subclass, thus this class cannot be directly used as a provider.

    The structure of the class is borrowed on the provider defined on https://github.com/StartTheShift/pyoauth2,
    however where that project focused on web authorization, this focuses (for now) on the 'password' grant

    These are the methods that must be implemented in a subclass:
        validate_client_id(self, client_id, grant_type)
            # Return True or False
        validate_client_secret(self, client_id, client_secret)
            # Return True or False
        from_user_credentials(self, client_id, username, password, token_type)
            # Return user data or None if authorization is invalid
        from_access_token(self, client_id, access_token)
            # Return mixed data or None on invalid
        from_refresh_token(self, client_id, from_refresh_token)
            # Return mixed data or None on invalid
        persist_token_information(self, client_id, scope, access_token,
                                  token_type, expires_in, refresh_token,
                                  data)
            # Return value ignored
        discard_refresh_token(self, client_id, refresh_token)
            # Return value ignored

    Optionally, the following may be overridden to acheive desired behavior:
        @property
        token_length(self)
        @property
        token_type(self)
        @property
        token_expires_in(self)
        generate_authorization_code(self)
        generate_access_token(self)
        generate_refresh_token(self)
    """
    def __init__(self, app):
        self.config = getattr(app, 'config', dict())
        self.logger = getattr(app, 'logger', logging.getLogger(__name__))

    @property
    def token_type(self):
        return 'Bearer'

    @property
    def token_length(self):
        return self.config.get('TOKEN_LENGTH', 40)

    @property
    def token_expires_in(self):
        """Property method to get the token expiration time in seconds."""
        return self.config.get('TOKEN_EXPIRES_IN', 3600)

    def generate_access_token(self):
        """Generate a random access token."""
        return util.secret(self.token_length)

    def generate_refresh_token(self):
        """Generate a random refresh token."""
        return util.secret(self.token_length)

    def validate_client(self, client_id, grant_type, client_secret=None):
        raise NotImplementedError('Subclasses must implement '
                                  'validate_client.')

    def from_user_credentials(self, client_id, username, password):
        raise NotImplementedError('Subclasses must implement '
                                  'from_user_credentials.')

    def from_access_token(self, access_token):
        raise NotImplementedError('Subclasses must implement '
                                  'from_access_token.')

    def from_refresh_token(self, client_id, refresh_token):
        raise NotImplementedError('Subclasses must implement '
                                  'from_access_token.')

    def persist_token_information(self, client_id, access_token,
                                  token_type, expires_in,
                                  refresh_token, data):
        raise NotImplementedError('Subclasses must implement '
                                  'validate_refresh_token.')

    def discard_refresh_token(self, client_id, refresh_token):
        raise NotImplementedError('Subclasses must implement '
                                  'discard_refresh_token.')

    def get_token(self, grant_type, client_id, **kwargs):
        """Get token from provided credentials

        Returns a dict with the authorization credentials
        """
        if grant_type != 'password':
            raise OAuth2Exception('unsupported_grant_type')

        try:
            for x in ['username', 'password']:
                if not kwargs.get(x):
                    raise TypeError("Missing required param for grant type {0}: {1}".format(grant_type, x))

            client_secret = kwargs.get('client_secret', None)

            # Validate the client credentials
            # TODO: this should validate that the client has permission to perform this grant request
            if not self.validate_client(client_id, grant_type, client_secret=client_secret):
                raise OAuth2Exception("invalid_client")

            username = kwargs.get('username')
            password = kwargs.get('password')

            # Validate user access
            data = self.from_user_credentials(client_id, username, password)
            if data is None:
                raise OAuth2Exception("invalid_grant")

            # Generate access tokens once all conditions have been met
            access_token = self.generate_access_token()
            token_type = self.token_type
            expires_in = self.token_expires_in
            refresh_token = self.generate_refresh_token()

            self.persist_token_information(client_id, access_token,
                                           token_type, expires_in,
                                           refresh_token, data)

            return dict(access_token=access_token,
                        token_type=token_type,
                        expires_in=expires_in,
                        refresh_token=refresh_token)

        except TypeError as e:
            self.logger.exception(e)
            raise OAuth2Exception('invalid_request')

    def refresh_token(self, grant_type, client_id, refresh_token, **kwargs):
        # Ensure proper grant_type
        if grant_type != 'refresh_token':
            raise OAuth2Exception('unsupported_grant_type')

        # Validate the client credentials
        # TODO: this should validate that the client has permission to perform this grant request
        if not self.validate_client(client_id, grant_type):
            raise OAuth2Exception("invalid_client")

        # Get user from the refresh token
        data = self.from_refresh_token(client_id, refresh_token)
        if not data:
            raise OAuth2Exception("invalid_grant")

        # discard original token
        self.discard_refresh_token(refresh_token)

        # Generate access tokens once all conditions have been met
        access_token = self.generate_access_token()
        token_type = self.token_type
        expires_in = self.token_expires_in
        refresh_token = self.generate_refresh_token()

        # Store credentials
        self.persist_token_information(client_id, access_token,
                                       token_type, expires_in,
                                       refresh_token, data)

        return dict(access_token=access_token,
                    token_type=token_type,
                    expires_in=expires_in,
                    refresh_token=refresh_token)

    def get_token_from_post_data(self, data):
        """Get a token response from POST data.
        :param data: POST data containing authorization information.
        :type data: dict
        :rtype: requests.Response
        """
        try:
            # Verify OAuth 2.0 Parameters
            for x in ['grant_type', 'client_id']:
                if not data.get(x):
                    raise TypeError("Missing required OAuth 2.0 POST param: {0}".format(x))

            # Handle get token from refresh_token
            if 'refresh_token' in data:
                return self.refresh_token(**data)

            return self.get_token(**data)
        except TypeError as e:
            self.logger.exception(e)
            raise OAuth2Exception('invalid_request')
        except StandardError as e:
            self.logger.exception(e)
            raise OAuth2Exception('server_error')


class OAuth2Exception(Exception):
    status_code = 400

    def __init__(self, error, error_description=None, error_uri=None, status_code=None):
        Exception.__init__(self)
        self.error = error
        if status_code is not None:
            self.status_code = status_code
        self.error_description = error_description
        self.error_uri = error_uri

    def to_dict(self):
        rv = dict()
        for attr in ['error', 'error_description', 'error_uri']:
            val = getattr(self, attr, None)
            if val is not None:
                rv[attr] = val

        return rv
