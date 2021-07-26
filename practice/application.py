import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True


# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""

    sum_shares = db.execute(
        "SELECT symbol, sum(shares) as total FROM portfolios WHERE user_id = ? GROUP BY symbol HAVING total > 0;", session["user_id"])

    amount = 0
    buy_list = []
    user_id = session["user_id"]

    for row in sum_shares:

        symbol_data = lookup(row["symbol"])

        buy_list.append({
            "symbol": symbol_data["symbol"],
            "name": symbol_data["name"],
            "shares": row["total"],
            "price": usd(symbol_data["price"]),
            "total": usd(row["total"] * (symbol_data["price"]))
        })

        amount += row["total"] * (symbol_data["price"])

    cash_data = db.execute("select cash from users where id = ?", user_id)
    amount += cash_data[0]["cash"]
    cash = usd(cash_data[0]["cash"])

    return render_template("index.html", buy_list=buy_list, cash=cash, amount=usd(amount))


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":

        user_id = session["user_id"]

        if not request.form.get("symbol") or not request.form.get("shares"):
            return apology("must provide symbol and shares", 400)

        symbol = request.form.get("symbol")
        shares = request.form.get("shares")
        symbol_data = lookup(symbol)
        if shares.isdigit() == False:
            return apology("invalid shares")

        if symbol_data == None:
            return apology("invalid symbol", 400)
        elif int(shares) < 1:
            return apology("invalid shares", 400)

        default_cash = db.execute("select cash from users where id = ?", user_id)
        cash = default_cash[0]["cash"]

        pay_cash = float(shares) * symbol_data["price"]

        if cash > pay_cash:
            apdate_cash = cash - pay_cash
            db.execute("UPDATE users SET cash = ? where id = ?", apdate_cash, user_id)
            db.execute("INSERT INTO portfolios (user_id, symbol, shares, price) VALUES (?, ?, ?, ?)", 
                       user_id, symbol_data["symbol"], shares, usd(symbol_data["price"]))
            flash("bought!")
            return redirect("/")

        else:
            return apology("do not have enough money")

    return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    info = db.execute("SELECT symbol, shares, transacted FROM portfolios WHERE user_id = ?;", session["user_id"])

    histories = []

    for row in info:
        user_id = session["user_id"]
        symbol_data = lookup(row["symbol"])

        histories.append({
            "symbol": symbol_data["symbol"],
            "shares": row["shares"],
            "price": usd(symbol_data["price"]),
            "transacted": row["transacted"]
        })

    return render_template("history.html", histories=histories)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":
        symbol = request.form.get("symbol")
        symbol_data = lookup(symbol)

        if symbol_data == None:
            return apology("invalid symbol", 400)

        else:
            symbol_name = symbol_data["name"]
            symbol_price = usd(symbol_data["price"])
            symbol_symbol = symbol_data["symbol"]

            return render_template("quoted.html", name=symbol_name, price=symbol_price, symbol=symbol_symbol)

    return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 400)

        # Ensure password was submitted
        elif not request.form.get("password") or not request.form.get("confirmation"):
            return apology("must provide password and confirmation", 400)

        name = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        if not password == confirmation:
            return apology("not match password and confirmation", 400)

        username_registered = db.execute("select username from users")

        list_name = [d.get("username") for d in username_registered]

        if name in list_name:
            return apology("username is already used", 400)
        # Remember which user has logged in
        else:
            hash_password = generate_password_hash(password, method='pbkdf2:sha256', salt_length=8)
            db.execute("INSERT INTO  users (username, hash) VALUES(?, ?)", name, hash_password)

            rows = db.execute("SELECT * FROM users WHERE username = ?", name)

            session["user_id"] = rows[0]["id"]
            flash("registered!")
            return redirect("/")

    return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "GET":
        user_id = session["user_id"]
        symbols = db.execute(
            "select symbol, sum(shares) as total from portfolios where user_id = ? group by symbol having total != 0", user_id)
        symbol_list = [d.get("symbol") for d in symbols]

        return render_template("sell.html", symbols=symbol_list)

    if request.method == "POST":
        user_id = session["user_id"]
        symbol = request.form.get("symbol")
        shares = request.form.get("shares")
        check_shares = db.execute("select sum(shares) as total from portfolios where symbol = ? and user_id = ?", symbol, user_id)

        if int(shares) > int(check_shares[0]["total"]):
            return apology("invalid number", 400)

        symbol_data = lookup(symbol)

        db.execute("INSERT INTO portfolios (user_id, symbol, shares, price) VALUES (?, ?, ?, ?)",
                   user_id, symbol_data["symbol"], -1 * int(shares), usd(symbol_data["price"]))
        default_cash = db.execute("select cash from users where id = ?", user_id)
        cash = default_cash[0]["cash"]
        get_cash = float(shares) * symbol_data["price"]
        apdate_cash = cash + get_cash

        db.execute("UPDATE users SET cash = ? where id = ?", apdate_cash, user_id)

        flash("bought!")
        return redirect("/")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
