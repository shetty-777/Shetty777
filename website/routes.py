import os
import re
import jwt
import urllib.parse
from zoneinfo import ZoneInfo
from datetime import datetime, timezone
from functools import wraps
from bs4 import BeautifulSoup
from markupsafe import Markup
from flask import Blueprint, render_template, redirect, request, flash, abort, current_app, jsonify, url_for
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from website import generate_token
from .models import Post, Subscriber, Comment, AllUsers
from . import db, subscriberform, postform, loginform, commentform, email

routes = Blueprint("routes", __name__, template_folder="../website/posts/", static_folder="../website/post_media/" )

def role_required(role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(403)
            if hasattr(current_user, 'userrole') and current_user.userrole == role:
                return f(*args, **kwargs)
            else:
                abort(403)

        return decorated_function
    return decorator

def verification_required():
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            if current_user.userrole == 'user' or  hasattr(current_user, 'verified') and current_user.verified == True:
                return f(*args, **kwargs)
            else:
                abort(401)

        return decorated_function
    return decorator

def format_datetime(value, tz_code, format):
		if value is None:
			return ""
		tz = ZoneInfo(tz_code)
		value = value.astimezone(tz)
		return value.strftime(format)
#---------------------------------oooo000oooo--------------------------------------#

@routes.route("/")
def index():
	rec_posts = Post.query.order_by(Post.date_created.desc()).all()
	rec_posts_list = []

	for rec_post in rec_posts[:10]:
		rec_post_file = rec_post.htmlfile

		with open(current_app.root_path+"/posts/"+rec_post_file, 'r', encoding='utf-8') as file:
			html_content = file.read()
		
		soup = BeautifulSoup(html_content, 'html.parser')
		#--------------------------------------------------------------------------
		title_h1_element = soup.find(id="post_title")

		if title_h1_element:
			title = title_h1_element.text
		#--------------------------------------------------------------------------
		banner_img_element = soup.find(id="post_banner")

		if banner_img_element:
			banner = banner_img_element.get('src') # type: ignore
			banner = re.search(r'''='(.*?)'\)''', str(banner)).group(1).strip() # type: ignore
		#-------------------------------------------------------------------------
		if rec_post.date_created:
			date = format_datetime(rec_post.date_created, 'Asia/Kolkata', "%d %b, %Y")

		rec_posts_list.append({"title": title, "banner": banner, "url": rec_post.url, "date": date})
	return render_template("index.html", user=current_user, rec_posts_list=rec_posts_list)

@routes.route("/about")
def about():
	return render_template("about.html", user=current_user)
#---------------------------------oooo000oooo--------------------------------------#

@routes.route("/subscribe", methods=['GET','POST'])
def subscribe():
	username = None
	emailid = None
	password = None
	confirm_password = None
	form = subscriberform()
	if form.validate_on_submit():
		username = form.username.data
		form.username.data = ''
		emailid = form.emailid.data
		form.emailid.data = ''
		password = generate_password_hash(str(form.password.data), method='scrypt')
		form.password.data = ''
		confirm_password = form.confirm_password.data
		form.confirm_password.data = ''
	
	
	#----------------oo0oo---------------#
	stripped_email = str(emailid).lower().replace('.','')
	if "+" in stripped_email:
		stripped_email = re.sub(r"""\+(.*?)@""", '', stripped_email)
	else:
		stripped_email = stripped_email.replace("@","")
	
	if request.method == 'POST':
		if Subscriber.query.filter_by(username=username).first():
			flash("Username is already taken, try a different one", category='warning')
		elif Subscriber.query.filter_by(emailid=emailid).first():
			flash("An account with this E-mail address already exists", category='warning')
		#---------------------------------------------------------------------
		elif 'username' in form.errors:
			flash("Do not use special characters", category='error')
		elif stripped_email == "shetty777bloggmailcom":
			flash("No no no! Don't do that, that is my e-mail address", category='error')
		elif 'emailid' in form.errors:
			flash("The E-mail address you provided is not valid", category='error')
		elif 'password' in form.errors:
			flash("Looks like the two passwords don't match. Make sure they are the same", category='error')
		#---------------------------------------------------------------------
		elif not form.errors:
			try:
				new_subscriber = Subscriber(username=username, emailid=emailid, password=password, userrole="subscriber") # type: ignore
				db.session.add(new_subscriber)
				db.session.commit()

				email.send(	subject = "E-mail verification for Shetty777",
							receivers = emailid,
							body_params = {"token": generate_token.generate_token(username, 'Fresh', 10)},
							html_template = "email/verify.html")
	
				return render_template("verify_email.html", user=current_user)
			except:
				db.session.rollback()

	return render_template("subscribe.html", user=current_user, username=username, emailid=emailid, password=password, confirm_password=confirm_password, form=form)

@routes.route("/send_manual_verification")
@role_required('user')
def send_manual_verification():
	try:
		emailid = urllib.parse.unquote(request.args.get('email')) # type: ignore
		username = urllib.parse.unquote(request.args.get('user')) # type: ignore
		print(emailid)
		print(username)
		email.send(	subject = "E-mail verification for Shetty777",
					receivers = emailid,
					body_params = {"token": generate_token.generate_token(username, 'Fresh', 10)},
					html_template = "email/verify_refreshed.html")
		flash('Verification E-mail sent to', category='success')
	except Exception as e:
		flash(f"Something didn't go right {e}", category='error')
	return redirect("/subscriber_list")

@routes.route("/verify_email/<token>")
def verify_email(token):
	try:
		token_data = jwt.decode(token, current_app.config["SECRET_KEY"], algorithms = ['HS256'], options={'verify_exp': False})
		username = token_data["username"]
		token_type = token_data["token_type"]
		exp = token_data["exp"]
		new_subscriber = Subscriber.query.filter_by(username=username).first()
		if int(datetime.now(tz=timezone.utc).timestamp()) < exp:
			try:
				if new_subscriber.verified == False: # type: ignore
					new_subscriber.verified = True # type: ignore
					db.session.commit()

					login_user(new_subscriber, remember=True)
					flash('Congratulations! You are now subscribed to Shetty777', category='success')
				
				elif new_subscriber.verified == True: # type: ignore
					flash('Your E-mail address has already been verified (1)', category='success')
				else:
					pass
			except:
				db.session.rollback()
			
		elif token_type == 'Fresh' and int(datetime.now(tz=timezone.utc).timestamp()) >= exp:
			if new_subscriber.verified == False:
				email.send(	subject = "E-mail verification for Shetty777 [Refreshed token]",
						receivers = new_subscriber.emailid, # type: ignore
						body_params = {"token": generate_token.generate_token(username, 'Refresh', 10080)},
						html_template = "email/verify_refreshed.html")
				return render_template("verify_email_refreshed.html", user=current_user)
			elif new_subscriber.verified == True: # type: ignore
				flash('Your E-mail address has already been verified (2)', category='success')
			else:
				pass

		elif token_type == 'Refresh' and int(datetime.now(tz=timezone.utc).timestamp()) >= exp:
			if new_subscriber.verified == False:
				email_to_verify = Subscriber.query.filter_by(username=username).first().emailid # type: ignore
				flash(Markup(f'Even your refresh token expired! <a href="mailto:shetty777.blog@gmail.com?subject=Verification%20token%20refresh%20request&body=With%20this%20E-mail,%20I%20request%20you%20to%20refresh%20my%20verification%20token%20to%20subscribe%20to%20Shetty777%0AI%20understand%20that%20not%20verifying%20with%20this%20new%20token%20will%20lead%20tos%20my%20account%20being%20deleted.%0AThe%20E-mail%20address%20is,%20{email_to_verify}">Request to get a new refresh token for your account</a>'), category='error')
				return redirect("/")
			elif new_subscriber.verified == True: # type: ignore
				flash('Your E-mail address has already been verified (3)', category='success')
			else:
				pass
	except:
		flash("Looks the verification token is invalid. Try again.", category='error')
		return redirect("/")
	
	return redirect("/")

@routes.route("/login", methods=['GET', 'POST'])
def login():
	usernameoremailid = None
	password = None
	form = loginform()
	if form.validate_on_submit():
		usernameoremailid = form.usernameoremailid.data
		form.usernameoremailid.data = ''
		password = form.password.data
		form.password.data = ''
	
	if request.method == 'POST':
		usernameoremailid = request.form.get("usernameoremailid")
		password = request.form.get("password")

		subscriber = Subscriber.query.filter_by(username=usernameoremailid).first()
		subscriber_email = Subscriber.query.filter_by(emailid=usernameoremailid).first()

		if subscriber:
			if check_password_hash(subscriber.password, password): # type: ignore
				login_user(subscriber, remember=True)
				flash('Successfully logged into your subscriber account', category='success')
				return redirect("/")
			else:
				flash('Password is incorrect', category='error')
		elif subscriber_email:
			if check_password_hash(subscriber_email.password, password): # type: ignore
				login_user(subscriber_email, remember=True)
				flash('Successfully logged into your subscriber account !!!', category='success')
				return redirect("/")
			else:
				flash('Password is incorrect', category='error')
		else:
			flash("The username or E-mail you have provided does not exist", category='error')
	return render_template("login.html", user=current_user, usernameoremailid=usernameoremailid, password=password, form=form)

@routes.route("/logout")
@login_required
def logout():
	logout_user()
	flash('Logged out', category='info')
	return redirect("/")

#---------------------------------oooo000oooo--------------------------------------#

@routes.route("/dashboard/<path:username>")
@login_required
def dashboard(username):
	try:
		usrname = urllib.parse.unquote(username).replace('/', '')
		user = db.session.query(AllUsers).filter_by(username=usrname).first()
		if user and current_user.username == user.username: # type: ignore
			marked_posts = user.marked_posts
			marked_posts_list = []

			for marked_post in marked_posts:
				marked_post_file = marked_post.htmlfile

				with open(current_app.root_path+"/posts/"+marked_post_file, 'r', encoding='utf-8') as file:
					html_content = file.read()
				
				soup = BeautifulSoup(html_content, 'html.parser')
				#--------------------------------------------------------------------------
				title_h1_element = soup.find(id="post_title")

				if title_h1_element:
					title = title_h1_element.text

				marked_posts_list.append({"title": title, "category": marked_post.category, "url": marked_post.url})

			return render_template("dashboard.html", user=current_user, marked_posts_list=marked_posts_list)
		else:
			flash("You cannot access other users' dashboards!", category='warning')
			return redirect("/")

	except:
		flash(f'Looks like the user does not exist; so dashboard cannot be opened', category='warning')
		return redirect("/")

#---------------------------------oooo000oooo--------------------------------------#

@routes.route("/articles")
def articles():
	articles = Post.query.filter_by(category='Article').order_by(Post.date_created.desc()).all()
	articles_list = []

	for article in articles:
		article_file = article.htmlfile

		with open(current_app.root_path+"/posts/"+article_file, 'r', encoding='utf-8') as file:
			html_content = file.read()
		
		soup = BeautifulSoup(html_content, 'html.parser')
		#--------------------------------------------------------------------------
		title_h1_element = soup.find(id="post_title")

		if title_h1_element:
			title = title_h1_element.text
		#--------------------------------------------------------------------------
		banner_img_element = soup.find(id="post_banner")

		if banner_img_element:
			banner = banner_img_element.get('src') # type: ignore
			banner = re.search(r'''='(.*?)'\)''', str(banner)).group(1).strip() # type: ignore
		#-------------------------------------------------------------------------
		if article.date_created:
			date = format_datetime(article.date_created, 'Asia/Kolkata', "%d %b, %Y")

		articles_list.append({"title": title, "banner": banner, "url": article.url, "date": date})

	return render_template("articles.html", user=current_user, articles_list=articles_list)

@routes.route("/projects")
def projects():
	projects = Post.query.filter_by(category='Project').order_by(Post.date_created.desc()).all()

	projects_list = []
	for project in projects:
		project_file = project.htmlfile

		with open(current_app.root_path+"/posts/"+project_file, 'r', encoding='utf-8') as file:
			html_content = file.read()
		
		soup = BeautifulSoup(html_content, 'html.parser')
		#--------------------------------------------------------------------------
		title_h1_element = soup.find(id='post_title')

		if title_h1_element:
			title = title_h1_element.text
		#--------------------------------------------------------------------------
		banner_img_element = soup.find(id='post_banner')

		if banner_img_element:
			banner = banner_img_element.get('src') # type: ignore
			banner = re.search(r'''='(.*?)'\)''', str(banner)).group(1).strip() # type: ignore
		#--------------------------------------------------------------------------
		if project.date_created:
			date = format_datetime(project.date_created, 'Asia/Kolkata', "%d %b, %Y")
		
		projects_list.append({"title": title, "banner": banner, "url": project.url, "date": date})

	return render_template("projects.html", user=current_user, projects_list=projects_list)

@routes.route("/blogs")
def blogs():
	blogs = Post.query.filter_by(category='Blog').order_by(Post.date_created.desc()).all()
	for blog in blogs:
		print(blog)
	return render_template("blogs.html", user=current_user)

#---------------------------------oooo000oooo--------------------------------------#

@routes.route("/post", methods=['GET','POST'])
@role_required('user')
def post():
	htmlfile = None
	images = None
	category = None
	url = None
	audio = None
	form = postform()
	if form.validate_on_submit():
		htmlfile = form.htmlfile.data
		form.htmlfile.data = ''
		images = form.images.data
		form.images.data = []
		audio = form.audio.data
		form.audio.data = ''
		category = form.category.data
		form.category.data = ''
		url = form.url.data
		form.url.data = ''
	
	if request.method == 'POST':
		post_url_exists = Post.query.filter_by(url=url).first()

		if post_url_exists:
			flash("A post with this URL already exists", category='warning')
		#---------------------------------------------------------------------
  		
		elif 'category' in form.errors:
			flash("Category must be 'Article' or 'Project'", category='error')
		elif 'url' in form.errors:
			flash('The following characters including "Space" is not allowed `@^()|\\/[] {}><', category='error')
		elif 'htmlfile' in form.errors:
			flash("Only HTML files are accepted", category='error')
		elif 'images' in form.errors:
			flash("Only images (.jpg, .png, .svg, .webp, et cetera...) are accepted", category='error')
		elif 'audio' in form.errors:
			flash("Only .mp3, .wav & .ogg files are accepted", category='error')
		#---------------------------------------------------------------------

		elif not form.errors:
			try:
				html_filename = secure_filename(htmlfile.filename) # type: ignore
				if not os.path.isfile(f'{current_app.root_path}/posts/{html_filename}'):
					htmlfile.save(os.path.join(current_app.root_path, 'posts', html_filename)) # type: ignore
					flash(f'Successfully uploaded file: {html_filename}', category='info')
				else:
					flash(f'File {html_filename} already exists', category='error')
					return redirect("/post")
				
				try:
					print("Audio")
					audio_filename = secure_filename(audio.filename) # type: ignore
					print("Audio is" + audio_filename)
					if not os.path.isfile(f'{current_app.root_path}/post_media/{audio_filename}'):
						print("Yo")
						audio.save(os.path.join(current_app.root_path, 'post_media', audio_filename)) # type: ignore
						flash(f'Successfully uploaded file: {audio_filename}', category='info')
					else:
						print("Yo again")
						flash(f'File {audio_filename} already exists', category='error')
						return redirect("/post")
				except Exception as e:
					print("No audio" + e)
					flash('No audio file; proceeding', category='info')

				for file in images: # type: ignore
					filename = secure_filename(file.filename)
					if not os.path.isfile(f'{current_app.root_path}/post_media/{filename}'):
						file.save(os.path.join(current_app.root_path, 'post_media', filename))
						flash(f'Successfully uploaded file: {filename}', category='info')
					else:
						flash(f'File {filename} already exists', category='error')
						return redirect("/post")
				
			except Exception as e:
				flash(f'File upload failed: {e}', category='error')
				return redirect("/post")

			#---------------------------------------------------------------------

			try:
				new_post = Post(htmlfile=html_filename, category=category, url=url) # type: ignore
				db.session.add(new_post)
				db.session.commit()
			except:
				db.session.rollback()

			post_for_mail = db.session.query(Post).filter_by(url=url).first()
			with open(current_app.root_path+"/posts/"+post_for_mail.htmlfile, 'r', encoding='utf-8') as file: # type: ignore
				html_content = file.read()
		
			soup = BeautifulSoup(html_content, 'html.parser')
			#--------------------------------------------------------------------------
			title_h1_element = soup.find(id="post_title")

			if title_h1_element:
				title = title_h1_element.text
			else:
				title = "Null"
		
		email_list = [email[0] for email in db.session.query(Subscriber.emailid).all()]
		if len(email_list) > 0:
			email.send(	subject = "Latest post buzz on Shetty777!",
						receivers = "Shetty777_Subscribers shetty777.blog@gmail.com",
						bcc = email_list,
						body_params = {"category": post_for_mail.category, "url":post_for_mail.url, "title": title}, # type: ignore
						text = f"Dear subscriber,\n I'm excited to share a new post on Shetty777! The latest { category } is now online.\n\n\nI am glad to have you here and appreciate your support :)\n\nBest regards,\nShashank S Shetty",
						html_template = "email/new_post.html")
		else:
			pass

		flash(f'Successfully created a new post; and sent notification to  {len(email_list)}  E-mail addresses', category='success')
		return redirect("/")
	
	return render_template("post.html", user=current_user, htmlfile=htmlfile, images=images, category=category, url=url, form=form)

#---------------------------------oooo000oooo--------------------------------------#

@routes.route("/web_posts/<post_url>", methods=['POST', 'GET'])
def web_posts(post_url):
	try:
		rating = None
		text_content = None
		avg_rating = None
		form = commentform()
		if form.validate_on_submit():
			rating = form.rating.data
			form.rating.data = ''
			text_content = form.text_content.data
			form.text_content.data = ''
				
		post = db.session.query(Post).filter_by(url=post_url).first()
		post_file = str(post.htmlfile).replace("<FileStorage: '", "") # type: ignore
		post_file = post_file.replace("' ('text/html')>", "")

		comments = db.session.query(Comment).filter_by(post_id=post.id).order_by(Comment.date_created.desc()).all() # type: ignore
		comment_list = []
		if comments:
			for comment in comments:
				commentor = db.session.query(AllUsers).filter_by(id=comment.commentor).first() # type: ignore
				comment_list.append({'id': comment.id, 'commentor': commentor, 'rating': comment.rating, 'text_content': comment.text_content, 'date': format_datetime(comment.date_created, 'Asia/Kolkata', "%d %b, %Y")})
			
		ratings = [r[0] for r in db.session.query(Comment.rating).filter(Comment.rating != None).all()]
		if len(ratings) != 0:
			avg_rating = round(sum(ratings) / len(ratings), 1)
		else:
			avg_rating = "No ratings"

		if hasattr(current_user, "id"):
			user_comments = Comment.query.filter_by(post_id=post.id, commentor=current_user.id).count() # type: ignore
		else:
			user_comments = 1
		
		if request.method == 'POST':
			if not form.errors:	
				if hasattr(current_user, "userrole") and current_user.userrole != 'user' and current_user.verified == True and user_comments < 1:
					if rating != None:
						try:
							new_comment = Comment(rating=rating, text_content=text_content, commentor=current_user.id, post_id=post.id) # type: ignore
							db.session.add(new_comment)
							db.session.commit()
							flash('You commented on this post', category='success')
						except:
							db.session.rollback()						
						return redirect(url_for('routes.web_posts', post_url=post_url))
					else:
						flash('A comment must contain some rating', category='warning')
						return redirect(url_for('routes.web_posts', post_url=post_url))
				elif current_user.verified != True:
					flash('You must be a verified subscriber to comment', category='warning')
					return redirect(url_for('routes.web_posts', post_url=post_url))				
				elif hasattr(current_user, "userrole") and current_user.userrole == 'user':
					if text_content == None:
						flash('Admin comment must contain text', category='warning')
						return redirect(url_for('routes.web_posts', post_url=post_url))
					else:
						try:
							new_comment = Comment(rating=None, text_content=text_content, commentor=current_user.id, post_id=post.id) # type: ignore
							db.session.add(new_comment)
							db.session.commit()
							flash('You commented on this post', category='success')
						except:
							db.session.rollback()
						return redirect(url_for('routes.web_posts', post_url=post_url))
				else:
					flash('You can only have 1 comment on a post', category='warning')
					return redirect(url_for('routes.web_posts', post_url=post_url))

		return render_template(post_file, user=current_user, current_post=post, rating=rating, text_content=text_content, comment_list=comment_list, form=form, avg_rating=avg_rating, user_comments=user_comments)

	except Exception as e:
		flash(f"There is no blog post of that name {e}", category='warning')
		return redirect("/")

@routes.route("/mark_post/<userid>/<postid>", methods=['POST'])
@verification_required()
def mark_post(userid, postid):
	usr = db.session.query(AllUsers).filter_by(id=userid).first()
	if usr == current_user:
		try:
			post = db.session.query(Post).filter_by(id=postid).first()
			usr.marked_posts.append(post) # type: ignore
			db.session.commit()
			return jsonify({"status": "success", "message": "Post marked"})
		except:
			db.session.rollback()
			abort(404)
	else:
		return jsonify({"status": "error", "message": "You cannot mark posts for other users"})

@routes.route("/unmark_post/<userid>/<postid>", methods=['POST'])
@verification_required()
def unmark_post(userid, postid):
	usr = db.session.query(AllUsers).filter_by(id=userid).first()
	if usr == current_user:
		try:
			post = db.session.query(Post).filter_by(id=postid).first()
			usr.marked_posts.remove(post) # type: ignore
			db.session.commit()
			return jsonify({"status": "success", "message": "Post unmarked"})
		except:
			db.session.rollback()
			abort(404)       
	else:
		return jsonify({"status": "error", "message": "You cannot unmark posts for other users"})


#---------------------------------oooo000oooo--------------------------------------#

@routes.route("/subscriber_list")
@role_required('user')
def subscriber_list():
	sublist=Subscriber.query.order_by(Subscriber.date_subscribed)
	return render_template("sublist.html", sublist=sublist, user=current_user)

@routes.route("/delete_subscriber/<int:id>", methods=['POST'])
@role_required('user')
def delete_subscriber(id):
	try:
		deleted_subscriber = db.session.query(Subscriber).filter_by(id=id).first()
		db.session.delete(deleted_subscriber)
		db.session.commit()

		email.send(subject="Subscriber account deleted",
                    receivers=deleted_subscriber.emailid, # type: ignore
                    html_template="email/subscriber_deleted.html")

		flash(f'{deleted_subscriber.username} was deleted and an E-mail was sent', category='info') # type: ignore
		return jsonify({"status": "success", "message": "Subscriber deleted successfully"})
	except:
		db.session.rollback()
		flash('Subscriber was not deleted', category='error')
		return jsonify({"status": "error", "message": "Subscriber deletion failed"})

#---------------------------------oooo000oooo--------------------------------------#

@routes.route("/post_list")
@role_required('user')
def post_list():
	postlist=Post.query.order_by(Post.date_created.desc())
	return render_template("postlist.html", postlist=postlist, user=current_user)


@routes.route("/delete_post/<int:id>", methods=['POST'])
@role_required('user')
def delete_post(id):
	post_to_delete = Post.query.get_or_404(id)
	try:
		deleted_post_file = post_to_delete.htmlfile

		with open(current_app.root_path+"/posts/"+deleted_post_file, 'r', encoding='utf-8') as file:
			html_content = file.read()
			
		soup = BeautifulSoup(html_content, 'html.parser')
		#--------------------------------------------------------------------------
		for img in soup.find_all('img'):
			if img:
				try:
					del_img = re.search(r'''='(.*?)'\)''', img.get('src')).group(1).strip() # type: ignore # type: ignore
					os.remove(current_app.root_path+"/post_media/"+del_img)
					flash(f'{del_img} file was deleted successfully', category='warning')
				except:
					pass				
			else:
				pass
		#--------------------------------------------------------------------------
		#-------------------------------------------------------------------------
		for audio in soup.find_all('audio'):
			if audio:
				try:
					for source in audio.find_all('source'):
						del_audio = re.search(r'''='(.*?)'\)''', source.get('src')).group(1).strip() # type: ignore
						os.remove(current_app.root_path+"/post_media/"+del_audio)
						flash(f'{del_audio} file was deleted successfully', category='info')
				except:
					pass
			else:
				pass

		os.remove(current_app.root_path + "/posts/" + deleted_post_file)

		db.session.delete(post_to_delete)
		db.session.commit()

		flash(f'The post with the url: {post_to_delete.url} was deleted successfully', category='warning')
		return jsonify({"status": "success", "message": "Post deleted successfully"})

	except:
		db.session.rollback()
		flash('Post was not deleted', category='error')
		return jsonify({"status": "error", "message": "Post deletion failed"})

#---------------------------------oooo000oooo--------------------------------------#

@routes.route("/delete_comment/<int:id>", methods=['POST'])
@verification_required()
def delete_comment(id):
	try:
		deleted_comment = db.session.query(Comment).filter_by(id=id).first()
		db.session.delete(deleted_comment)
		db.session.commit()

		flash('Comment was deleted', category='info') # type: ignore
		return jsonify({"status": "success", "message": "Comment deleted successfully"})
	except:
		db.session.rollback()
		flash('Comment was not deleted', category='error')
		return jsonify({"status": "error", "message": "Comment deletion failed"})
