from models import User
from app.auth.models import Grant


from app import api


@api.resource('/v1/user/')
class UserResource:
    aliases = {
        'id': 'id',
        'created': 'created',
        'modified': 'modified'
        'email': 'email'
    }

    @api.grant(Grant.ADMIN)
    def list(self):
        """Lists all users"""
        return User.query.all()

    @api.grant(Grant.ADMIN, Grant.USER)
    def detail(self, pk):
        return User.query.get(pk)
