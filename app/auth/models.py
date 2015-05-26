from app import db
from app.user.models import User
from app.util import now, secret, uuid
from app.sql import ChoiceType, StringListType, UUID
from app.constants import Roles

from oauth import GrantTypes
from datetime import timedelta


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


class Grant(db.Model):
    __tablename__ = 'grants'

    id = db.Column(db.Integer, primary_key=True)
    created = db.Column(db.DateTime, default=now)
    modified = db.Column(db.DateTime, default=now, onupdate=now)
    role = db.Column(ChoiceType(Roles), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    user = db.relationship('User')

    @classmethod
    def check_grant(cls, user, role):
        return cls.query.filter(Grant.user == user, Grant.role == role).first() is not None


class Client(db.Model):
    __tablename__ = 'clients'

    id = db.Column(UUID, primary_key=True, default=uuid)
    created = db.Column(db.DateTime, default=now)
    modified = db.Column(db.DateTime, default=now, onupdate=now)
    secret = db.Column('secret', db.String(16), unique=True, default=secret)

    name = db.Column(db.String(64))
    url = db.Column(db.String(256))

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
    refresh_token = db.Column(db.String(40), nullable=False, index=True)
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
