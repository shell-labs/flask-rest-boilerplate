from flask import request, jsonify, abort
from app import app, api, auth as provider, db
from models import Application, Client, Role

from app.restful import BadRequest

from oauth import OAuth2Exception


@api.resource('/v1/client/')
class ClientResource:
    aliases = {
        'client_id': 'id',
        'client_secret': 'secret',
    }

    @api.public
    def create(self):
        app_key = self.data.get('app_key', None)
        if not app_key:
            raise BadRequest("Must provide a valid app_key to create a client")

        app = Application.query.get(app_key)
        if not app:
            raise NotFound("Must provide a valid app_key to create a client")

        client = Client(app_key=app_key)
        db.session.add(client)
        db.session.commit()

        return client

    @api.grant(Role.ADMIN)
    def list(self):
        pass


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
