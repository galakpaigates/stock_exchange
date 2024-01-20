import os
from flask import flash, redirect, render_template, request, session, url_for, Blueprint
from datetime import datetime
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from helpers import login_required, lookup

from website import db
from website.utils import *


MORE_OPTIONS = [
    "password",
    "add-cash",
    "profile-picture"
]

all_routes = Blueprint("all_routes", __name__)


@all_routes.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@all_routes.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    
    if request.method == "POST":
        
        form_data = request.form
        
        symbol = form_data.get("symbol")
        lookup_response = lookup(symbol)
        
        if lookup_response == None:
            flash(message="Invalid Symbol!", category='error')
            return render_template("buy.html", symbol=symbol)
        
        shares = form_data.get("shares")
        
        if shares == None:
            flash(message="Invalid Symbol!", category='error')
            return render_template("buy.html", symbol=symbol)
        
        try:
            shares = float(shares)
            if shares < 0.0001:
                raise ValueError()
            
        except ValueError:
            flash(message="Shares should be an real number greater than 0!", category='error')
            return render_template("buy.html", symbol=symbol, shares=shares)
    
        current_user_id = session["user_id"] # get current user's id
        
        cash = float(db.execute("SELECT cash FROM users WHERE id = ?;", current_user_id)[0]['cash']) # get user's current account balance
        stock_price = float(lookup_response['price']) # lookup stock's price
        
        cash -= stock_price
        stock_symbol = lookup_response['name']
        
        if cash < 0:
            flash(message="Ur mah na reach! U jeh na make it!", category="error")
            return render_template('buy.html', shares=shares, symbol=symbol)
        
        # watch out for race conditions
        db.execute("BEGIN;")

        # subtract the stock price from the user's amount and record the transaction in the database
        try:
            db.execute("UPDATE users SET (cash) = ? WHERE id = ?;", cash, current_user_id)
            db.execute("INSERT INTO transactions (user_id, type, stock_symbol, share, amount, datetime) VALUES (?, ?, ?, ?, ?, ?);", current_user_id, "BUY", stock_symbol, shares, stock_price, datetime.now().strftime("%Y-%m-%d %H:%M"))
            
            existing_stock = db.execute("SELECT stock_symbol, share FROM user_stocks WHERE user_id = ? AND stock_symbol = ?;", current_user_id, stock_symbol)

            # add a new stock if the user does not already have a share in that stock
            if len(existing_stock) == 0:
                db.execute("INSERT INTO user_stocks (user_id, stock_symbol, share) VALUES (?, ?, ?);", current_user_id, stock_symbol, shares)

                db.execute("COMMIT;")        
                return redirect(url_for("index"))
                
            db.execute("UPDATE user_stocks SET (share) = ? WHERE user_id = ? AND stock_symbol = ?;", shares + existing_stock[0]['share'], current_user_id, stock_symbol)

            
        except RuntimeError:
            flash(message="Transaction not completed, Try again!", category="error")
            return render_template('buy.html', shares=shares, symbol=symbol)
            
        db.execute("COMMIT;")
        return redirect(url_for("index"))
    
    return render_template("buy.html")


@all_routes.route("/history", methods=["GET"])
@login_required
def history():
    """Show history of transactions"""
    
    full_transaction_history = db.execute("SELECT * FROM transactions WHERE user_id = ?;", session['user_id'])
        
    return render_template("history.html", full_transaction_history=full_transaction_history)


@all_routes.route("/login", methods=["GET", "POST"])
def login():
    print(len(session))
    if session.get("user_id") is None:
        flash("Login required to purchase and sell stocks and access more features of the site!")
        
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")

        # Ensure username was submitted
        if not username or username == None:
            flash("Username is required!")
            return render_template("login.html", username=username, password=password)

        # Ensure password was submitted
        elif not password or password == None:
            flash("Password is required!")
            return render_template("login.html", username=username, password=password)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", username)

        # Ensure username exists and password is correct
        if len(rows) != 1:
            flash("Username does not exist!")
            return render_template("login.html", username=username, password=password)
        
        elif not check_password_hash(rows[0]["hash"], password):
            flash("Incorrect Password!")
            return render_template("login.html", username=username, password=password)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect(url_for("index"))

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@all_routes.route("/logout", methods=['GET'])
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect(url_for("index"))


@all_routes.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    
    if request.method == "POST":
        
        symbol = request.form.get("symbol")
        lookup_response = lookup(symbol)
        
        if lookup_response == None:
            flash(message="Invalid Symbol!", category='error')
            return render_template("quote.html", symbol=symbol)
        
        return render_template("quote.html", lookup_response=lookup_response)
    
    return render_template("quote.html")


@all_routes.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    
    if request.method == "POST":
    
        form_data = request.form
        
        username = form_data.get("name")
        password = form_data.get("password")
        confirm_password = form_data.get("confirm_password")
        
        if username == None:
            flash(message="Userame is required!", category="error")
            return render_template("register.html", username=username, password=password, confirm_password=confirm_password)
        
        elif db.execute("SELECT * FROM users WHERE username = ?;", username):
            flash(message="Username is taken!")
            return render_template("register.html", username=username, password=password, confirm_password=confirm_password)
        
        elif password == None or len(password) < 5:
            flash(message="Password must be atleast 5 characters!", category="error")
            return render_template("register.html", username=username, password=password, confirm_password=confirm_password)
        
        elif password != confirm_password:
            flash(message="Passwords don't match!", category="error")
            return render_template("register.html", username=username, password=password, confirm_password=confirm_password)
        
        # register user in the database
        db.execute("INSERT INTO users (username, hash) VALUES (?, ?);", username, generate_password_hash(password=password, method='pbkdf2:sha512:600000'))
        
        flash(message="Account created!", category="success")
        return redirect(url_for("all_routes.login"))
    
    return render_template("register.html")


@all_routes.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    
    current_user_id = session['user_id']
    all_user_stocks = db.execute("SELECT DISTINCT(stock_symbol) FROM transactions WHERE user_id = ?;", current_user_id)
    
    if request.method == "POST":
        form_data = request.form
        
        # get the fields of the form (stock and shares)
        stock_to_sell = form_data.get("symbol")
        shares = form_data.get("shares")
        
        # ensure the user selected a stock
        if stock_to_sell == None:
            flash(message="Please Select a Stock to Sell!", category="error")
            return render_template("sell.html", all_user_stocks=all_user_stocks, symbol=stock_to_sell, shares=shares)

        # convert to upper case to ensure ease of comparison and assignment
        stock_to_sell = stock_to_sell.upper()

        # ensure the user gave a share
        if shares == None:
            flash(message="Please Input Number of Shares to Sell!", category="error")
            return render_template("sell.html", all_user_stocks=all_user_stocks, symbol=stock_to_sell, shares=shares)
        
        # convert shares to float and handle ValueError
        try:
            shares = float(shares)
            if shares < 0.0001:
                raise ValueError()
            
        except ValueError:
            flash(message="Shares should be an real number greater than 0!", category='error')
            return render_template("sell.html", all_user_stocks=all_user_stocks, symbol=stock_to_sell, shares=shares)
        
        # get the current user's amount of share
        share_sum = float(db.execute("SELECT SUM(share) AS share_sum FROM user_stocks WHERE user_id = ? AND stock_symbol = ?;", current_user_id, stock_to_sell)[0]['share_sum'])
        
        # ensure the user has sufficient share to sell
        if share_sum < shares:
            flash(message="Insufficient Share! U jeh na make it!", category="error")
            return render_template("sell.html", all_user_stocks=all_user_stocks, symbol=stock_to_sell, shares=shares)
        
        # get current user's cash
        cash = float(db.execute("SELECT cash FROM users WHERE id = ?;", current_user_id)[0]['cash'])

        lookup_response = lookup(stock_to_sell)
        
        # ensure the stock is valid
        if lookup_response == None:
            flash(message="Invalid Stock Symbol!", category="error")
            return render_template("sell.html", all_user_stocks=all_user_stocks, symbol=stock_to_sell, shares=shares)
    
        # get the price of the stock about to be purchased
        stock_price = float(lookup_response['price'])

        # add the stock to the current user's account
        cash += stock_price
        share_sum -= shares
        
        # watch out for race conditions
        db.execute("BEGIN;")

        # record the transaction in the database
        try:
            db.execute("UPDATE users SET (cash) = ? WHERE id = ?;", cash, current_user_id) # update user's cash
            db.execute("INSERT INTO transactions (user_id, type, stock_symbol, amount, share, datetime) VALUES (?, ?, ?, ?, ?, ?);", current_user_id, "SELL", stock_to_sell, stock_price, shares, datetime.now().strftime('%Y-%m-%d %H:%M')) # record transaction

            db.execute("UPDATE user_stocks SET (share) = ? WHERE user_id = ? AND stock_symbol = ?;", share_sum, current_user_id, stock_to_sell)
        
        # handle error
        except RuntimeError:
            flash(message="Transaction not completed, Try again!", category="error")
            return render_template("sell.html", all_user_stocks=all_user_stocks, symbol=stock_to_sell, shares=shares)
            
        # success
        db.execute("COMMIT;")
        flash(message="Share Successfully Sold!", category="success")
        return redirect(url_for("index"))
            
    
    return render_template("sell.html", all_user_stocks=all_user_stocks)


@all_routes.route("/more", methods=['GET', 'POST'])
@login_required
def more():
    
    # handle submitted forms
    if request.method == "POST":
        form_data = request.form
        
        current_user_id = session['user_id']
        
        # change account password
        if len(form_data) == 3  and (request.form.get("old_password") or request.form.get("new_password") or request.form.get("confirm_password")):
            
            old_password = form_data.get("old_password")
            new_password = form_data.get("new_password")
            confirm_password = form_data.get("confirm_password")
            
            current_hashed_password = password=db.execute("SELECT hash FROM users WHERE id = ?;", current_user_id)[0]['hash']
            
            # ensure proper old_password
            if old_password == None or len(old_password) < 5:
                flash('Old Password must be atleast 5 characters!')
                return render_template('more.html', dynamic_route='password', old_password=old_password, new_password=new_password, confirm_password=confirm_password)
            
            # check if new_password matched
            elif new_password == None or len(new_password) < 5:
                flash('New Password must be atleast 5 characters!')
                return render_template('more.html', dynamic_route='password', old_password=old_password, new_password=new_password, confirm_password=confirm_password)
            
            # ensure new password confirmation
            elif new_password != confirm_password:
                flash('New Password and Confirm Password does NOT Match!')
                return render_template('more.html', dynamic_route='password', old_password=old_password, new_password=new_password, confirm_password=confirm_password)
            
            # check if old and new password match
            elif not check_password_hash(pwhash=current_hashed_password, password=old_password):
                flash('Incorrect Old Password!')
                return render_template('more.html', dynamic_route='password', old_password=old_password, new_password=new_password, confirm_password=confirm_password)
            
            # change password in the database
            db.execute("UPDATE users SET (hash) = ? WHERE id = ?;", generate_password_hash(password=new_password, method='pbkdf2:sha512:600000'), current_user_id)
            flash("Password Successfully Changed!")
            return redirect(url_for('index'))
            
        # add cash to account
        elif len(form_data) == 1 and request.form.get("new_cash"):
            
            new_cash = form_data.get("new_cash")

            if new_cash == None or len(new_cash) <= 0:
                flash("Please Input a Valid New Cash!")
                return render_template("more.html", dynamic_route='add-cash', new_cash=new_cash)
        
            try:
                new_cash = float(new_cash)
                if new_cash < 0.0001:
                    raise ValueError()
                
            except ValueError:
                flash("New Cash must be a positive real number atleast 0!")
                return render_template("more.html", dynamic_route='add-cash', new_cash=new_cash)
        
            current_cash = db.execute("SELECT cash FROM users WHERE id = ?;", current_user_id)[0]['cash']
            
            db.execute("UPDATE users SET (cash) = ? WHERE id = ?;", (new_cash + current_cash), current_user_id)
            flash("Cash Successfully Added!")
            return redirect(url_for("index"))

        # add a profile picture
        elif "profile-picture" in request.files:
            profile_picture = request.files.get("profile-picture")

            if not isinstance(profile_picture, FileStorage) or profile_picture is None or profile_picture.filename is None:
                flash("Please provide a valid image!")
                return redirect(url_for("all_routes.more"))
            

            filename = secure_filename(profile_picture.filename)
            filepath = os.path.join(os.path.dirname(__file__), 'static/imgs/profile', filename)
            
            profile_picture.save(filepath)

            # do the final image validation
            if not validate_image(filepath):
                flash("Invalid file type, not an Image!")
                clear_tmp_profile_dir()
                return redirect(url_for("all_routes.more"))

            with open(filepath, 'rb') as uploaded_picture:
                existing_profile_picture = db.execute("SELECT picture FROM profiles WHERE user_id = ?", current_user_id)
        
                picture_data = uploaded_picture.read()
                
                if len(existing_profile_picture) <= 0:
                    # Insert the image data into the profiles table if the user does not already have a profile picture
                    db.execute("INSERT INTO profiles (user_id, picture) VALUES (?, ?);", current_user_id, picture_data)
                else:
                    # otherwise update the image to the new one
                    db.execute("UPDATE profiles SET (picture) = ? WHERE user_id = ?", picture_data, current_user_id)
                    

            flash("Profile picture uploaded successfully!")
            return redirect(url_for("index"))
            
        return redirect(url_for("all_routes.more"))
        
    options_as_words = [option.replace('-', ' ') for option in MORE_OPTIONS]
    return render_template("more.html", more_options=options_as_words)


@all_routes.route("/more/<dynamic_route>", methods=['POST', 'GET'])
@login_required
def dynamically_display_more_options(dynamic_route):
    
    if dynamic_route.lower() not in MORE_OPTIONS:
        return render_template("more.html", route_not_valid=dynamic_route)
    
    return render_template("more.html", dynamic_route=dynamic_route)

