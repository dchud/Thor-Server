import os
from flask import Flask
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
from flask_bcrypt import Bcrypt
from flask_login import LoginManager


# Initialize app.
app = Flask(__name__, instance_relative_config=True)
# App configurations.
basedir = os.path.abspath(os.path.dirname(__file__))
# Load the default configuration
app.config.from_object('website.config')
# Check for a local configuration from instance/local_config.py
app.config.from_pyfile('local_config.py', silent=True)

# Add-ons for the app.
bootstrap = Bootstrap(app)
db = SQLAlchemy(app)
mail = Mail(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = "login.login_page"


# Load in the blueprints for individual pages. Notice that we have to perform
# the views import at this late stage after all of the other dependencies have
# been created (namely the database).
from .views import blueprints
from .models import User

for blueprint in blueprints:
    app.register_blueprint(blueprint)


# This callback is used to reload the user object from the user ID stored in
# the session.
@login_manager.user_loader
def load_user(user_id):
    return User.query.filter_by(id=user_id).first()
