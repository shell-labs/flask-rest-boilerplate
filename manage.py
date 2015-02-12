from flask.ext.script import Manager
from flask.ext.migrate import Migrate, MigrateCommand
from app import app, db

migrate = Migrate(app, db)

manager = Manager(app)
manager.add_command('db', MigrateCommand)


@MigrateCommand.command
def populate(sample_data=False):
    "Populate database with default data"
    pass


if __name__ == '__main__':
    manager.run()
