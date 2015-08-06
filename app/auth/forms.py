from __future__ import absolute_import
from __future__ import unicode_literals

from flask.ext.wtf import Form
from wtforms import SubmitField


class AuthorizationForm(Form):
    yes = SubmitField('yes', )
    no = SubmitField('no', )
