from __future__ import absolute_import
from __future__ import unicode_literals
from app import db
from passlib.hash import sha256_crypt


class Etag(db.Model):
    __tablename__ = 'etags'

    id = db.Column(db.Integer, primary_key=True)
    pk = db.Column(db.String)
    etag = db.Column(db.String)

    def __init__(self, pk, etag):
        self.pk = pk
        self.etag = etag

    @staticmethod
    def create_etag(*args):
        encrypt_string = ''
        for arg in args:
            encrypt_string += str(arg)
        return sha256_crypt.encrypt(encrypt_string)