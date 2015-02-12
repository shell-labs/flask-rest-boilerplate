from oauth import OAuth2Provider, OAuth2Exception
from models import Client, User, Token
from app import db, app

class AuthProvider(OAuth2Provider):
    def validate_client(self, client_id, grant_type=None):
        return Client.query.get(client_id) is not None

    def validate_user_access(self, username, password):
        return User.authenticate(username, password)

    def from_username(self, client_id, username):
        return User.query.filter_by(email=username).first()

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

        token = Token(client=client, user=data, access_token=access_token, expires_in=expires_in, refresh_token=refresh_token)
        db.session.add(token)
        db.session.commit()
