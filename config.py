from __future__ import absolute_import
from __future__ import unicode_literals


class Config(object):
    DEBUG = False
    TESTING = False
    SQLALCHEMY_DATABASE_URI = 'sqlite://'
    TOKEN_EXPIRATION_TIME = 3600

    # Define the application directory
    import os
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))

    # Log file (the directory must exist)
    APPLICATION_LOG = os.path.join(BASE_DIR, 'log', 'application.log')
    ACCESS_LOG = os.path.join(BASE_DIR, 'log', 'access.log')

    # Secret key for flask sessions and CSRF protection
    SECRET_KEY = "secret key that you need to change, seriously!"

    # Do not check CSRF by default
    WTF_CSRF_CHECK_DEFAULT = False


class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = 'mysql://user@localhost/foo'


class DevelopmentConfig(Config):
    SQLALCHEMY_DATABASE_URI = "postgresql://test:test123@localhost/flask"
    DEBUG = True


class TestingConfig(Config):
    PRESERVE_CONTEXT_ON_EXCEPTION = False
    TESTING = True
    DEBUG = True


# Default configuration
default = DevelopmentConfig
