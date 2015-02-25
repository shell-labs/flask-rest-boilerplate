from models import User
from app.auth.models import Grant

from app import api, db
from app.restful import Unauthorized, BadRequest, NotFound
from app.constants import Roles


@api.resource('/v1/user/')
class UserResource:
    aliases = {
        'id': 'username',
        'created': 'created',
        'modified': 'modified',
        'email': 'email'
    }

    @api.grant(Roles.ADMIN)
    def list(self):
        """Lists all users"""
        return User.query.all()

    # /v1/user/<pk>/
    @api.grant(Roles.ADMIN, Roles.USER)
    def detail(self, pk):
        if Grant.check_grant(self.user, Roles.ADMIN):
            return User.query.filter(User.username == pk).first()

        if self.user.username == pk:
            return self.user

        raise Unauthorized('Only admins and data owners can view user data')

    @api.grant(Roles.ADMIN)
    def create(self):
        # Check
        for s in ['email', 'password']:
            if not self.data.get(s, None):
                raise BadRequest("Missing required parameter %s" % s)

        user = User(
            email=self.data.get('email'),
            password=self.data.get('password')
        )
        db.session.add(user)

        # Create user role. The default is Grant.USER
        role = self.data.get('role', None)
        if not role:
            db.session.add(Grant(user=user, role=Roles.USER))
        elif len([v for v in Roles if role == v]) > 0:
            db.session.add(Grant(user=user, role=role))
        else:
            raise BadRequest('Unknown role %s' % role)

        db.session.commit()

        return user

    @api.grant(Roles.ADMIN, Roles.USER)
    def update(self, pk):
        user = User.query.filter(User.username == pk).first()
        if not user:
            raise NotFound("Cannot update non existing object")

        if not Grant.check_grant(self.user, Roles.ADMIN) and self.user.id != user.id:
            raise Unauthorized('Only administrators and data owners can update user data')

        # Can only update password
        user.password = self.data.get('password', user.password)

        db.session.add(user)
        db.session.commit()

        return user
