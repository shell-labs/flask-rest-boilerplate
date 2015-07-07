from __future__ import absolute_import
from __future__ import unicode_literals
from app import db
from app.util import now
from passlib.hash import sha256_crypt


class Etag(db.Model):
    __tablename__ = 'etags'

    id = db.Column(db.Integer, primary_key=True)
    created = db.Column(db.DateTime, default=now)
    modified = db.Column(db.DateTime, default=now, onupdate=now)
    pk = db.Column(db.String)
    etag = db.Column(db.String)

    def __init__(self, pk, etag):
        self.pk = pk
        self.etag = etag

    @staticmethod
    def create_etag(data):
        return sha256_crypt.encrypt(data, salt="samesaltforever")


def get_etag(pk):
    return Etag.query.filter(Etag.pk == pk).first()

def commit_etag(etag):
    db.session.add(etag)
    db.session.commit()