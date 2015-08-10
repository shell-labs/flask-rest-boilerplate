from __future__ import absolute_import
from __future__ import unicode_literals
from flask import request, jsonify, abort, redirect, flash, render_template
from app import app, api, auth as provider, db
from .models import Application, Client

from flask.ext.login import login_required

from .oauth import OAuth2Exception
from .forms import AuthorizationForm
import six


# Authorization Code
# Returns a redirect header on success
# Based on http://tech.shift.com/post/39516330935/implementing-a-python-oauth-2-0-provider-part-1
@app.route("/v1/oauth2/auth", methods=["GET", "POST"])
@login_required
def authorization_code():
    # Get a dict of POSTed form data
    data = {k: d[k] for d in [request.form, request.args] for k in six.iterkeys(d or {})}

    # Validate query data first
    error_uri = provider.check_authorization_details_from_query_data(data)

    # If we have an error in the request, send response immediately
    if error_uri is not None:
        return redirect(error_uri, 302)

    # Request authorization from client
    form = AuthorizationForm()
    if form.validate_on_submit():
        data['access_granted'] = form.yes.data

        # This is the important line
        redirect_uri = provider.get_authorization_uri(**data)

        # Redirect to the return URI (it can be an error or a success response)
        return redirect(redirect_uri, 302)

    app, owner = provider.get_client_details(data.get('client_id'))

    return render_template('authorize.html', form=form, app=app, owner=owner)


# Token exchange
# Returns JSON token information on success
# Based on http://tech.shift.com/post/39516330935/implementing-a-python-oauth-2-0-provider-part-1
@app.route("/v1/oauth2/token", methods=["POST"])
def token():
    # Get a dict of POSTed form data
    data = {k: d[k] for d in [request.json, request.form, request.args] for k in six.iterkeys(d or {})}

    # This is the important line
    credentials = provider.get_token_from_post_data(data)

    # Convert the response to a json response
    response = jsonify(credentials)
    response.headers['Content-Type'] = 'application/json;charset=UTF-8'
    response.headers['Cache-Control'] = 'no-store'
    response.headers['Pragma'] = 'no-cache'

    return response


@app.errorhandler(OAuth2Exception)
def oauth2_error(error):
    response = jsonify(error.to_dict())
    response.headers['Content-Type'] = 'application/json;charset=UTF-8'
    response.headers['Cache-Control'] = 'no-store'
    response.headers['Pragma'] = 'no-cache'
    response.status_code = error.status_code
    return response
