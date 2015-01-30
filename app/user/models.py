from app import db
from app.util import now


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    created = db.Column(db.DateTime, default=now)
    modified = db.Column(db.DateTime, default=now, onupdate=now)
    name = db.Column(db.String(32), nullable=False, unique=True)
    email = db.Column(db.String(255), unique=True)

    _password = db.Column('password', db.String(20), nullable=False)

    def __init__(self, name, email):
        self.name = name
        self.email = email

    def __repr__(self):
        return '<User %r>' % (self.name)
