import os
import re
import jwt
import urllib.parse
from zoneinfo import ZoneInfo
from datetime import datetime, timezone
from functools import wraps
from bs4 import BeautifulSoup
from markupsafe import Markup
from random import choice
from flask import (
    Blueprint,
    Response,
    current_app,
    request,
    render_template,
    redirect,
    flash,
    abort,
    jsonify,
    url_for,
    send_from_directory,
)
from flask_login import current_user, login_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from website import generate_token
from .models import Post, Subscriber, Comment, AllUsers
from . import (
    db,
    email,
    SubscriberForm,
    ForgotPasswordForm,
    ResetPasswordForm,
    PostForm,
    LoginForm,
    CommentForm,
)

routes: Blueprint = Blueprint(
    "routes",
    __name__,
    template_folder="../website/posts/",
    static_folder="../website/post_media/",
)


def role_required(role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(403)
            if hasattr(current_user, "user_role") and current_user.user_role == role:
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
            if (
                current_user.user_role == "admin"
                or hasattr(current_user, "verified")
                and current_user.verified == True
            ):
                return f(*args, **kwargs)
            else:
                abort(401)

        return decorated_function

    return decorator


def format_datetime(value, tz_code, format) -> str:
    if value is None:
        return ""
    tz = ZoneInfo(tz_code)
    value = value.astimezone(tz)
    return value.strftime(format)


# ---------------------------------oooo000oooo--------------------------------------#


@routes.route("/")
def index():
    recent_posts = Post.query.order_by(Post.date_created.desc()).all()
    recent_posts_list = []

    for recent_post in recent_posts[:10]:
        recent_post_file = recent_post.html_file

        with open(
            current_app.root_path + "/posts/" + recent_post_file, "r", encoding="utf-8"
        ) as file:
            html_content = file.read()

        soup = BeautifulSoup(html_content, "html.parser")
        # --------------------------------------------------------------------------#
        title = soup.find(id="post_title").text
        banner = soup.find(id="post_banner").get("src")
        banner = re.search(r"""='(.*?)'\)""", str(banner)).group(1).strip()
        date = format_datetime(recent_post.date_created, "Asia/Kolkata", "%d %b, %Y")

        recent_posts_list.append(
            {"title": title, "banner": banner, "url": recent_post.url, "date": date}
        )
    return render_template(
        "index.html", user=current_user, recent_posts_list=recent_posts_list
    )


@routes.route("/about")
def about() -> str:
    return render_template("about.html", user=current_user)


@routes.route("/sitemap.xml")
def sitemap() -> Response:
    return send_from_directory("static", "sitemap.xml")


@routes.route("/robots.txt")
def robots() -> Response:
    return send_from_directory("static", "robots.txt")


# ---------------------------------oooo000oooo--------------------------------------#


@routes.route("/subscribe", methods=["GET", "POST"])
def subscribe() -> str | Response:
    username = None
    email_id = None
    password = None
    confirm_password = None
    form = SubscriberForm()
    if form.validate_on_submit():
        username = form.username.data
        form.username.data = ""
        email_id = form.email_id.data
        form.email_id.data = ""
        password = generate_password_hash(str(form.password.data), method="scrypt")
        form.password.data = ""
        form.confirm_password.data = ""

    # ----------------oo0oo---------------#
    stripped_email = str(email_id).lower().replace(".", "")
    if "+" in stripped_email:
        stripped_email = re.sub(r"""\+(.*?)@""", "", stripped_email)
    else:
        stripped_email = stripped_email.replace("@", "")

    if request.method == "POST":
        if Subscriber.query.filter_by(username=username).first():
            flash("Username is already taken, try a different one", category="warning")
        elif Subscriber.query.filter_by(email_id=email_id).first():
            flash(
                "An account with this E-mail address already exists", category="warning"
            )
        # ---------------------------------------------------------------------
        elif "username" in form.errors:
            flash("Do not use special characters", category="error")
        elif stripped_email == "shetty777bloggmailcom":
            flash(
                "No no no! Don't do that, that is my e-mail address", category="warning"
            )
        elif "email_id" in form.errors:
            flash("The E-mail address you provided is not valid", category="error")
        elif "password" in form.errors:
            flash(
                "Looks like the two passwords don't match. Make sure they are the same",
                category="error",
            )
        # ---------------------------------------------------------------------
        elif not form.errors:
            try:
                new_subscriber = Subscriber(
                    username=username,
                    email_id=email_id,
                    password=password,
                    user_role="subscriber",
                )
                db.session.add(new_subscriber)
                db.session.commit()

                email.send(
                    subject="E-mail verification for Shetty777",
                    receivers=email_id,
                    body_params={
                        "token": generate_token.generate_token(email_id, "Fresh", 10)
                    },
                    html_template="email/verify.html",
                )

                return render_template("verify_email.html", user=current_user)
            except Exception as e:
                db.session.rollback()
                flash(f"Something didn't go right {e}", category="error")
                return jsonify({"status": "error", "message": e})

    return render_template(
        "subscribe.html",
        user=current_user,
        username=username,
        email_id=email_id,
        password=password,
        confirm_password=confirm_password,
        form=form,
    )


@routes.route("/send_manual_verification")
@role_required("admin")
def send_manual_verification():
    try:
        email_id = urllib.parse.unquote(request.args.get("email"))
        email.send(
            subject="E-mail verification for Shetty777",
            receivers=email_id,
            body_params={"token": generate_token.generate_token(email_id, "Fresh", 10)},
            html_template="email/verify_refreshed.html",
        )
        flash("Verification E-mail sent to", category="success")
    except Exception as e:
        flash(f"Something didn't go right {e}", category="error")
        return jsonify({"status": "error", "message": e})
    return redirect("/subscriber_list")


@routes.route("/verify_email/<token>")
def verify_email(token):
    try:
        token_data = jwt.decode(
            token,
            current_app.config["SECRET_KEY"],
            algorithms=["HS256"],
            options={"verify_exp": False},
        )
        email_id = token_data["email_id"]
        token_type = token_data["token_type"]
        exp = token_data["exp"]
        new_subscriber = Subscriber.query.filter_by(email_id=email_id).first()
        if int(datetime.now(tz=timezone.utc).timestamp()) < exp:
            try:
                if new_subscriber.verified == False:
                    new_subscriber.verified = True
                    db.session.commit()

                    login_user(new_subscriber, remember=True)
                    flash(
                        "Congratulations! You are now subscribed to Shetty777",
                        category="success",
                    )

                elif new_subscriber.verified == True:
                    flash(
                        "Your E-mail address has already been verified",
                        category="success",
                    )
                else:
                    pass
            except Exception as e:
                db.session.rollback()
                flash(f"Something didn't go right {e}", category="error")
                return jsonify({"status": "error", "message": e})

        elif (
            token_type == "Fresh"
            and int(datetime.now(tz=timezone.utc).timestamp()) >= exp
        ):
            if new_subscriber.verified == False:
                email.send(
                    subject="E-mail verification for Shetty777 [Refreshed token]",
                    receivers=new_subscriber.email_id,
                    body_params={
                        "token": generate_token.generate_token(
                            email_id, "Refresh", 4320
                        )
                    },
                    html_template="email/verify_refreshed.html",
                )
                return render_template("verify_email_refreshed.html", user=current_user)
            elif new_subscriber.verified == True:
                flash(
                    "Your E-mail address has already been verified", category="success"
                )
            else:
                pass

        elif (
            token_type == "Refresh"
            and int(datetime.now(tz=timezone.utc).timestamp()) >= exp
        ):
            if new_subscriber.verified == False:
                email_to_verify = (
                    Subscriber.query.filter_by(email_id=email_id).first().email_id
                )
                flash(
                    Markup(
                        f'Even your refresh token expired! <a href="mailto:shetty777.blog@gmail.com?subject=Verification%20token%20refresh%20request&body=With%20this%20E-mail,%20I%20request%20you%20to%20refresh%20my%20verification%20token%20to%20subscribe%20to%20Shetty777%0AI%20understand%20that%20not%20verifying%20with%20this%20new%20token%20will%20lead%20to%20my%20account%20having%20limited%20access.%0AThe%20E-mail%20address%20is,%20{email_to_verify}">Request to get a new refresh token for your account</a>'
                    ),
                    category="error",
                )
                return redirect("/")
            elif new_subscriber.verified == True:
                flash(
                    "Your E-mail address has already been verified", category="success"
                )
            else:
                pass
    except:
        flash(
            "Looks like the verification token is invalid. Try again.", category="error"
        )
        return redirect("/")

    return redirect("/")


@routes.route("/login", methods=["GET", "POST"])
def login():
    username_or_email_id = None
    password = None
    form = LoginForm()
    if form.validate_on_submit():
        username_or_email_id = form.username_or_email_id.data
        form.username_or_email_id.data = ""
        password = form.password.data
        form.password.data = ""
    if request.method == "POST":
        subscriber = Subscriber.query.filter_by(username=username_or_email_id).first()
        subscriber_email = Subscriber.query.filter_by(
            email_id=username_or_email_id
        ).first()
        if subscriber:
            if check_password_hash(subscriber.password, password):
                login_user(subscriber, remember=True)
                flash(
                    "Successfully logged into your subscriber account",
                    category="success",
                )
                return redirect("/")
            else:
                flash("Password is incorrect", category="error")
        elif subscriber_email:
            if check_password_hash(subscriber_email.password, password):
                login_user(subscriber_email, remember=True)
                flash(
                    "Successfully logged into your subscriber account !!!",
                    category="success",
                )
                return redirect("/")
            else:
                flash("Password is incorrect", category="error")
        else:
            flash(
                "An account with the username or E-mail you have provided does not exist",
                category="error",
            )
    return render_template(
        "login.html",
        user=current_user,
        username_or_email_id=username_or_email_id,
        password=password,
        form=form,
    )


@routes.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out", category="info")
    return redirect("/")


@routes.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():
    username_or_email_id = None
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        username_or_email_id = form.username_or_email_id.data
        form.username_or_email_id.data = ""
    if request.method == "POST":
        username = Subscriber.query.filter_by(username=username_or_email_id).first()
        email_id = Subscriber.query.filter_by(email_id=username_or_email_id).first()
        if username or email_id:
            email_id = (
                username.email_id if username is not None else username_or_email_id
            )
            email.send(
                subject="Password Reset for you subscription at Shetty777",
                receivers=email_id,
                body_params={
                    "token": generate_token.generate_token(email_id, "Reset", 5)
                },
                html_template="email/password_reset.html",
            )
            flash(f"A password reset link has been sent to {email_id}", category="info")
            return redirect("/")
        else:
            flash(
                "A subscriber with that username or E-mail address does not exist",
                category="warning",
            )
            return redirect("/")

    return render_template(
        "forgot_password.html",
        user=current_user,
        username_or_email_id=username_or_email_id,
        form=form,
    )


@routes.route("/reset_password/<token>", methods=["GET", "POST"])
def reset_password(token):
    try:
        token_data = jwt.decode(
            token,
            current_app.config["SECRET_KEY"],
            algorithms=["HS256"],
            options={"verify_exp": False},
        )
        email_id = token_data["email_id"]
        token_type = token_data["token_type"]
        exp = token_data["exp"]
        password_forgetter = Subscriber.query.filter_by(email_id=email_id).first()

        if (
            token_type == "Reset"
            and int(datetime.now(tz=timezone.utc).timestamp()) < exp
        ):
            try:
                if password_forgetter.verified == True:
                    new_password = None
                    confirm_new_password = None
                    form = ResetPasswordForm()
                    if form.validate_on_submit():
                        new_password = generate_password_hash(
                            str(form.new_password.data), method="scrypt"
                        )
                        form.new_password.data = ""
                        form.confirm_new_password.data = ""
                    if request.method == "POST":
                        setattr(password_forgetter, "password", new_password)
                        db.session.commit()
                        flash(
                            "You can now login with your new password",
                            category="success",
                        )
                        return redirect("/login")

                elif password_forgetter.verified == False:
                    flash(
                        "Your E-mail address has not been verified. Contact the administrator for support",
                        category="warning",
                    )

            except Exception as e:
                db.session.rollback()
                flash(f"Something didn't go right {e}", category="error")
                return jsonify({"status": "error", "message": e})

        elif (
            token_type == "Reset"
            and int(datetime.now(tz=timezone.utc).timestamp()) >= exp
        ):
            flash(
                "Oops! Too long... You reset token expired. Try again",
                category="warning",
            )
        else:
            flash("Hey, Don't do that! That token should not be here", category="error")
            return redirect("/")
    except:
        flash(
            "Looks like the password reset token is invalid. Try again.",
            category="error",
        )
        return redirect("/")
    return render_template(
        "reset_password.html",
        user=current_user,
        email_id=email_id,
        new_password=new_password,
        confirm_new_password=confirm_new_password,
        form=form,
    )


# ---------------------------------oooo000oooo--------------------------------------#


@routes.route("/dashboard/<path:username>")
@login_required
def dashboard(username):
    try:
        usrname = urllib.parse.unquote(username).replace("/", "")
        user = db.session.query(AllUsers).filter_by(username=usrname).first()
        if user and current_user.username == user.username:
            marked_posts = user.marked_posts
            marked_posts_list = []

            for marked_post in marked_posts:
                marked_post_file = marked_post.html_file

                with open(
                    current_app.root_path + "/posts/" + marked_post_file,
                    "r",
                    encoding="utf-8",
                ) as file:
                    html_content = file.read()

                soup = BeautifulSoup(html_content, "html.parser")
                # --------------------------------------------------------------------------#
                title_h1_element = soup.find(id="post_title")

                if title_h1_element:
                    title = title_h1_element.text

                marked_posts_list.append(
                    {
                        "title": title,
                        "category": marked_post.category,
                        "url": marked_post.url,
                    }
                )

            return render_template(
                "dashboard.html", user=current_user, marked_posts_list=marked_posts_list
            )
        else:
            flash("You cannot access other users' dashboards!", category="warning")
            return redirect("/")

    except:
        flash(
            f"Looks like the user does not exist; so their dashboard cannot be opened",
            category="warning",
        )
        return redirect("/")


# ---------------------------------oooo000oooo--------------------------------------#


@routes.route("/articles")
def articles():
    articles = (
        Post.query.filter_by(category="Article")
        .order_by(Post.date_created.desc())
        .all()
    )
    articles_list = []

    for article in articles:
        article_file = article.html_file

        with open(
            current_app.root_path + "/posts/" + article_file, "r", encoding="utf-8"
        ) as file:
            html_content = file.read()

        soup = BeautifulSoup(html_content, "html.parser")
        # --------------------------------------------------------------------------#
        title = soup.find(id="post_title").text
        banner = soup.find(id="post_banner").get("src")
        banner = re.search(r"""='(.*?)'\)""", str(banner)).group(1).strip()
        date = format_datetime(article.date_created, "Asia/Kolkata", "%d %b, %Y")

        articles_list.append(
            {"title": title, "banner": banner, "url": article.url, "date": date}
        )

    return render_template(
        "articles.html", user=current_user, articles_list=articles_list
    )


@routes.route("/projects")
def projects():
    projects = (
        Post.query.filter_by(category="Project")
        .order_by(Post.date_created.desc())
        .all()
    )

    projects_list = []
    for project in projects:
        project_file = project.html_file

        with open(
            current_app.root_path + "/posts/" + project_file, "r", encoding="utf-8"
        ) as file:
            html_content = file.read()

        soup = BeautifulSoup(html_content, "html.parser")
        # --------------------------------------------------------------------------#
        title = soup.find(id="post_title").text
        banner = soup.find(id="post_banner").get("src")
        banner = re.search(r"""='(.*?)'\)""", str(banner)).group(1).strip()
        date = format_datetime(project.date_created, "Asia/Kolkata", "%d %b, %Y")

        projects_list.append(
            {"title": title, "banner": banner, "url": project.url, "date": date}
        )

    return render_template(
        "projects.html", user=current_user, projects_list=projects_list
    )


@routes.route("/blogs")
def blogs():
    blogs = (
        Post.query.filter_by(category="Blog").order_by(Post.date_created.desc()).all()
    )
    for blog in blogs:
        print(blog)
    return render_template("blogs.html", user=current_user)


# ---------------------------------oooo000oooo--------------------------------------#


@routes.route("/post", methods=["GET", "POST"])
@role_required("admin")
def post():
    html_file = None
    images = None
    category = None
    author = None
    url = None
    audios = None
    form = PostForm()
    if form.validate_on_submit():
        html_file = form.html_file.data
        form.html_file.data = ""
        images = form.images.data
        form.images.data = []
        audios = form.audios.data
        form.audios.data = ""
        category = form.category.data
        form.category.data = ""
        author = form.author.data
        form.author.data = ""
        url = form.url.data
        form.url.data = ""

    if request.method == "POST":
        post_url_exists = Post.query.filter_by(url=url).first()

        if post_url_exists:
            flash("A post with this URL already exists", category="werror")
        elif "category" in form.errors:
            flash("Category must be 'Article' or 'Project' or 'Blog'", category="error")
        elif "author" in form.errors:
            flash("The author must be one of the authors listed", category="error")
        elif "url" in form.errors:
            flash(
                "The following characters are not allowed '\"`@^()|\\/[] {}><",
                category="error",
            )
        elif "html_file" in form.errors:
            flash("Only HTML files are accepted", category="error")
        elif "images" in form.errors:
            flash(
                "Only images (.jpg, .jpeg, .png, .svg, .webp, .gif) are accepted",
                category="error",
            )
        elif "audios" in form.errors:
            flash("Only .mp3, .wav & .ogg files are accepted", category="error")
        # ---------------------------------------------------------------------

        elif not form.errors:
            try:
                html_filename = secure_filename(html_file.filename)
                if not os.path.isfile(f"{current_app.root_path}/posts/{html_filename}"):
                    html_file.save(
                        os.path.join(current_app.root_path, "posts", html_filename)
                    )
                    flash(
                        f"Successfully uploaded file: {html_filename}", category="info"
                    )
                else:
                    flash(f"File {html_filename} already exists", category="error")
                    return redirect("/post")

                try:
                    for audio in audios:
                        audio_filename = secure_filename(audio.filename)
                        if not os.path.isfile(
                            f"{current_app.root_path}/post_media/{audio_filename}"
                        ):
                            audio.save(
                                os.path.join(
                                    current_app.root_path, "post_media", audio_filename
                                )
                            )
                            flash(
                                f"Successfully uploaded file: {audio_filename}",
                                category="info",
                            )
                        else:
                            flash(
                                f"File {audio_filename} already exists",
                                category="error",
                            )
                            return redirect("/post")
                except Exception as e:
                    flash(f"No audio files; proceeded...", category="info")

                for image in images:
                    image_filename = secure_filename(image.filename)
                    if not os.path.isfile(
                        f"{current_app.root_path}/post_media/{image_filename}"
                    ):
                        image.save(
                            os.path.join(
                                current_app.root_path, "post_media", image_filename
                            )
                        )
                        flash(
                            f"Successfully uploaded file: {image_filename}",
                            category="info",
                        )
                    else:
                        flash(f"File {image_filename} already exists", category="error")
                        return redirect("/post")

            except Exception as e:
                flash(f"File upload failed: {e}", category="error")
                return redirect("/post")

            # --------------------------------------------------------------------------#

            try:
                new_post = Post(
                    html_file=html_filename, category=category, author=author, url=url
                )
                db.session.add(new_post)
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                flash(f"Something didn't go right {e}", category="error")
                return jsonify({"status": "error", "message": e})

            post_for_mail = db.session.query(Post).filter_by(url=url).first()
            with open(
                current_app.root_path + "/posts/" + post_for_mail.html_file,
                "r",
                encoding="utf-8",
            ) as file:
                html_content = file.read()

            soup = BeautifulSoup(html_content, "html.parser")
            # --------------------------------------------------------------------------#
            title = soup.find(id="post_title").text

            email_list = [
                email[0] for email in db.session.query(Subscriber.email_id).all()
            ]
            if len(email_list) > 0:
                email.send(
                    subject=choice(
                        [
                            "Brand new post buzz on Shetty777!",
                            "Catch the latest scoop on Shetty777!",
                            "Discover what’s new on Shetty777!",
                            "Explore the newest post on Shetty777!",
                            "Fresh content just posted on Shetty777!",
                            "Latest update now live on Shetty777!",
                        ]
                    ),
                    receivers="Shetty777 Subscribers",
                    bcc=email_list,
                    body_params={
                        "category": post_for_mail.category,
                        "url": post_for_mail.url,
                        "title": title,
                        "author": author,
                    },
                    text=f"Dear subscriber,\n I'm excited to share a new post on Shetty777! The latest { category } is now online.\n\n\nI am glad to have you on board and appreciate your support :)\n\nBest regards,\nShashank S Shetty",
                    html_template="email/new_post.html",
                )
        else:
            pass

        flash(
            f"Successfully created a new post; and sent notification to  {len(email_list)}  E-mail addresses",
            category="success",
        )
        return redirect("/")

    return render_template(
        "post.html",
        user=current_user,
        html_file=html_file,
        images=images,
        category=category,
        url=url,
        form=form,
    )


# ---------------------------------oooo000oooo--------------------------------------#


@routes.route("/web_posts/<post_url>", methods=["POST", "GET"])
def web_posts(post_url):
    try:
        rating = None
        text_content = None
        avg_rating = None
        form = CommentForm()
        if form.validate_on_submit():
            rating = form.rating.data
            form.rating.data = ""
            text_content = form.text_content.data
            form.text_content.data = ""

        post = db.session.query(Post).filter_by(url=post_url).first()
        post_file = str(post.html_file).replace("<FileStorage: '", "")
        post_file = post_file.replace("' ('text/html')>", "")

        comments = (
            db.session.query(Comment)
            .filter_by(post_id=post.id)
            .order_by(Comment.date_created.desc())
            .all()
        )
        comment_list = []
        if comments:
            for comment in comments:
                commentator = (
                    db.session.query(AllUsers).filter_by(id=comment.commentator).first()
                )
                comment_list.append(
                    {
                        "id": comment.id,
                        "commentator": commentator,
                        "rating": comment.rating,
                        "text_content": comment.text_content,
                        "date": format_datetime(
                            comment.date_created, "Asia/Kolkata", "%d %b, %Y"
                        ),
                    }
                )

        ratings = [
            item["rating"] for item in comment_list if item["rating"] is not None
        ]
        if len(ratings) != 0:
            avg_rating = round(sum(ratings) / len(ratings), 1)
        else:
            avg_rating = "No ratings"

        if hasattr(current_user, "id"):
            user_comments = Comment.query.filter_by(
                post_id=post.id, commentator=current_user.id
            ).count()
        else:
            user_comments = 1

        if request.method == "POST":
            if not form.errors:
                if (
                    hasattr(current_user, "user_role")
                    and current_user.user_role != "admin"
                    and current_user.verified == True
                    and user_comments < 1
                ):
                    if rating != None:
                        try:
                            new_comment = Comment(
                                rating=rating,
                                text_content=text_content,
                                commentator=current_user.id,
                                post_id=post.id,
                            )
                            db.session.add(new_comment)
                            db.session.commit()
                            email.send(
                                subject="Someone commented on a post",
                                receivers="shetty777.blog@gmail.com",
                                text=f"There is a new comment on <a href='https://shetty777.koyeb.app/web_posts/{post_url}'>this post</a>.",
                            )
                            flash("You commented on this post", category="success")
                        except Exception as e:
                            db.session.rollback()
                            return jsonify({"status": "error", "message": e})
                        return redirect(url_for("routes.web_posts", post_url=post_url))
                    else:
                        flash("A comment must contain some rating", category="warning")
                        return redirect(url_for("routes.web_posts", post_url=post_url))
                elif current_user.verified != True:
                    flash(
                        "You must be a verified subscriber to comment",
                        category="warning",
                    )
                    return redirect(url_for("routes.web_posts", post_url=post_url))
                elif (
                    hasattr(current_user, "user_role")
                    and current_user.user_role == "admin"
                ):
                    if text_content == None:
                        flash("Admin comment must contain text", category="warning")
                        return redirect(url_for("routes.web_posts", post_url=post_url))
                    else:
                        try:
                            new_comment = Comment(
                                rating=None,
                                text_content=text_content,
                                commentator=current_user.id,
                                post_id=post.id,
                            )
                            db.session.add(new_comment)
                            db.session.commit()
                            flash("You commented on this post", category="success")
                        except Exception as e:
                            db.session.rollback()
                            return jsonify({"status": "error", "message": e})
                        return redirect(url_for("routes.web_posts", post_url=post_url))
                else:
                    flash(
                        "You can only rate/comment once on a post", category="warning"
                    )
                    return redirect(url_for("routes.web_posts", post_url=post_url))
        return render_template(
            post_file,
            user=current_user,
            current_post=post,
            author=post.author,
            rating=rating,
            text_content=text_content,
            comment_list=comment_list,
            form=form,
            avg_rating=avg_rating,
            user_comments=user_comments,
        )

    except Exception as e:
        flash(f"There is no post of that name {e}", category="warning")
        return redirect("/")


@routes.route("/mark_post/<userid>/<postid>", methods=["POST"])
@verification_required()
def mark_post(userid, postid):
    user = db.session.query(AllUsers).filter_by(id=userid).first()
    post = db.session.query(Post).filter_by(id=postid).first()
    if user and user == current_user:
        try:
            user.marked_posts.append(post)
            db.session.commit()
            return jsonify({"status": "success", "message": "Post marked successfully"})
        except:
            db.session.rollback()
            abort(404)
    elif user is None:
        flash("There is no such user", category="warning")
        return redirect(url_for("routes.web_posts", post_url=post.post_url))
    elif post is None:
        flash("There is no such post", category="warning")
        return redirect(url_for("routes.web_posts", post_url=post.post_url))
    else:
        flash("You cannot mark posts for other subscribers", category="warning")
        return redirect(url_for("routes.web_posts", post_url=post.post_url))


@routes.route("/unmark_post/<userid>/<postid>", methods=["POST"])
@verification_required()
def unmark_post(userid, postid):
    user = db.session.query(AllUsers).filter_by(id=userid).first()
    post = db.session.query(Post).filter_by(id=postid).first()
    if user and user == current_user:
        try:
            user.marked_posts.remove(post)
            db.session.commit()
            return jsonify(
                {"status": "success", "message": "Post unmarked successfully"}
            )
        except:
            db.session.rollback()
            abort(404)
    elif user is None:
        flash("There is no such user", category="warning")
        return redirect(url_for("routes.web_posts", post_url=post.post_url))
    elif post is None:
        flash("There is no such post", category="warning")
        return redirect(url_for("routes.web_posts", post_url=post.post_url))
    else:
        flash("You cannot unmark posts for other subscribers", category="warning")
        return redirect(url_for("routes.web_posts", post_url=post.post_url))


# ---------------------------------oooo000oooo--------------------------------------#


@routes.route("/subscriber_list")
@role_required("admin")
def subscriber_list():
    subscriber_list = Subscriber.query.order_by(Subscriber.date_subscribed)
    return render_template(
        "subscriber_list.html", subscriber_list=subscriber_list, user=current_user
    )


@routes.route("/delete_subscriber/<int:id>", methods=["POST"])
@role_required("admin")
def delete_subscriber(id):
    try:
        deleted_subscriber = db.session.query(Subscriber).filter_by(id=id).first()
        db.session.delete(deleted_subscriber)
        db.session.commit()

        email.send(
            subject="Subscriber account deleted",
            receivers=deleted_subscriber.email_id,
            html_template="email/subscriber_deleted.html",
        )

        flash(
            f"{deleted_subscriber.username} was deleted and an E-mail was sent",
            category="info",
        )
        return jsonify(
            {"status": "success", "message": "Subscriber deleted successfully"}
        )
    except Exception as e:
        db.session.rollback()
        flash("Subscriber was not deleted", category="error")
        return jsonify({"status": "error", "message": e})


# ---------------------------------oooo000oooo--------------------------------------#


@routes.route("/post_list")
@role_required("admin")
def post_list():
    post_list = Post.query.order_by(Post.date_created.desc())
    return render_template("post_list.html", post_list=post_list, user=current_user)


@routes.route("/delete_post/<int:id>", methods=["POST"])
@role_required("admin")
def delete_post(id):
    post_to_delete = Post.query.get_or_404(id)
    try:
        deleted_post_file = post_to_delete.html_file

        with open(
            current_app.root_path + "/posts/" + deleted_post_file, "r", encoding="utf-8"
        ) as file:
            html_content = file.read()

        soup = BeautifulSoup(html_content, "html.parser")
        # --------------------------------------------------------------------------#
        for img in soup.find_all("img"):
            if img and img != soup.find(id="author_img"):
                try:
                    del_img = (
                        re.search(r"""='(.*?)'\)""", img.get("src")).group(1).strip()
                    )
                    os.remove(current_app.root_path + "/post_media/" + del_img)
                    flash(f"{del_img} file was deleted successfully", category="info")
                except Exception as e:
                    return jsonify({"status": "error", "message": e})
            else:
                pass
        # --------------------------------------------------------------------------#
        # -------------------------------------------------------------------------
        for audio in soup.find_all("audio"):
            if audio:
                try:
                    for source in audio.find_all("source"):
                        del_audio = (
                            re.search(r"""='(.*?)'\)""", source.get("src"))
                            .group(1)
                            .strip()
                        )
                        os.remove(current_app.root_path + "/post_media/" + del_audio)
                        flash(
                            f"{del_audio} file was deleted successfully",
                            category="info",
                        )
                except Exception as e:
                    return jsonify({"status": "error", "message": e})
            else:
                pass

        os.remove(current_app.root_path + "/posts/" + deleted_post_file)

        db.session.delete(post_to_delete)
        db.session.commit()

        flash(
            f"The post with the URL: {post_to_delete.url} was deleted successfully",
            category="info",
        )
        return jsonify({"status": "success", "message": "Post deleted successfully"})

    except Exception as e:
        db.session.rollback()
        flash("Post was not deleted", category="error")
        return jsonify({"status": "error", "message": e})


# ---------------------------------oooo000oooo--------------------------------------#


@routes.route("/delete_comment/<int:id>", methods=["POST"])
@verification_required()
def delete_comment(id):
    try:
        deleted_comment = db.session.query(Comment).filter_by(id=id).first()
        if (
            deleted_comment.commentator == current_user.id
            or current_user.user_role == "admin"
        ):
            db.session.delete(deleted_comment)
            db.session.commit()

            flash("Comment was deleted", category="info")
            return jsonify(
                {"status": "success", "message": "Comment deleted successfully"}
            )
        else:
            flash("You cannot delete other users comments", category="warning")
            return redirect("/")
    except Exception as e:
        db.session.rollback()
        flash("Comment was not deleted", category="error")
        return jsonify({"status": "error", "message": e})
