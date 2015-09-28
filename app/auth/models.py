from __future__ import absolute_import
from __future__ import unicode_literals
from app import db
from app.util import now, enum, uuid, secret
from app.sql import ChoiceType, StringListType, UUID

from .oauth import GrantTypes
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

    id = db.Column(UUID, primary_key=True, default=uuid)
    created = db.Column(db.DateTime, default=now)
    modified = db.Column(db.DateTime, default=now, onupdate=now)
    secret = db.Column('secret', db.String(16), unique=True, default=secret)

    name = db.Column(db.String(64))
    redirect_uri = db.Column(db.String(256))

    # The list of allowed grant types for this client
    allowed_grant_types = db.Column(StringListType(GrantTypes), default=[GrantTypes.REFRESH_TOKEN])

    # Application
    app_id = db.Column(db.Integer, db.ForeignKey('applications.id'))
    app = db.relationship('Application')


class Token(db.Model):
    __tablename__ = 'tokens'

    id = db.Column(db.Integer, primary_key=True)
    created = db.Column(db.DateTime, default=now)
    modified = db.Column(db.DateTime, default=now, onupdate=now)

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    client_id = db.Column(UUID, db.ForeignKey('clients.id'), nullable=False)

    token_type = db.Column(db.String(20), nullable=False)
    access_token = db.Column(db.String(40), nullable=False, index=True)
    refresh_token = db.Column(db.String(40), index=True)
    _expires_in = db.Column('expires_in', db.Integer, nullable=False)

    user = db.relationship('User')
    client = db.relationship('Client')

    def __init__(self, expires_in=3600, **kwargs):
        super(Token, self).__init__(**kwargs)
        self.expires_in = expires_in

    @property
    def expires_in(self):
        """Return time to expiration, calculated by
        substracting the elapsed time since the creation of the token
        by the database value of expires_in
        """
        if self.created:
            delta = (timedelta(seconds=self._expires_in) - (now() - self.created)).seconds
            return delta if delta > 0 else 0

        return self._expires_in

    @expires_in.setter
    def expires_in(self, value):
        self._expires_in = value

    @property
    def expires(self):
        """Return the date of expiration according to the
        creation date of the token, or None if there is
        no creation date"""
        if self.created:
            return self.created + timedelta(seconds=self._expires_in)
        return None

    @property
    def expired(self):
        """Return true if the token is expired"""
        return now() > self.created + timedelta(seconds=self._expires_in)
