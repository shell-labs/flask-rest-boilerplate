from __future__ import absolute_import
from __future__ import unicode_literals

from flask.ext.wtf import Form
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email

from .models import User


class LoginForm(Form):
    email = StringField('email', validators=[DataRequired(), Email()])
    password = PasswordField('password', validators=[DataRequired()])

    def validate(self):
        if not Form.validate(self):
            return False

        user, authenticated = User.authenticate(self.email.data.lower(), self.password.data)
        if authenticated:
            self.user = user
            return True
        else:
            self.email.errors.append("Invalid e-mail or password")
            return False
