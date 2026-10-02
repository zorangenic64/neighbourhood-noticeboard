from flask import Flask, render_template, request, redirect, url_for, abort, jsonify, session, flash, get_flashed_messages

from flask_login import (
    LoginManager,
    login_user,
    logout_user,
    current_user,
    login_required
)

from flask_wtf.csrf import CSRFProtect

from werkzeug.security import (
    check_password_hash,
    generate_password_hash
)

from models.models import db, Post, User, PostPick, Comment


from datetime import datetime, timedelta

from zxcvbn import zxcvbn

from utils.text_filter import contains_blocked_word

from utils.location_data import load_location_choices

from utils.proximity import post_is_within_distance

from sqlalchemy import and_, inspect, or_, text
from threading import Lock

USERNAME_MIN_LENGTH = 3
USERNAME_MAX_LENGTH = 25
PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 25
RESET_PASSWORD_MIN_LENGTH = PASSWORD_MIN_LENGTH
SECURITY_QUESTION_MIN_LENGTH = 1
SECURITY_QUESTION_MAX_LENGTH = 25
SECURITY_ANSWER_MIN_LENGTH = 1
SECURITY_ANSWER_MAX_LENGTH = 25
POST_TITLE_MIN_LENGTH = 6
POST_TITLE_MAX_LENGTH = 50
POST_BODY_MIN_LENGTH = 1
POST_BODY_MAX_LENGTH = 1000
COMMENT_MIN_LENGTH = 1
COMMENT_MAX_LENGTH = 300
POST_EXPIRY_CHOICES = (7, 14, 30)

app = Flask(__name__)


app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///noticeboard.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Required for Flask sessions/login
app.config["SECRET_KEY"] = "8c10d156b76463f19d63d50d542b558404cb744a2f15f14a72f0bdeb38e553ce"

csrf = CSRFProtect(app)

db.init_app(app)

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

_post_expiry_schema_checked = False
_post_expiry_schema_lock = Lock()


@app.before_request
def ensure_post_expiry_schema():
    global _post_expiry_schema_checked

    if _post_expiry_schema_checked:
        return

    with _post_expiry_schema_lock:
        if _post_expiry_schema_checked:
            return

        inspector = inspect(db.engine)
        if not inspector.has_table("post"):
            return

        columns = {column["name"] for column in inspector.get_columns("post")}
        if "expires_in_days" not in columns:
            with db.engine.begin() as connection:
                connection.execute(text(
                    "ALTER TABLE post ADD COLUMN expires_in_days "
                    "INTEGER NOT NULL DEFAULT 7"
                ))

        _post_expiry_schema_checked = True


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route("/")
def home():
    clear_comment_state = session.pop("clear_comment_state", False)
    selected_category = request.args.get("category")
    picked_filter = request.args.get("picked")
    search_text = request.args.get("search", "").strip()
    distance = request.args.get("distance", "Any")
    date_filter = request.args.get("date_filter", "All")
    if date_filter not in {"All", "Last 24hr", "Last 7 Days", "Last Week"}:
        date_filter = "All"

    if not current_user.is_authenticated:
        distance = "Any"

    query = Post.query

    if not current_user.is_authenticated:
        query = query.filter(Post.visibility == "public")

    if selected_category:
        query = query.filter(Post.category == selected_category)

    now = datetime.utcnow()
    if date_filter == "Last 24hr":
        cutoff = now - timedelta(hours=24)
        query = query.filter(
            or_(
                Post.created_at >= cutoff,
                Post.comments.any(Comment.created_at >= cutoff)
            )
        )
    elif date_filter == "Last 7 Days":
        cutoff = now - timedelta(days=7)
        query = query.filter(
            or_(
                Post.created_at >= cutoff,
                Post.comments.any(Comment.created_at >= cutoff)
            )
        )
    elif date_filter == "Last Week":
        week_start = now - timedelta(days=14)
        week_end = now - timedelta(days=7)
        post_created_last_week = and_(
            Post.created_at >= week_start,
            Post.created_at < week_end
        )
        comment_created_last_week = Post.comments.any(
            and_(
                Comment.created_at >= week_start,
                Comment.created_at < week_end
            )
        )
        query = query.filter(
            or_(post_created_last_week, comment_created_last_week)
        )

    if picked_filter == "1" and current_user.is_authenticated:
        picked_post_ids = [
            p.post_id for p in current_user.picked_posts
        ]
        if picked_post_ids:
            query = query.filter(Post.id.in_(picked_post_ids))
        else:
            query = query.filter(Post.id.in_([]))

    # text search: tokens separated by spaces are ANDed across title and body
    if search_text:
        tokens = search_text.split()
        for token in tokens:
            term = f"%{token}%"
            query = query.filter(
                or_(
                    Post.title.ilike(term),
                    Post.body.ilike(term)
                )
            )

    posts = query.order_by(Post.created_at.desc()).all()

    if current_user.is_authenticated and distance != "Any":
        user_loc = current_user.default_location
        posts = [
            post for post in posts
            if post_is_within_distance(post.location, user_loc, distance)
        ]

    picked_post_ids = []
    if current_user.is_authenticated:
        picked_post_ids = [p.post_id for p in current_user.picked_posts]

    return render_template(
        "index.html",
        posts=posts,
        selected_category=selected_category,
        picked_filter=bool(picked_filter == "1"),
        picked_post_ids=picked_post_ids,
        search_text=search_text,
        distance=distance,
        date_filter=date_filter,
        clear_comment_state=clear_comment_state
    )

@app.route("/login", methods=["GET", "POST"])
def login():

    error = None

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        user = User.query.filter_by(
            username=username
        ).first()

        if user and check_password_hash(
            user.password_hash,
            password
        ):
            
            user.last_login = datetime.utcnow()
            db.session.commit()
        
            login_user(user)
            session["clear_comment_state"] = True
            return redirect(url_for("home"))

        error = "Invalid username or password"

    return render_template(
        "login.html",
        error=error
    )

@app.route("/check-username")
def check_username():

    username = request.args.get(
        "username",
        ""
    ).strip()

    if not username:
        return jsonify({
            "valid": False,
            "message": "Username cannot be empty."
        })

    if not USERNAME_MIN_LENGTH <= len(username) <= USERNAME_MAX_LENGTH:
        return jsonify({
            "valid": False,
            "message": "Username must be between 3 and 25 characters."
        })

    if contains_blocked_word(username):
        return jsonify({
            "valid": False,
            "message": "That username is not allowed."
        })

    if User.query.filter_by(
        username=username
    ).first():

        return jsonify({
            "valid": False,
            "message": "That username is already taken."
        })

    return jsonify({
        "valid": True,
        "message": "Username is available."
    })

@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():

    error = None
    session.pop("recovery_user_id", None)
    session.pop("recovery_verified", None)

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        if not username:

            error = "Please enter your username."

        elif not USERNAME_MIN_LENGTH <= len(username) <= USERNAME_MAX_LENGTH:

            error = "Username must be between 3 and 25 characters."

        else:

            user = User.query.filter_by(
                username=username
            ).first()

            if not user:

                error = "Username not found."

            else:

                session["recovery_user_id"] = user.id

                return redirect(
                    url_for("forgot_password_question")
                )

    return render_template(
        "forgot_password.html",
        error=error
    )

@app.route("/forgot-password/cancel")
def cancel_password_recovery():
    session.pop("recovery_user_id", None)
    session.pop("recovery_verified", None)
    return redirect(url_for("home"))

@app.route(
    "/forgot-password/question",
    methods=["GET", "POST"]
)
def forgot_password_question():

    error = None

    user_id = session.get(
        "recovery_user_id"
    )

    if not user_id:
        return redirect(
            url_for("forgot_password")
        )

    user = User.query.get(user_id)

    if not user:
        session.pop(
            "recovery_user_id",
            None
        )

        return redirect(
            url_for("forgot_password")
        )

    if request.method == "POST":

        security_answer = request.form.get(
            "security_answer",
            ""
        ).strip()

        if not security_answer:

            error = (
                "Please enter your security answer."
            )

        elif len(security_answer) > SECURITY_ANSWER_MAX_LENGTH:

            error = "Security answer must be no more than 25 characters."

        elif not check_password_hash(
            user.security_answer_hash,
            security_answer.lower()
        ):

            error = "Incorrect security answer."

        else:

            session["recovery_verified"] = True

            return redirect(
                url_for("reset_password")
            )

    return render_template(
        "forgot_password_question.html",
        security_question=user.security_question,
        error=error
    )

@app.route(
    "/reset-password",
    methods=["GET", "POST"]
)
def reset_password():

    error = None
    password_strength = None
    password_score = None

    # Make sure the recovery process has been verified
    if not session.get("recovery_verified"):
        return redirect(
            url_for("forgot_password")
        )

    user_id = session.get(
        "recovery_user_id"
    )

    if not user_id:
        session.pop(
            "recovery_verified",
            None
        )

        return redirect(
            url_for("forgot_password")
        )

    user = User.query.get(user_id)

    if not user:

        session.pop(
            "recovery_user_id",
            None
        )

        session.pop(
            "recovery_verified",
            None
        )

        return redirect(
            url_for("forgot_password")
        )

    if request.method == "POST":

        new_password = request.form.get(
            "new_password",
            ""
        )

        confirm_password = request.form.get(
            "confirm_password",
            ""
        )

        if not new_password:

            error = "Password cannot be empty."

        elif len(new_password) > PASSWORD_MAX_LENGTH:

            error = "Password must be no more than 25 characters long."

        elif new_password != confirm_password:

            error = "Passwords do not match."

        else:

            has_minimum_length = (
                len(new_password) >= RESET_PASSWORD_MIN_LENGTH
            )

            has_uppercase = any(
                character.isupper()
                for character in new_password
            )

            has_digit = any(
                character.isdigit()
                for character in new_password
            )

            has_symbol = any(
                not character.isalnum()
                for character in new_password
            )

            strength_result = zxcvbn(
                new_password
            )

            password_score = (
                strength_result["score"]
            )

            strength_names = {
                0: "Very Weak",
                1: "Weak",
                2: "Fair",
                3: "Strong",
                4: "Very Strong"
            }

            password_strength = (
                strength_names[password_score]
            )

            if not has_minimum_length:

                error = (
                    "Password must be at least "
                    f"{RESET_PASSWORD_MIN_LENGTH} characters long."
                )

            elif not has_uppercase:

                error = (
                    "Password must contain at least "
                    "one capital letter."
                )

            elif not has_digit:

                error = (
                    "Password must contain at least "
                    "one number."
                )

            elif not has_symbol:

                error = (
                    "Password must contain at least "
                    "one symbol."
                )

            elif password_score < 2:

                error = (
                    "This password is too easy to guess. "
                    "Please choose a stronger password."
                )

            else:

                user.password_hash = (
                    generate_password_hash(
                        new_password
                    )
                )

                db.session.commit()

                # Clear the recovery process
                session.pop(
                    "recovery_user_id",
                    None
                )

                session.pop(
                    "recovery_verified",
                    None
                )

                # Automatically log the user in
                login_user(user)

                return redirect(
                    url_for("home")
                )

    return render_template(
        "reset_password.html",
        error=error,
        password_strength=password_strength,
        password_score=password_score
    )

@app.route("/register", methods=["GET", "POST"])
def register():
    error = None
    locations = load_location_choices()

    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]
        security_question = request.form["security_question"]
        security_answer = request.form["security_answer"].strip().lower()
        default_location = request.form.get("default_location", "Unknown")

        if default_location not in locations:
            default_location = "Unknown"

        if not USERNAME_MIN_LENGTH <= len(username) <= USERNAME_MAX_LENGTH:
            error = "Username must be between 3 and 25 characters."
        elif not PASSWORD_MIN_LENGTH <= len(password) <= PASSWORD_MAX_LENGTH:
            error = "Password must be between 8 and 25 characters."
        elif not SECURITY_QUESTION_MIN_LENGTH <= len(security_question) <= SECURITY_QUESTION_MAX_LENGTH:
            error = "Security question must be between 1 and 25 characters."
        elif not SECURITY_ANSWER_MIN_LENGTH <= len(security_answer) <= SECURITY_ANSWER_MAX_LENGTH:
            error = "Security answer must be between 1 and 25 characters."
        elif password != confirm_password:
            error = "Passwords do not match."
        else:
            existing = User.query.filter_by(username=username).first()
            if existing:
                error = "Username already exists."
            else:
                user = User(
                    username=username,
                    password_hash=generate_password_hash(password),
                    security_question=security_question,
                    security_answer_hash=generate_password_hash(security_answer),
                    default_location=default_location
                )
                db.session.add(user)
                db.session.commit()
                return redirect(url_for("login"))

    return render_template(
        "register.html",
        error=error,
        locations=locations
    )

@app.route("/post/new", methods=["GET", "POST"])
@login_required
def create_post():
    locations = load_location_choices()
    error = None
    expires_in_days = 7

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        body = request.form.get("body", "").strip()
        try:
            expires_in_days = int(request.form.get("expires_in_days", "7"))
        except (TypeError, ValueError):
            expires_in_days = 0
        category = request.form.get("category", "")
        location = request.form.get("location", current_user.default_location)
        visibility = request.form.get("visibility", "public")
        comments_enabled = request.form.get("comments_enabled") == "1"

        if location not in locations:
            location = current_user.default_location

        if contains_blocked_word(title) or contains_blocked_word(body):
            return render_template(
                "post_form.html",
                post={
                    "title": "",
                    "body": "",
                    "category": category,
                    "location": current_user.default_location,
                    "expires_in_days": expires_in_days,
                },
                locations=locations,
                current_user=current_user,
                expiry_choices=POST_EXPIRY_CHOICES,
                selected_expiry_days=expires_in_days,
                is_edit=False,
                error="Post contains blocked words. Please remove the disallowed text and try again."
            )

        if not title or not body:
            error = "Title and body are required."
        elif not POST_TITLE_MIN_LENGTH <= len(title) <= POST_TITLE_MAX_LENGTH:
            error = "Post title must be between 6 and 50 characters."
        elif not POST_BODY_MIN_LENGTH <= len(body) <= POST_BODY_MAX_LENGTH:
            error = "Post description must be between 1 and 1000 characters."
        elif expires_in_days not in POST_EXPIRY_CHOICES:
            error = "Expiry must be 7, 14, or 30 days."
        else:
            post = Post(
                title=title,
                body=body,
                category=category,
                location=location,
                visibility=visibility,
                comments_enabled=comments_enabled,
                expires_in_days=expires_in_days,
                author_id=current_user.id
            )
            db.session.add(post)
            db.session.commit()
            return redirect(url_for("home"))

    return render_template(
        "post_form.html",
        post=None,
        locations=locations,
        current_user=current_user,
        expiry_choices=POST_EXPIRY_CHOICES,
        selected_expiry_days=expires_in_days,
        is_edit=False,
        error=error
    )

@app.route("/post/<int:post_id>/edit", methods=["GET", "POST"])
@login_required
def edit_post(post_id):
    post = Post.query.get_or_404(post_id)
    locations = load_location_choices()
    error = None

    if post.author_id != current_user.id:
        abort(403)

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        body = request.form.get("body", "").strip()
        category = request.form.get("category", "")
        location = request.form.get("location", post.location)
        visibility = request.form.get("visibility", post.visibility)
        comments_enabled = request.form.get("comments_enabled") == "1"

        if location not in locations:
            location = current_user.default_location

        if contains_blocked_word(title) or contains_blocked_word(body):
            return render_template(
                "post_form.html",
                post={
                    "title": "",
                    "body": "",
                    "category": category,
                    "location": current_user.default_location,
                    "expires_in_days": post.expires_in_days,
                },
                locations=locations,
                current_user=current_user,
                is_edit=True,
                error="Post contains blocked words. Please remove the disallowed text and try again."
            )

        post.title = title
        post.body = body
        post.category = category
        post.location = location
        post.visibility = visibility
        post.comments_enabled = comments_enabled

        if not title or not body:
            error = "Title and body are required."
        elif not POST_TITLE_MIN_LENGTH <= len(title) <= POST_TITLE_MAX_LENGTH:
            error = "Post title must be between 6 and 50 characters."
        elif not POST_BODY_MIN_LENGTH <= len(body) <= POST_BODY_MAX_LENGTH:
            error = "Post description must be between 1 and 1000 characters."
        else:
            db.session.commit()
            return redirect(url_for("home"))

    return render_template(
        "post_form.html",
        post=post,
        locations=locations,
        current_user=current_user,
        is_edit=True,
        expiry_choices=POST_EXPIRY_CHOICES,
        error=error
    )


@app.route(
    "/post/<int:post_id>/pick",
    methods=["POST"]
)
@login_required
def toggle_pick(post_id):

    post = Post.query.get_or_404(post_id)

    existing_pick = PostPick.query.filter_by(
        user_id=current_user.id,
        post_id=post.id
    ).first()

    if existing_pick:

        db.session.delete(existing_pick)
        db.session.commit()

    else:

        new_pick = PostPick(
            user_id=current_user.id,
            post_id=post.id
        )

        db.session.add(new_pick)
        db.session.commit()

    return redirect(
        request.referrer
        or url_for("home")
    )

@app.route("/post/<int:post_id>/delete", methods=["POST"])
@login_required
def delete_post(post_id):

    post = Post.query.get_or_404(post_id)

    # Only the owner can delete the post
    if post.author_id != current_user.id:
        abort(403)

    db.session.delete(post)
    db.session.commit()

    return redirect(url_for("home"))

@app.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))



@app.route("/account", methods=["GET", "POST"])
@login_required
def account():
    error = None
    success = None
    success_type = None
    locations = load_location_choices()

    if request.method == "POST":
        form_type = request.form.get("form_type")

        if form_type == "password":
            current_password = request.form.get("current_password", "")
            new_password = request.form.get("new_password", "")
            confirm_password = request.form.get("confirm_password", "")

            if not check_password_hash(current_user.password_hash, current_password):
                error = "Current password is incorrect."
            elif not PASSWORD_MIN_LENGTH <= len(new_password) <= PASSWORD_MAX_LENGTH:
                error = "New password must be between 8 and 25 characters."
            elif new_password != confirm_password:
                error = "Passwords do not match."
            else:
                current_user.password_hash = generate_password_hash(new_password)
                db.session.commit()
                success = "Password changed successfully."
                success_type = "password"

        elif form_type == "security":
            security_question = request.form.get("security_question", "")
            security_answer = request.form.get("security_answer", "").strip().lower()

            if not SECURITY_QUESTION_MIN_LENGTH <= len(security_question) <= SECURITY_QUESTION_MAX_LENGTH:
                error = "Security question must be between 1 and 25 characters."
            elif not SECURITY_ANSWER_MIN_LENGTH <= len(security_answer) <= SECURITY_ANSWER_MAX_LENGTH:
                error = "Security answer must be between 1 and 25 characters."
            else:
                current_user.security_question = security_question
                current_user.security_answer_hash = generate_password_hash(security_answer)
                db.session.commit()
                success = "Security details saved successfully."
                success_type = "security"

        else:
            chosen = request.form.get("default_location", current_user.default_location)

            if chosen in locations:
                current_user.default_location = chosen
                db.session.commit()
                flash("Default location saved successfully.", "account_location_success")
                return redirect(url_for("account"))
            else:
                error = "Invalid location."

    for category, message in get_flashed_messages(with_categories=True):
        if category == "account_location_success":
            success = message
            success_type = "location"

    return render_template(
        "account.html",
        error=error,
        success=success,
        success_type=success_type,
        locations=locations,
        current_user=current_user
    )

@app.route("/account/delete", methods=["POST"])
@login_required
def delete_account():
    user = current_user._get_current_object()
    user_id = user.id

    for post in Post.query.filter_by(author_id=user_id).all():
        db.session.delete(post)

    db.session.flush()

    for comment in Comment.query.filter_by(author_id=user_id).all():
        db.session.delete(comment)

    for pick in PostPick.query.filter_by(user_id=user_id).all():
        db.session.delete(pick)

    db.session.delete(user)
    db.session.commit()
    logout_user()

    return redirect(url_for("home"))


@app.route(
    "/post/<int:post_id>/comment",
    methods=["POST"]
)
@login_required
def add_comment(post_id):

    post = Post.query.get_or_404(post_id)

    if not post.comments_enabled:
        abort(403)

    body = request.form.get(
        "body",
        ""
    ).strip()

    if not body:
        return redirect(url_for("home"))

    if not COMMENT_MIN_LENGTH <= len(body) <= COMMENT_MAX_LENGTH:
        return redirect(request.referrer or url_for("home"))

    if contains_blocked_word(body):
        return redirect(url_for("home"))

    comment = Comment(
        body=body,
        author_id=current_user.id,
        post_id=post.id,
        location=current_user.default_location
    )

    db.session.add(comment)
    db.session.commit()

    return redirect(
        request.referrer
        or url_for("home")
    )


@app.route(
    "/comment/<int:comment_id>/delete",
    methods=["POST"]
)
@login_required
def delete_comment(comment_id):

    comment = Comment.query.get_or_404(
        comment_id
    )

    if comment.author_id != current_user.id:
        abort(403)

    db.session.delete(comment)
    db.session.commit()

    return redirect(
        request.referrer
        or url_for("home")
    )

@app.route(
    "/comment/<int:comment_id>/edit",
    methods=["GET", "POST"]
)
@login_required
def edit_comment(comment_id):

    comment = Comment.query.get_or_404(
        comment_id
    )

    if comment.author_id != current_user.id:
        abort(403)

    error = None

    if request.method == "POST":

        body = request.form.get(
            "body",
            ""
        ).strip()

        if not body:
            error = "Comment cannot be empty."

        elif not COMMENT_MIN_LENGTH <= len(body) <= COMMENT_MAX_LENGTH:
            error = "Comment must be between 1 and 300 characters."

        elif contains_blocked_word(body):
            error = (
                "The comment contains a word "
                "that is not allowed."
            )

        else:

            comment.body = body

            db.session.commit()

            return redirect(
                url_for("home")
            )

    return render_template(
        "edit_comment.html",
        comment=comment,
        error=error
    )

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True)

