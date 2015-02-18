from app import db
from app.user.models import User
from app.util import now, secret, uuid
from app.sql import ChoiceType, UUID

from datetime import timedelta


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

    app_key = db.Column('app_id', UUID, db.ForeignKey('applications.id'))

    secret = db.Column('secret', db.String(16), unique=True, default=secret)

    app = db.relationship('Application')


class Token(db.Model):
    __tablename__ = 'tokens'

    id = db.Column(db.Integer, primary_key=True)
    created = db.Column(db.DateTime, default=now)
    modified = db.Column(db.DateTime, default=now, onupdate=now)

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    client_id = db.Column(UUID, db.ForeignKey('clients.id'))

    token_type = db.Column(db.String(20), nullable=False)
    access_token = db.Column(db.String(40), nullable=False, index=True)
    refresh_token = db.Column(db.String(40), nullable=False, index=True)
    _expires_in = db.Column('expires_in', db.Integer, nullable=False    )

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
