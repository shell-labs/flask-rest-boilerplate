from __future__ import absolute_import
from __future__ import unicode_literals
from flask.ext.script import Manager
from flask.ext.migrate import Migrate, MigrateCommand
from app import app, db
from app.user.models import User, Grant
from app.auth.models import Application, Client
from app.constants import Roles

import sys
import getpass

migrate = Migrate(app, db)

manager = Manager(app)
manager.add_command('db', MigrateCommand)

NewCommand = Manager(usage='Create resources on database')
manager.add_command('new', NewCommand)


def query_yes_no(question, default="yes"):
    """Ask a yes/no question via raw_input() and return their answer.

    "question" is a string that is presented to the user.
    "default" is the presumed answer if the user just hits <Enter>.
        It must be "yes" (the default), "no" or None (meaning
        an answer is required of the user).

    The "answer" return value is True for "yes" or False for "no".

    Source: http://stackoverflow.com/questions/3041986/python-command-line-yes-no-input
    """
    valid = {"yes": True, "y": True, "ye": True,
             "no": False, "n": False}
    if default is None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while True:
        sys.stdout.write(question + prompt)
        choice = raw_input().lower()
        if default is not None and choice == '':
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            sys.stdout.write("Please respond with 'yes' or 'no' "
                             "(or 'y' or 'n').\n")


def query(question, default=None, required=True):
    """Request a data prompt through raw_input() and return the answer.
    If default is set and the user does not enter an input, then default
    value will be used for the answer"""

    prompt = ": "
    if default is not None:
        prompt = " [%s]: " % default

    while True:
        sys.stdout.write(question + prompt)
        response = raw_input()

        if response:
            return response
        elif default is not None:
            return default
        elif not required:
            return None


def query_password():
    password = None
    while True:
        password = getpass.getpass('Password: ')
        password2 = getpass.getpass('Re-type: ')
        if (password != password2):
            print("Passwords do not match")
        else:
            return password


@MigrateCommand.command
def create():
    "Initialize the database"
    db.create_all()


@MigrateCommand.command
def populate(sample_data=False):
    "Populate database with default data"
    pass


def request_user_details():
    pass


@NewCommand.command
def admin(email):
    """Create an administrator account"""

    # Check if the user already exists
    user = User.query.filter(User.email == email).first()
    if not user:
        user = User(email=email)
        user.password = query_password()
        db.session.add(user)
    else:
        sys.stdout.write("User '%s' already exists " % email)

    if not Grant.check_grant(user, Roles.ADMIN):
        if query_yes_no(", are you sure you want to grant admin rights?" % email, default="no"):
            db.session.add(Grant(user=user, role=Roles.ADMIN))
            db.session.commit()
            print("User with email '%s' is now an administrator" % email)
        else:
            return "Command cancelled"

    print("and is an administrator")


@NewCommand.command
def application(email):
    """Create an application for used identifier by the specified email"""

    # Check if the user exists
    user = User.query.filter(User.email == email).first()
    if not user:
        return "User with email '%s' does not exist" % email

    application = Application.query.filter(Application.owner == user).first()
    operation = "updated"
    if application is None:
        operation = "created"
        application = Application()
    elif not query_yes_no("An application already exists for user %s, do you want to edit it?" % email, default="yes"):
        return "The operation has been cancelled"

    application.name = query('Application name', default=application.name)

    description = query('Describe your application (200 chars max)', default=application.description, required=False)
    description = (description[:200]) if description and len(description) > 200 else description
    application.description = description

    application.url = query('Give a URL for your application', default=application.url)

    application.owner = user

    db.session.add(application)
    db.session.commit()

    return "The application with id %s for user %s has been %s" % (application.id, email, operation)


@NewCommand.option('-a', '--app', help="Applicaton id", dest='app_id')
@NewCommand.option('-c', '--client', help="Id of the client to edit", dest='client_id')
def client(app_id=None, client_id=None):
    """Create/edit a client for the specified app id"""

    # Check if the app exists
    application = None

    if app_id:
        application = Application.query.get(app_id)
        if not application:
            return "Application with id '%s' does not exist" % app_id

    client = None
    if client_id:
        client = Client.query.get(client_id)
    elif application is None:
        return "An application id is required to create a new client"

    operation = "updated"
    if client is None:
        operation = "created"
        client = Client()
    elif not query_yes_no("Are you sure you want to edit the client with id %s?" % client.id, default="yes"):
        return "The operation has been cancelled"
    else:
        application = client.app

    client.name = query('Provide client name for application \'%s\'' % application.name, default=client.name)
    client.redirect_uri = query('Redirect URI', default=client.redirect_uri)
    client.app = application

    db.session.add(client)
    db.session.commit()

    return "The client with id %s has been %s" % (client.id, operation)


@manager.command
def passwd(email):
    """Change a user password"""
    # Check if the user already exists
    user = User.query.filter(User.email == email).first()
    if user:
        if query_yes_no("Are you sure you want to change the password for user '%s'?" % email, default="no"):
            user.password = query_password()
            db.session.add(user)
            db.session.commit()
            return "Password has been changed for user '%s'"
        else:
            return "Command cancelled"

    print("User with email '%s' does not exist" % email)

if __name__ == '__main__':
    manager.run()
