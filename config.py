class Config(object):
    DEBUG = False
    TESTING = False
    SQLALCHEMY_DATABASE_URI = 'sqlite://:memory:'

    # Define the application directory
    import os
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = 'mysql://user@localhost/foo'


class DevelopmentConfig(Config):
    SQLALCHEMY_DATABASE_URI = "postgresql://test:test123@localhost/flask"
    DEBUG = True


class TestingConfig(Config):
    TESTING = True


# Default configuration
default = DevelopmentConfig
