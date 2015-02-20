from flask import request, jsonify, abort
from app import app, api, auth as provider, db
from models import Application, Client

from oauth import OAuth2Exception


# Authorization Code
# Returns a redirect header on success
# Based on http://tech.shift.com/post/39516330935/implementing-a-python-oauth-2-0-provider-part-1
@app.route("/v1/oauth2/auth", methods=["GET"])
def authorization_code():
    raise OAuth2Exception("unsupported_grant_type")


# Token exchange
# Returns JSON token information on success
# Based on http://tech.shift.com/post/39516330935/implementing-a-python-oauth-2-0-provider-part-1
@app.route("/v1/oauth2/token", methods=["POST"])
def token():
    # Get a dict of POSTed form data
    data = {k: d[k] for d in [request.json, request.form] for k in d.iterkeys()}

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
