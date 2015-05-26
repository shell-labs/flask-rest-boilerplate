from __future__ import absolute_import
from __future__ import unicode_literals
import sqlalchemy.dialects.postgresql
import uuid
import sqlalchemy.types as types
import six

try:
    # Check if the psycopg2 module exists
    import psycopg2.extras

    # Required for PostgreSQL to accept UUID type.
    psycopg2.extras.register_uuid()
except ImportError:
    pass


class ChoiceType(types.TypeDecorator):
    impl = types.String
    python_type = str

    def __init__(self, choices, **kw):
        self.choices = dict(choices)
        super(ChoiceType, self).__init__(**kw)

    def process_bind_param(self, value, dialect):
        chosen = [k for k, v in six.iteritems(self.choices) if v == value]
        if len(chosen) > 0:
            return chosen[0]

        return None

    def process_result_value(self, value, dialect):
        if value:
            return self.choices[value]
        return None


class StringListType(types.TypeDecorator):
    """Defines a value limited string list to be stored on database

    The list is stored as a comma-separated string and it is
    converted to a list upon loading.

    When creating the column, an allowed values list must be provided
    to the constructor

    ```
    from app import db

    ROLES = ('user', 'admin', 'reporter')

    class User(db.Model):
        roles = db.Column(StringListType(ROLES))
    ```
    """

    impl = types.String
    python_type = list

    def __init__(self, allowed, separator=',', **kw):
        self.allowed = tuple(allowed)
        self.separator = separator
        super(StringListType, self).__init__(**kw)

    def process_bind_param(self, value, dialect):
        return self.separator.join([v for v in value if v in self.allowed])

    def process_result_value(self, value, dialect):
        return [v for v in value.split(self.separator) if v in self.allowed]


class UUID(types.TypeDecorator):
    """ Converts UUID to string before storing to database.
        Converts string to UUID when retrieving from database. """

    impl = types.TypeEngine

    def load_dialect_impl(self, dialect):
        """ When using Postgres database, use the Postgres UUID column type.
            Otherwise, use String column type. """
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(sqlalchemy.dialects.postgresql.UUID)

        return dialect.type_descriptor(types.String)

    def process_bind_param(self, value, dialect):
        """ When using Postgres database, check that is a valid uuid and
            store as UUID object.
            Otherwise, convert to string before storing to database. """

        if value is None:
            return value

        if not isinstance(value, UUID):
            # Try to convert to UUID to check validity
            value = uuid.UUID(value)

        if dialect.name == 'postgres':
            return value

        return str(value).replace('-', '')

    def process_result_value(self, value, dialect):
        """ When using Postgres database, convert to string before returning value.
            Otherwise, provide as is. """
        if dialect.name == 'postgresql':
            return str(value).replace('-', '')

        if value is None:
            return value

        return value
