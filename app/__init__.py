from __future__ import absolute_import
from __future__ import unicode_literals
# Import flask and template operators
from flask import Flask, render_template, request

# Import SQLAlchemy
from flask.ext.sqlalchemy import SQLAlchemy

# Define the WSGI application object
app = Flask(__name__)

# Configurations
app.config.from_object('config.default')

# Define the database object which is imported
# by modules and controllers
db = SQLAlchemy(app)

# Authentication
# from .auth import AuthProvider
# auth = AuthProvider(app)

from flask_oauthlib.provider import OAuth2Provider
oauth = OAuth2Provider(app)

# CSRF protection for forms
from flask.ext.wtf.csrf import CsrfProtect

csrf = CsrfProtect()
csrf.init_app(app)

# Login Manager
from flask.ext.login import LoginManager
from .auth.models import User

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


# Tell the login manager how to find the user
@login_manager.user_loader
def load_user(userid):
    return User.query.filter_by(username=userid).first()


# Rest API
from .restful import Api
api = Api(app, oauth)

# Configure logging
import logging
from logging.handlers import TimedRotatingFileHandler
from logging import Formatter

# Configure the application log
if app.config.get('APPLICATION_LOG', None):
    application_log_handler = TimedRotatingFileHandler(app.config.get('APPLICATION_LOG'), 'd', 7)
    application_log_handler.setLevel(logging.INFO)
    application_log_handler.setFormatter(Formatter(
        '%(asctime)s %(levelname)s: %(message)s '
        '[in %(pathname)s:%(lineno)d]'
    ))
    app.logger.addHandler(application_log_handler)


# Configure the access log if defined in the configuration
if app.config.get('ACCESS_LOG', None):
    access_log = logging.getLogger('access_log')
    access_log_handler = TimedRotatingFileHandler(app.config.get('ACCESS_LOG'), 'd', 7)
    access_log_handler.setLevel(logging.INFO)
    access_log_handler.setFormatter(Formatter('%(asctime)s   %(message)s'))
    access_log.addHandler(access_log_handler)

    @app.before_request
    def pre_request_logging():
        # Log except when testing
        if not app.config.get('TESTING'):
            access_log.info('\t'.join([
                request.remote_addr,
                request.method,
                request.url,
                str(request.data)])
            )


# Sample HTTP error handling
@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

# Import modules
from app.auth import views as auth_views
