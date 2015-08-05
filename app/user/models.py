from __future__ import absolute_import
from __future__ import unicode_literals
from app import db
from app.util import now, enum, uuid
from app.sql import ChoiceType
from app.constants import Genders

from passlib.hash import sha256_crypt


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    created = db.Column(db.DateTime, default=now)
    modified = db.Column(db.DateTime, default=now, onupdate=now)
    email = db.Column(db.String(255), unique=True, index=True)

    username = db.Column(db.String(32), default=uuid, nullable=False, index=True, unique=True)
    _password = db.Column('password', db.String(128), nullable=False)

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
    user = db.relationship('User', backref=db.backref('details', lazy='joined', uselist=False))
