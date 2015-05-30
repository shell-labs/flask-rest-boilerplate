from __future__ import absolute_import
from __future__ import unicode_literals
from .oauth import OAuth2Provider, OAuth2Exception
from app.user.models import User
from .models import Client, Token, Grant
from app import db, app


class AuthProvider(OAuth2Provider):
    def validate_client(self, client_id, grant_type, client_secret=None):
        client = Client.query.get(client_id)
        if client and (client_secret is None or client.secret == client_secret):
            return grant_type in client.allowed_grant_types

        return False

    def from_user_credentials(self, client_id, username, password):
        (user, authenticated) = User.authenticate(username, password)
        if not authenticated:
            return None

        return user

    def from_access_token(self, access_token):
        token = Token.query.filter_by(access_token=access_token).first()
        if not token or token.expired:
            return (None, None)

        return (token.user, token.client)

    def from_refresh_token(self, client_id, refresh_token):
        token = Token.query.filter_by(client_id=client_id, refresh_token=refresh_token).first()
        if not token:
            return None

        return token.user

    def discard_refresh_token(self, client_id, refresh_token):
        token = Token.query.filter_by(client_id=client_id, refresh_token=refresh_token).first()
        if not token:
            return

        db.session.delete(token)
        db.session.commit()

    def persist_token_information(self, client_id, access_token,
                                  token_type, expires_in,
                                  refresh_token, data):
        client = Client.query.get(client_id)

        if client is None:
            raise OAuth2Exception('invalid_client')

        if data is None or not hasattr(data, 'id'):
            app.logger.error("Provided data %s is None or has no id property" % data)
            raise OAuth2Exception('invalid_request')

        token = Token(client=client, user=data, access_token=access_token,
                      expires_in=expires_in, refresh_token=refresh_token,
                      token_type=token_type)
        db.session.add(token)
        db.session.commit()

    def validate_user_roles(self, user, roles=[]):
        # There is no role restriction
        if not roles:
            return True

        for role in roles:
            if Grant.check_grant(user, role):
                return True

        return False
