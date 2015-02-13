from oauth import OAuth2Provider, OAuth2Exception
from models import Client, User, Token, Role
from app import db, app

class AuthProvider(OAuth2Provider):
    def validate_client(self, client_id, grant_type=None):
        return Client.query.get(client_id) is not None

    def from_client_id(self, client_id, token_type):
        token = Token.query.filter_by(client_id=client_id, token_type=token_type)
        if not token or token.expired:
            return None

        return dict(access_token=token.access_token, refresh_token=token.refresh_token,
                    expires_in=token.expires_in)

    def from_user_credentials(self, client_id, username, password, token_type):
        (user, authenticated) = User.authenticate(username, password)
        if not authenticated:
            return None, None

        token = Token.query.filter_by(client_id=client_id, user=user, token_type=token_type).first()
        if not token or token.expired:
            return user, None

        return user, dict(access_token=token.access_token, token_type=token.token_type,
                          refresh_token=token.refresh_token, expires_in=token.expires_in)

    def from_access_token(self, access_token):
        token = Token.query.filter_by(access_token=access_token).first()
        if not token or token.expired:
            return None

        return token.user

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
        for role in roles:
            r = Role.query.filter_by(role=role, user=user).first()
            if not r:
                return False

        return True
