from __future__ import absolute_import
from __future__ import unicode_literals

from .models import Etag


def get_etag(uri):
    """Get the current etag for the specified uri"""
    etag = Etag.query.get(uri)
    if not etag:
        return None

    return etag.value


def calculate_etag_from_data(data):
    """Calculate the etag value from the data"""
    return Etag.calculate(data)


def set_etag(uri, etag):
    """Store the Etag for the specified URI and given hash value"""
    etag_obj = Etag.query.get(uri)
    if etag_obj is None:
        etag_obj = Etag(uri=uri, value=etag)

    # Store in db
    db.session.add(etag_obj)
    db.session.commit()


def set_etag_from_data(uri, data):
    """Store the Etag for the specified URI and given data value"""
    etag_obj = Etag.query.get(uri)
    if etag_obj is None:
        etag_obj = Etag(uri=uri, value=calculate_etag_from_data(data))

    # Store in db
    db.session.add(etag_obj)
    db.session.commit()
