from flask import Blueprint, render_template, redirect, request, flash
from flask_login import login_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.wrappers.response import Response
from . import db
from .models import Admin

auth = Blueprint("auth", __name__)

def validate_user(admin, password1, password2):
    return admin and check_password_hash(admin.password1, password1) and check_password_hash(admin.password2, password2)

@auth.route("/signin", methods=['GET', 'POST'])
def signin() -> str | Response:
    if request.method == 'POST':
        username = request.form.get("username")
        password1 = request.form.get("password1")
        password2 = request.form.get("password2")

        admin = Admin.query.filter_by(username=username).first()
        if validate_user(admin, password1, password2):
            login_user(admin, remember=True)
            flash('Signed into admin account', category='success')
            return redirect("/")
        flash('Incorrect username or password(s)', category='error')

    return render_template("signin.html", user=current_user)

# @auth.route("/signup", methods=['GET', 'POST'])
# def signup() -> str | Response:
#     if request.method == 'POST':
#         username = request.form.get("username")
#         password1 = request.form.get("password1")
#         password2 = request.form.get("password2")

#         user_exists = Admin.query.filter_by(username=username).first()
#         if user_exists:
#             flash("Admin already exists", category='warning')
#         elif password1 and password2:
#             new_user = Admin(username=username,password1=generate_password_hash(password1, method='scrypt'),password2=generate_password_hash(password2, method='scrypt'),user_role="admin",verified=True) 
#             db.session.add(new_user)
#             db.session.commit()
#             login_user(new_user, remember=True)
#             flash('Admin created successfully', category='success')
#             return redirect("/")

#     return render_template("signup.html", user=current_user)
