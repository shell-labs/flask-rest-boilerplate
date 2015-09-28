from __future__ import absolute_import
from __future__ import unicode_literals
from app import app, db, oauth, csrf, api
from flask import request
from flask.ext.login import current_user, login_user, login_required, logout_user
from app.util import is_safe_url
from app.constants import Genders
from .forms import LoginForm
from .models import Client, Grant, User, Token, UserDetails
from datetime import datetime, timedelta


@oauth.clientgetter
def load_client(client_id):
    return Client.query.filter_by(client_id=client_id).first()


@oauth.grantgetter
def load_grant(client_id, code):
    return Grant.query.filter_by(client_id=client_id, code=code).first()


@oauth.grantsetter
def save_grant(client_id, code, request, *args, **kwargs):
    # decide the expires time yourself
    expires = datetime.utcnow() + timedelta(seconds=100)
    grant = Grant(
        client_id=client_id,
        code=code['code'],
        redirect_uri=request.redirect_uri,
        _scopes=' '.join(request.scopes),
        user=current_user,
        expires=expires
    )
    db.session.add(grant)
    db.session.commit()
    return grant


@oauth.tokengetter
def load_token(access_token=None, refresh_token=None):
    if access_token:
        tok = Token.query.filter_by(access_token=access_token).first()
        print(str(tok.scopes))
        return tok
    elif refresh_token:
        return Token.query.filter_by(refresh_token=refresh_token).first()


@oauth.tokensetter
def save_token(token, request, *args, **kwargs):
    toks = Token.query.filter_by(client_id=request.client.client_id,
                                 user_id=request.user.id)
    # make sure that every client has only one token connected to a user
    for t in toks:
        db.session.delete(t)

    expires_in = token.get('expires_in')
    expires = datetime.utcnow() + timedelta(seconds=expires_in)

    tok = Token(
        access_token=token['access_token'],
        refresh_token=token['refresh_token'],
        token_type=token['token_type'],
        _scopes=token['scope'],
        expires=expires,
        client_id=request.client.client_id,
        user_id=request.user.id,
    )
    db.session.add(tok)
    db.session.commit()
    return tok


@oauth.usergetter
def get_user(username, password, *args, **kwargs):
    user, authenticated = User.authenticate(username, password)
    if authenticated:
        return user
    return None


@app.route('/', endpoint='index')
def index():
    return "IT WORKS!!"


@app.route('/login', methods=['GET', 'POST'])
def login():
    # Protect with csrf
    csrf.protect()

    # Here we use a class of some kind to represent and validate our
    # client-side form data. For example, WTForms is a library that will
    # handle this for us.
    form = LoginForm()
    if form.validate_on_submit():
        # Login and validate the user.
        login_user(form.user)

        flask.flash('Logged in successfully.')

        next = flask.request.args.get('next')
        if not is_safe_url(next):
            return flask.abort(400)

        return flask.redirect(next or flask.url_for('index'))

    return flask.render_template('login.html', form=form)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    next = flask.request.args.get('next')
    if not is_safe_url(next):
        return flask.abort(400)

    return flask.redirect(next or flask.url_for('index'))


@app.route('/v1/oauth2/auth', methods=['GET', 'POST'])
@login_required
@oauth.authorize_handler
def authorize(*args, **kwargs):
    if request.method == 'GET':
        client_id = kwargs.get('client_id')
        client = Client.query.filter_by(client_id=client_id).first()
        kwargs['app'] = client.app
        kwargs['owner'] = client.user
        return render_template('authorize.html', **kwargs)

    confirm = request.form.get('confirm', 'no')
    return confirm == 'yes'


@app.route('/v1/oauth2/token', methods=['POST'])
@oauth.token_handler
def access_token():
    return None


@app.route('/v1/oauth2/revoke', methods=['POST'])
@oauth.revoke_handler
def revoke_token():
    pass


@api.resource('/v1/user/')
class UserResource:
    aliases = {
        'id': 'username',
        'created': 'created',
        'modified': 'details.modified',
        'email': 'email',
        'name': 'details.name',
        'url': 'details.url',
        'bio': 'details.bio',
        'born': 'details.born',
        'gender': 'details.gender',
    }

    @api.admin
    def list(self):
        """Lists all users"""
        return User.query.all()

    # /v1/user/<pk>/
    @api.scopes('user')
    def detail(self, pk):
        if request.user.is_admin:
            return User.query.filter(User.username == pk).first()

        if request.user.get_id() == pk:
            return request.user

        raise Unauthorized('Only admins and data owners can view user data')

    @api.admin
    def create(self):
        # Check
        for s in ['email', 'password']:
            if not self.data.get(s, None):
                raise BadRequest("Missing required parameter %s" % s)

        user = User(
            email=self.data.get('email'),
            password=self.data.get('password')
        )

        # Always create details
        gender = self.data.get('gender', None)
        if gender and gender not in Genders:
            raise BadRequest(("Gender must be one of (" + ','.join(["'%s'"] * len(Genders)) + ")") % tuple(Genders))

        user.details = UserDetails(
            name=self.data.get('name', None),
            url=self.data.get('url', None),
            bio=self.data.get('bio', None),
            born=self.data.get('born', None),
            gender=gender,
            user=user
        )
        db.session.add(user)
        db.session.commit()

        return user

    @api.scopes('user')
    def update(self, pk):
        user = User.query.filter(User.username == pk).first()
        if not user:
            raise NotFound("Cannot update non existing object")

        if not request.user.is_admin and request.user.id != user.id:
            raise Unauthorized('Only administrators and data owners can update user data')

        # Can only update password
        user.password = self.data.get('password', user.password)

        gender = self.data.get('gender', user.details.gender)
        if gender and gender not in Genders:
            raise BadRequest(("Gender must be one of (" + ','.join(["'%s'"] * len(Genders)) + ")") % tuple(Genders))

        # Update user details
        user.details.name = self.data.get('name', user.details.name)
        user.details.url = self.data.get('url', user.details.url)
        user.details.bio = self.data.get('bio', user.details.url)
        user.details.born = self.data.get('born', user.details.born)
        user.details.gender = gender
        db.session.add(user.details)

        db.session.add(user)
        db.session.commit()

        return user
