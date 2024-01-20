from cs50 import SQL
from flask import Flask
from flask_session import Session
import os

from helpers import usd

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

def create_app():
    # Configure application
    app = Flask(__name__)

    # Custom filter
    app.jinja_env.filters["usd"] = usd

    ALLOWED_EXTENSIONS = ['png', 'jpg', 'jpeg', 'gif']
    UPLOAD_FOLDER = os.path.join(app.root_path, 'static/imgs/profile')

    # Configure session to use filesystem (instead of signed cookies)
    app.config["SESSION_PERMANENT"] = False
    app.config["SESSION_TYPE"] = "filesystem"
    app.config["SECRET_KEY"] = "SasidfSDASDFdsifj2908oiu2039oi!@#$Ds"
    app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

    Session(app)

    from website.routes import all_routes
    app.register_blueprint(all_routes)

    return app