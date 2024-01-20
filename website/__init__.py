from gettext import find
from cs50 import SQL
from flask import Flask, render_template, session
from flask_session import Session
import os, base64

from helpers import apology, usd, login_required
from website.utils import calculate_total_holding, find_value_in_object, remove_duplicates, clear_tmp_profile_dir


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

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


@app.route("/")
@login_required
def index():
    # delete all the temporarily saved pictures
    clear_tmp_profile_dir()
    
    """Show portfolio of stocks"""
    
    current_user_id = session["user_id"]
    user_info = db.execute("SELECT username, cash FROM users WHERE id = ?;", current_user_id)
    
    # get the amount of cash and the share from each distinct transaction that occured
    amount_and_share_sum = db.execute(
        """
            SELECT SUM(
                DISTINCT(
                    user_stocks.share
                )
            )
            AS share_sum, 
            SUM(
                DISTINCT(
                    transactions.amount
                )
            )
            AS stock_sum 
            FROM transactions
            JOIN user_stocks 
            ON transactions.user_id = ? 
            AND 
            transactions.user_id = user_stocks.user_id
            AND 
            user_stocks.stock_symbol = transactions.stock_symbol
            AND 
            user_stocks.user_id = ?;
        """,
        current_user_id,
        current_user_id
    )
    
    # query the database for the user's profile picture if there is any
    profile_picture = db.execute("SELECT picture FROM profiles WHERE user_id = ?;", current_user_id)
    
    # set the profile picture var to None and let the condition in the Jinja Template take of the rest of the logic
    if len(profile_picture) <= 0:
        profile_picture = None
    else:
        # otherwise convert image to base64
        profile_picture = base64.b64encode(profile_picture[0]['picture']).decode('utf-8')
        
        # create a new dict in the session if it does not already exists
        if session.get('user_profile_info') is None:
            session['user_profile_info'] = {}
            
        # store user profile picture in the session
        session['user_profile_info'] = {
            'user_id': current_user_id,
            'picture': profile_picture
        }
    
    username = user_info[0]['username']
    account_balance = user_info[0]['cash']
    
    full_stock_information = db.execute(
        """
            SELECT DISTINCT 
            user_stocks.share,
            user_stocks.stock_symbol, 
            transactions.amount
            FROM transactions 
            JOIN user_stocks 
            ON transactions.user_id = ? 
            AND 
            transactions.user_id = user_stocks.user_id 
            AND 
            user_stocks.stock_symbol = transactions.stock_symbol 
            AND 
            user_stocks.user_id = ?;
        """, 
        current_user_id, 
        current_user_id
    )
    
    full_stock_information = remove_duplicates(full_stock_information)
    
    return render_template(
        "index.html",
        username=username,
        account_balance=round(account_balance, 2), 
        amount_and_share_sum=amount_and_share_sum,
        full_stock_information=full_stock_information, 
        all_holding_sum=calculate_total_holding(full_stock_information=full_stock_information), 
        profile_picture=profile_picture
    )


@app.errorhandler(404)
def page_not_found(error):
    return apology(message="Page not Found!", code=404)


@app.errorhandler(500)
def server_error(error):
    return apology(message="Server Error", code=500)

@app.context_processor
def inject_functions():
    return dict(find_value_in_object=find_value_in_object)

from website import routes