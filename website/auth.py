from flask import Blueprint, render_template, redirect, request, flash
from flask_login import login_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from . import db
from .models import User

auth = Blueprint("auth", __name__)

def validate_user(user, password1, password2):
    return user and check_password_hash(user.password1, password1) and check_password_hash(user.password2, password2)

@auth.route("/signin", methods=['GET', 'POST'])
def signin():
    if request.method == 'POST':
        username = request.form.get("username")
        password1 = request.form.get("password1")
        password2 = request.form.get("password2")

        user = User.query.filter_by(username=username).first()
        if validate_user(user, password1, password2):
            login_user(user, remember=True)
            flash('Signed into admin account', category='success')
            return redirect("/")
        flash('Incorrect username or password(s)', category='error')

    return render_template("signin.html", user=current_user)

'''@auth.route("/signup", methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get("username")
        password1 = request.form.get("password1")
        password2 = request.form.get("password2")

        user_exists = User.query.filter_by(username=username).first()
        if user_exists:
            flash("User already exists", category='warning')
        elif password1 and password2:
            new_user = User(username=username,password1=generate_password_hash(password1, method='scrypt'),password2=generate_password_hash(password2, method='scrypt'),userrole="user",verified=True) # type: ignore
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user, remember=True)
            flash('User created successfully', category='success')
            return redirect("/")

    return render_template("signup.html", user=current_user)'''
