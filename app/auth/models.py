from __future__ import absolute_import
from __future__ import unicode_literals
from app import db
from app.util import now, enum, uuid, secret
from app.sql import ChoiceType, StringListType, UUID
from app.constants import Genders, GrantTypes, ResponseTypes

from flask.ext.login import UserMixin
from passlib.hash import sha256_crypt


class User(db.Model, UserMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    created = db.Column(db.DateTime, default=now)
    modified = db.Column(db.DateTime, default=now, onupdate=now)
    email = db.Column(db.String(255), unique=True, index=True)

    username = db.Column(db.String(32), default=uuid, nullable=False, index=True, unique=True)
    _password = db.Column('password', db.String(128))

    is_admin = db.Column(db.Boolean, default=False)

    details = db.relationship('UserDetails', backref='user', lazy='joined', uselist=False)

    def __init__(self, password=None, **kwargs):
        super(User, self).__init__(**kwargs)
        self.password = password

        if 'details' not in kwargs:
            # By default create empty details for the user
            self.details = UserDetails(user=self)

    def _get_password(self):
        return self._password

    def _set_password(self, password):
        if password:
            self._password = sha256_crypt.encrypt(password, rounds=12345)

    # Hide password encryption by exposing password field only.
    password = db.synonym('_password',
                          descriptor=property(_get_password,
                                              _set_password))

    def check_password(self, password):
        if self._password is None:
            return False
        return sha256_crypt.verify(password, self._password)

    @classmethod
    def authenticate(cls, login, password):
        user = cls.query.filter(db.or_(User.email == login, User.username == login)).first()
        authenticated = user.check_password(password) if user else False

        return user, authenticated

    def __repr__(self):
        return '<User %r>' % (self.email)

    def get_id(self):
        return str(self.username)

    def is_active(self):
        # Only administrators are allowed to login
        return self.is_admin


class UserDetails(db.Model):
    __tablename__ = 'user_details'

    id = db.Column(db.Integer, primary_key=True)
    created = db.Column(db.DateTime, default=now)
    modified = db.Column(db.DateTime, default=now, onupdate=now)

    name = db.Column(db.String(100))
    url = db.Column(db.String)
    bio = db.Column(db.String)
    born = db.Column(db.DateTime)
    gender = db.Column(ChoiceType(Genders))

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)


class Application(db.Model):
        __tablename__ = 'applications'

        id = db.Column(db.Integer, primary_key=True)
        created = db.Column(db.DateTime, default=now)
        modified = db.Column(db.DateTime, default=now, onupdate=now)

        name = db.Column(db.String(64))
        description = db.Column(db.String(200))
        url = db.Column(db.String(256))

        # An application has a unique user owner
        owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True)
        owner = db.relationship('User')


class Client(db.Model):
    __tablename__ = 'clients'

    client_id = db.Column('id', UUID, primary_key=True, default=uuid)
    client_secret = db.Column('secret', db.String(16), unique=True, index=True,
                              nullable=False, default=secret)

    created = db.Column(db.DateTime, default=now)
    modified = db.Column(db.DateTime, default=now, onupdate=now)

    # Application
    app_id = db.Column(db.Integer, db.ForeignKey('applications.id'), nullable=False)
    app = db.relationship('Application')

    # human readable name, not required
    name = db.Column(db.String(40))

    # public or confidential
    is_confidential = db.Column(db.Boolean)

    _redirect_uris = db.Column('redirect_uris', db.Text)
    _default_scopes = db.Column('default_scopes', db.Text)

    # The list of allowed grant types for this client
    allowed_grant_types = db.Column(StringListType(GrantTypes), default=[GrantTypes.REFRESH_TOKEN])
    allowed_response_types = db.Column(StringListType(ResponseTypes), default=[ResponseTypes.TOKEN])

    # OAuthLib also supports
    # validate_scopes: A function to validate scopes

    @property
    def id(self):
        return self.client_id

    @property
    def secret(self):
        return self.client_secret

    # required if you need to support client credential
    @property
    def user(self):
        return self.app.owner

    @property
    def client_type(self):
        if self.is_confidential:
            return 'confidential'
        return 'public'

    @property
    def redirect_uris(self):
        if self._redirect_uris:
            return self._redirect_uris.split()
        return []

    @property
    def default_redirect_uri(self):
        return self.redirect_uris[0]

    @property
    def default_scopes(self):
        if self._default_scopes:
            return self._default_scopes.split()
        return []


class Grant(db.Model):
    __tablename__ = 'grants'

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer, db.ForeignKey('users.id', ondelete='CASCADE')
    )
    user = db.relationship('User')

    client_id = db.Column(UUID, db.ForeignKey('clients.id'), nullable=False)
    client = db.relationship('Client')

    code = db.Column(db.String(255), index=True, nullable=False)

    redirect_uri = db.Column(db.String(255))
    expires = db.Column(db.DateTime)

    _scopes = db.Column('scopes', db.Text)

    def delete(self):
        db.session.delete(self)
        db.session.commit()
        return self

    @property
    def scopes(self):
        if self._scopes:
            return self._scopes.split()
        return []


class Token(db.Model):
    __tablename__ = 'tokens'

    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(UUID, db.ForeignKey('clients.id'), nullable=False)
    client = db.relationship('Client')

    user_id = db.Column(
        db.Integer, db.ForeignKey('users.id')
    )
    user = db.relationship('User')

    # currently only bearer is supported
    token_type = db.Column(db.String(40))

    access_token = db.Column(db.String(255), unique=True)
    refresh_token = db.Column(db.String(255), unique=True)
    expires = db.Column(db.DateTime)
    _scopes = db.Column('scopes', db.Text)

    def delete(self):
        db.session.delete(self)
        db.session.commit()
        return self

    @property
    def scopes(self):
        if self._scopes:
            return self._scopes.split()
        return []
