import os
import psycopg2
from zoneinfo import ZoneInfo
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user
from flask_migrate import Migrate
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, MultipleFileField, FileAllowed, FileRequired
from flask_redmail import RedMail
from wtforms import StringField, SubmitField, EmailField, PasswordField, SelectField, RadioField, TextAreaField
from wtforms.validators import Email, Length, EqualTo, InputRequired, NoneOf, Optional

#from dotenv import load_dotenv
#load_dotenv()

db: SQLAlchemy = SQLAlchemy()
email: RedMail = RedMail()

def create_app() -> Flask:
	app = Flask(__name__)

	app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")
	app.config["SESSION_TYPE"] = "localstorage"
	app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

	#app.config['SQLALCHEMY_DATABASE_URI'] =  'postgresql+psycopg2://postgres:shetty777pgSQL@localhost:5433/main_database'
	app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql+psycopg2://{user}:{password}@{host}:{port}/{dbname}?sslmode=require'.format(
        user=os.environ.get("SQLALCHEMY_DATABASE_URI_USER"),
        password=os.environ.get("SQLALCHEMY_DATABASE_URI_PASSWORD"),
        host=os.environ.get("SQLALCHEMY_DATABASE_URI_HOST"),
        port=os.environ.get("SQLALCHEMY_DATABASE_URI_PORT"),
        dbname=os.environ.get("SQLALCHEMY_DATABASE_URI_NAME")
    )
	app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_pre_ping': True,
        'pool_size': 10,
        'max_overflow': 20,
        'pool_timeout': 30,
        'pool_recycle': 1800
    }

	app.config["EMAIL_HOST"] = 'smtp.gmail.com'
	app.config["EMAIL_PORT"] = 587
	app.config["EMAIL_USERNAME"] = os.environ.get("EMAIL_USERNAME")
	app.config["EMAIL_PASSWORD"] = os.environ.get("APP_PASSWORD")
	app.config["EMAIL_SENDER"] = os.environ.get("EMAIL_USERNAME")
	
	db.init_app(app)
	Migrate(app, db)
	email.init_app(app)

	def format_datetime(value, tz_code, format):
		if value is None:
			return ""
		tz = ZoneInfo(tz_code)
		value = value.astimezone(tz)
		return value.strftime(format)
	app.jinja_env.filters['format_datetime'] = format_datetime


	from .models import AllUsers
	from .routes import routes
	from .auth import auth
	app.register_blueprint(routes, url_prefix="/")
	app.register_blueprint(auth, url_prefix="/")

	
	login_manager = LoginManager()
	login_manager.login_view = "routes.login"
	login_manager.init_app(app)

	login_manager.login_message_category = "info"

	@login_manager.user_loader
	def load_user(id):
		return AllUsers.query.get(int(id))
    
	@app.before_request
	def create_database():
		app.before_request_funcs[None].remove(create_database)
		db.create_all()


	@app.errorhandler(401)
	def access_denied1(e) -> tuple:
		return render_template("error_handlers/401.html", user=current_user), 401

	@app.errorhandler(403)
	def access_denied2(e) -> tuple:
		return render_template("error_handlers/403.html", user=current_user), 403

	@app.errorhandler(404)
	def not_found(e) -> tuple:
		return render_template("error_handlers/404.html", user=current_user), 404

	@app.errorhandler(405)
	def method_not_allowed(e) -> tuple:
		return render_template("error_handlers/405.html", user=current_user), 405
        
	@app.errorhandler(500)
	def server_down(e) -> tuple:
		return render_template("error_handlers/500.html", user=current_user), 500
    
	@app.errorhandler(502)
	def bad_gateway(e) -> tuple:
		return render_template("error_handlers/502.html", user=current_user), 502
   
	return app

#---------------oo0oo---------------#

class SubscriberForm(FlaskForm):
	username = StringField("Your username:", validators=[InputRequired(), NoneOf(['%', '+', '=', '\\', ':', ';', '"', '<', '>', '?', '/'], message="Do not use special characters")])
	email_id = EmailField("Your E-mail address:", validators=[InputRequired(), Email(check_deliverability=True, message="E-mail address is not valid")])
	password = PasswordField("A strong password:", validators=[InputRequired(), Length(min=6, max=70)])
	confirm_password = PasswordField("Repeat the password:", validators=[InputRequired(),  EqualTo(fieldname='password', message ="Passwords do not match" )])
	subscribe = SubmitField("Subscribe")

class LoginForm(FlaskForm):
	username_or_email_id = StringField("Your username or E-mail address:", validators=[InputRequired()])
	password = PasswordField("Your password:", validators=[InputRequired(), Length(min=6, max=70)])
	login = SubmitField("Login to Subscriber account")

class ForgotPasswordForm(FlaskForm):
	username_or_email_id = StringField("Your username or E-mail address:", validators=[InputRequired()])
	send_reset_mail = SubmitField("Send E-mail for password reset")

class ResetPasswordForm(FlaskForm):
	new_password = PasswordField("A strong password:", validators=[InputRequired(), Length(min=6, max=70)])
	confirm_new_password = PasswordField("Repeat the password:", validators=[InputRequired(), EqualTo(fieldname='new_password', message ="Passwords do not match" )])
	reset = SubmitField("Reset password")

class PostForm(FlaskForm):
	category = SelectField("What kind of post is this?", validators=[InputRequired()], choices=[('Article'), ('Project'), ('Blog')])
	author = SelectField("Who is the author of this post?", validators=[InputRequired()], choices=[('Shashank Shetty'), ('Vibha P'), ('Srikanth Shetty'), ('Amulya B R')])
	html_file = FileField("The HTML file of the post:", validators=[FileRequired(), FileAllowed(['html'])])
	url = StringField("URL address of the post:", validators=[InputRequired(), NoneOf([" ", "`", "@", "^", "(", ")", "|", "\\", "/", "[", "]", "{", "}", ">", "<"])])
	images = MultipleFileField("Accompanying images of the post:", validators=[FileRequired(), FileAllowed(['jpg', 'jpeg', 'png', 'svg', 'webp', 'gif'])])
	audios = MultipleFileField("Audio files in the post (optional):", validators=[FileAllowed(['mp3', 'ogg', 'wav'])])
	post = SubmitField("Create the post")

class CommentForm(FlaskForm):
	rating = RadioField('How much do you rate this post out of  7 ?', choices=[1, 2, 3, 4, 5, 6, 7], validators=[Optional()]) 
	text_content = TextAreaField("Comment text:", validators=[Length(max=500)])
	comment = SubmitField("Comment")
