import os, json

from flask import Flask, session, redirect, render_template, request, jsonify, flash
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from helper import *
from werkzeug.security import check_password_hash, generate_password_hash

import requests

import datetime;

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)
# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

@app.route("/")
@login_required
def home():
    return redirect("/search")
@app.route("/search",methods = ["POST","GET"])
@login_required
def search():
    """ Show search box """
    return render_template("search.html")
@app.route("/catalogue",methods = ["POST"])
@login_required
def catalogue():
    if not request.form.get("book"):
        return render_template("error.html",message = "you must provide a book.")
    query = "%" + request.form.get("book") + "%"

    query = query.title()
    rows = db.execute("SELECT isbn_number,book_name, author_name, publishing_year FROM books WHERE \
                    isbn_number LIKE :query OR \
                    book_name LIKE :query OR \
                    author_name LIKE :query LIMIT 15",
                    {"query": query})
    if rows.rowcount == 0:
        return render_template("error.html", message="we can't find books with that description.")

        # Fetch all the results
    books = rows.fetchall()
    return render_template("catalogue.html", books=books)

@app.route("/login",methods = ["POST","GET"])
def login():
    session.clear()
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("user"):
            return render_template("error1.html", message="must provide username")

        # Ensure password was submitted
        elif not request.form.get("password"):
            return render_template("error1.html", message="must provide password")
        ts = datetime.datetime.now()
        # Query database for username (http://zetcode.com/db/sqlalchemy/rawsql/)
        # https://docs.sqlalchemy.org/en/latest/core/connections.html#sqlalchemy.engine.ResultProxy
        rows = db.execute("SELECT * FROM account WHERE username = :username",
                            {"username": request.form.get("user")})

        result = rows.fetchone()
        # Ensure username exists and password is correct
        if result == None :
            return render_template("error1.html", message="invalid username ")
        if result[2] != request.form.get("password") :
            return render_template("error1.html", message="invalid password")
        #Remember which user has logged in
        session['user_id'] = result[0]
        session['username'] = result[1]
        db.execute("UPDATE account SET last_login = :last_login where user_id =:user_id", {"last_login":ts,"user_id":result[0]})
        db.commit()
        # Redirect user to home page
        return redirect("/search",code = 307)
    else:
        return render_template("first.html",message="")
@app.route("/register",methods = ["Get","POST"])
def register():
    session.clear()
    if request.method == "POST":
        if not request.form.get("user"):
            return render_template("error.html", message="must provide username")

        # Query database for username
        userCheck = db.execute("SELECT * FROM account WHERE username = :username",{"username":request.form.get("user")}).fetchone()
        # Check if username already exist
        if userCheck:
            return render_template("error1.html", message="username already exist")

        userCheck = db.execute("SELECT * FROM account WHERE email = :email",{"email":request.form.get("email")}).fetchone()
        # Check if email already exist
        if userCheck:
            return render_template("error1.html", message="email already exist")
        # Ensure password was submitted
        elif not request.form.get("password"):
            return render_template("error1.html", message="must provide password")

        #hashedPassword = generate_password_hash(request.form.get("password"), method='pbkdf2:sha256', salt_length=8)
        ts = datetime.datetime.now()
        db.execute("INSERT INTO account (username,password,email,created_on) VALUES (:username, :password,:email,:created_on)",{"username":request.form.get("user"),
                                 "password":request.form.get("password"),"email":request.form.get("email"),"created_on":ts})
        db.commit()

        flash('Account created', 'info')
        # Redirect user to login page
        return redirect("/login")
    else:
        return render_template("register.html")

@app.route("/logout")
def logout():
    """ Log user out """

    # Forget any user ID
    session.clear()

    # Redirect user to login form
    return redirect("/login")


@app.route("/book/<isbn_number>", methods=['GET','POST'])
@login_required
def book(isbn_number):
    """ Save user review and load same page with reviews updated."""

    if request.method == "POST":

        # Save current user info
        currentUser = session["user_id"]
        username = session["username"]

        # Fetch form data
        rating = request.form.get("rating")
        comment = request.form.get("comment")

        # Check for user submission (ONLY 1 review/user allowed per book)
        row2 = db.execute("SELECT * FROM reviews WHERE reviewer_username= :reviewer_username AND isbn_number = :isbn_number",
                    {"reviewer_username": username ,
                     "isbn_number" :isbn_number})

        # A review already exists
        if row2.rowcount == 1:

            flash('You already submitted a review for this book', 'warning')
            return redirect("/book/" + isbn_number)

        # Convert to save into DB
        rating = int(rating)
        ts = datetime.datetime.now()
        db.execute("INSERT INTO reviews (isbn_number,reviewer_username,comment,rating,review_time) VALUES (:isbn_number, :reviewer_username,:comment, :rating, :review_time)",
                {"isbn_number":isbn_number,"reviewer_username":username,"comment": comment,"rating": rating,"review_time" : ts})

        # Commit transactions to DB and close the connection
        db.commit()

        flash('Review submitted!', 'info')

        return redirect("/book/" + isbn_number)

    # Take the book ISBN and redirect to his page (GET)
    else:

        row = db.execute("SELECT isbn_number,book_name,author_name,publishing_year FROM books WHERE \
                        isbn_number= :isbn_number",
                        {"isbn_number": isbn_number})

        bookInfo = row.fetchall()

        """ GOODREADS reviews """

        # Read API key from env variable
        key = os.getenv("GOODREADS_KEY")

        # Query the api with key and ISBN as parameters
        query = requests.get("https://www.goodreads.com/book/review_counts.json",
                params={"key": key, "isbns": isbn_number})

        # Convert the response to JSON
        response = query.json()

        # "Clean" the JSON before passing it to the bookInfo list
        response = response['books'][0]

        # Append it as the second element on the list. [1]
        bookInfo.append(response)

        """ Users reviews

         # Search book_id by ISBN
        row = db.execute("SELECT id FROM books WHERE isbn = :isbn",
                        {"isbn": isbn})
        SELECT username, comment, rating,time
        # Save id into variable
        book = row.fetchone() # (id,)
        book = book[0]"""

        # Fetch book reviews
        # Date formatting (https://www.postgresql.org/docs/9.1/functions-formatting.html)
        results = db.execute("SELECT reviewer_username,comment,rating,review_time FROM reviews where isbn_number = :isbn_number ORDER BY review_time",
        {"isbn_number" : isbn_number})

        reviews = results.fetchall()

        return render_template("book.html", bookInfo=bookInfo, reviews=reviews)
@app.route("/api/<isbn>", methods=['GET'])
@login_required
def api_call(isbn):

    # COUNT returns rowcount
    # SUM returns sum selected cells' values
    # INNER JOIN associates books with reviews tables

    row = db.execute("SELECT book_name, author_name, publishing_year,books.isbn_number, \
                    COUNT(reviews.review_id) as review_count, \
                    AVG(reviews.rating) as average_score \
                    FROM books \
                    INNER JOIN reviews \
                    ON books.isbn_number = reviews.isbn_number \
                    WHERE books.isbn_number = :isbn \
                    GROUP BY book_name,author_name,publishing_year,books.isbn_number",
                    {"isbn": isbn})

    # Error checking
    if row.rowcount != 1:
        return jsonify({"Error": "Invalid book ISBN"}), 422

    # Fetch result
    tmp = row.fetchone()

    # Convert to dict
    result = dict(tmp.items())

    # Round Avg Score to 2 decimal. This returns a string which does not meet the requirement.
    # https://floating-point-gui.de/languages/python/
    result['average_score'] = float('%.2f'%(result['average_score']))

    return jsonify(result)
