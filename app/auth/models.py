from app import db
from app.util import now, secret, uuid
from app.sql import ChoiceType, UUID

from passlib.hash import sha256_crypt
from datetime import timedelta

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    created = db.Column(db.DateTime, default=now)
    modified = db.Column(db.DateTime, default=now, onupdate=now)
    email = db.Column(db.String(255), unique=True, index=True)

    _password = db.Column('password', db.String(128), nullable=False)

    def _get_password(self):
        return self._password

    def _set_password(self, password):
        self._password = sha256_crypt.encrypt(password, rounds=12345)

    # Hide password encryption by exposing password field only.
    password = db.synonym('_password',
                          descriptor=property(_get_password,
                                              _set_password))

    def __init__(self, email):
        self.email = email

    def check_password(self, password):
        if self._password is None:
            return False
        return sha256_crypt.verify(password, self._password)

    @classmethod
    def authenticate(cls, login, password):
        user = cls.query.filter(User.email==login).first()
        authenticated = user.check_password(password) if user else False

        return user, authenticated

    def __repr__(self):
        return '<User %r>' % (self.email)


class Application(db.Model):
        __tablename__ = 'applications'

        id = db.Column(UUID, primary_key=True, default=uuid)
        created = db.Column(db.DateTime, default=now)
        modified = db.Column(db.DateTime, default=now, onupdate=now)

        name = db.Column(db.String(64))
        description = db.Column(db.String(200))
        url = db.Column(db.String(256))

        # An application has a unique user owner
        owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True)
        owner = db.relationship('User')


class Role(db.Model):
    __tablename__ = 'roles'

    ADMIN = u'Administrator'
    CLIENT = u'Client'
    OWNER = u'Application Owner'
    ROLES = (
        (u'ADM', ADMIN),
        (u'CLI', CLIENT),
        (u'APP', OWNER),
    )

    id = db.Column(db.Integer, primary_key=True)
    created = db.Column(db.DateTime, default=now)
    modified = db.Column(db.DateTime, default=now, onupdate=now)
    role = db.Column(ChoiceType(ROLES), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    user = db.relationship('User')


class Client(db.Model):
    __tablename__ = 'clients'

    id = db.Column(UUID, primary_key=True, default=uuid)
    created = db.Column(db.DateTime, default=now)
    modified = db.Column(db.DateTime, default=now, onupdate=now)

    app_key = db.Column('app_id', db.Integer, db.ForeignKey('applications.id'))

    secret = db.Column('secret', db.String(16), unique=True, default=secret)

    app = db.relationship('Application')


class Token(db.Model):
    __tablename__ = 'tokens'

    id = db.Column(db.Integer, primary_key=True)
    created = db.Column(db.DateTime, default=now)
    modified = db.Column(db.DateTime, default=now, onupdate=now)

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'))

    token_type = db.Column(db.String(20), nullable=False)
    access_token = db.Column(db.String(40), nullable=False, index=True)
    refresh_token = db.Column(db.String(40), nullable=False, index=True)
    _expires_in = db.Column('expires_in', db.Integer, nullable=False)

    user = db.relationship('User')
    client = db.relationship('Client')

    def __init__(self, expires_in=3600, **kwargs):
        super(Token, self).__init__(**kwargs)
        self.expires_in = expires_in

    @property
    def expires_in(self):
        if self.created:
            delta = (timedelta(seconds=self._expires_in) - (now() - self.created)).seconds
            return delta if delta > 0 else 0

        return self._expires_in

    @expires_in.setter
    def expires_in(self, value):
        self._expires_in = value

    @property
    def expires(self):
        if self.created:
            return self.created + timedelta(seconds=self._expires_in)
        return None

    @property
    def expired(self):
        return now() > self.created + timedelta(seconds=self._expires_in)
