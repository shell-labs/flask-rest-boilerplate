from __future__ import absolute_import
from __future__ import unicode_literals
from app import db
from app.util import now
import hashlib


class Etag(db.Model):
    __tablename__ = 'etags'

    uri = db.Column(db.String, primary_key=True)
    created = db.Column(db.DateTime, default=now)
    modified = db.Column(db.DateTime, default=now, onupdate=now)
    value = db.Column(db.String, nullable=False)

    @staticmethod
    def calculate(data):
        hash_object = hashlib.sha1(data.encode())
        hex_dig = hash_object.hexdigest()
        return hex_dig
