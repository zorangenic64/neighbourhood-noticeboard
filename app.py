from flask import Flask, render_template, request, redirect, url_for, abort, jsonify, session 

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


from datetime import datetime

from zxcvbn import zxcvbn

from utils.text_filter import contains_blocked_word

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


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route("/")
def home():

    category = request.args.get("category")
    picked = request.args.get("picked")

    if current_user.is_authenticated:
        query = Post.query
    else:
        query = Post.query.filter_by(
            visibility="public"
        )

    if category:
        query = query.filter_by(
            category=category
        )

    if picked and current_user.is_authenticated:

        query = query.join(
            PostPick,
            Post.id == PostPick.post_id
        ).filter(
            PostPick.user_id == current_user.id
        )


    posts = query.order_by(
        Post.created_at.desc()
    ).all()

    picked_post_ids = set()

    if current_user.is_authenticated:

        picked_post_ids = {
            pick.post_id
            for pick in PostPick.query.filter_by(
                user_id=current_user.id
            ).all()
        }

    return render_template(
        "index.html",
        posts=posts,
        selected_category=category,
        picked_post_ids=picked_post_ids,
        picked_filter=picked
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

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        if not username:

            error = "Please enter your username."

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

        elif new_password != confirm_password:

            error = "Passwords do not match."

        else:

            has_minimum_length = (
                len(new_password) >= 8
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
                    "8 characters long."
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

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        confirm_password = request.form.get(
            "confirm_password",
            ""
        )

        security_question = request.form.get(
            "security_question",
            ""
        ).strip()

        security_answer = request.form.get(
            "security_answer",
            ""
        ).strip()

        # Check username

        if not username:
            error = "Username cannot be empty."

        elif contains_blocked_word(username):
            error = "That username is not allowed."

        elif User.query.filter_by(
            username=username
        ).first():
            error = "That username is already taken."

        # Check password

        elif not password:
            error = "Password cannot be empty."

        elif password != confirm_password:
            error = "Passwords do not match."

        # Check password requirements

        else:

            has_minimum_length = len(password) >= 8

            has_uppercase = any(
                character.isupper()
                for character in password
            )

            has_digit = any(
                character.isdigit()
                for character in password
            )

            has_symbol = any(
                not character.isalnum()
                for character in password
            )

            strength_result = zxcvbn(password)
            password_score = strength_result["score"]

            if not has_minimum_length:
                error = (
                    "Password must be at least "
                    "8 characters long."
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

            # Check security details

            elif not security_question:
                error = (
                    "Security question cannot be empty."
                )

            elif not security_answer:
                error = (
                    "Security answer cannot be empty."
                )

            else:

                user = User(
                    username=username,
                    password_hash=generate_password_hash(
                        password
                    ),
                    security_question=security_question,
                    security_answer_hash=generate_password_hash(
                        security_answer.lower()
                    ),
                    created_at=datetime.utcnow()
                )

                db.session.add(user)
                db.session.commit()

                return redirect(url_for("login"))

    return render_template(
        "register.html",
        error=error
    )

@app.route("/post/new", methods=["GET", "POST"])
@login_required
def create_post():

    error = None

    if request.method == "POST":

        title = request.form.get(
            "title",
            ""
        ).strip()

        body = request.form.get(
            "body",
            ""
        ).strip()

        category = request.form.get(
            "category",
            ""
        )

        visibility = request.form.get(
            "visibility",
            ""
        )

        comments_enabled = (
            request.form.get("comments_enabled") == "on"
        )

        if not title:

            error = "Title cannot be empty."

        elif contains_blocked_word(title):

            error = "The post title contains a word that is not allowed."

        elif not body:

            error = "Description cannot be empty."

        elif contains_blocked_word(body):

            error = (
                "The post description contains a word "
                "that is not allowed."
            )

        else:

            post = Post(
                title=title,
                body=body,
                category=category,
                visibility=visibility,
                comments_enabled=comments_enabled,
                author_id=current_user.id
            )

            db.session.add(post)
            db.session.commit()

            return redirect(url_for("home"))

    return render_template(
        "create_post.html",
        error=error
    )

@app.route("/post/<int:post_id>/edit", methods=["GET", "POST"])
@login_required
def edit_post(post_id):

    post = Post.query.get_or_404(post_id)

    if post.author_id != current_user.id:
        abort(403)

    error = None

    if request.method == "POST":

        title = request.form.get(
            "title",
            ""
        ).strip()

        body = request.form.get(
            "body",
            ""
        ).strip()

        category = request.form.get(
            "category",
            ""
        )

        visibility = request.form.get(
            "visibility",
            ""
        )

        comments_enabled = (
            request.form.get("comments_enabled") == "on"
        )

        if not title:

            error = "Title cannot be empty."

        elif contains_blocked_word(title):

            error = (
                "The post title contains a word "
                "that is not allowed."
            )

        elif not body:

            error = "Description cannot be empty."

        elif contains_blocked_word(body):

            error = (
                "The post description contains a word "
                "that is not allowed."
            )

        else:

            post.title = title
            post.body = body
            post.category = category
            post.visibility = visibility
            post.comments_enabled = comments_enabled

            db.session.commit()

            return redirect(url_for("home"))

    return render_template(
        "edit_post.html",
        post=post,
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

@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("home"))



@app.route("/account", methods=["GET", "POST"])
@login_required
def account():

    error = None
    success = None
    password_strength = None
    password_score = None

    if request.method == "POST":

        form_type = request.form.get("form_type")

        # -------------------------------------------------
        # SECURITY QUESTION / ANSWER
        # -------------------------------------------------

        if form_type == "security":

            security_question = request.form.get(
                "security_question",
                ""
            ).strip()

            security_answer = request.form.get(
                "security_answer",
                ""
            ).strip()

            if not security_question:

                error = (
                    "Security question cannot be empty."
                )

            elif not security_answer:

                error = (
                    "Security answer cannot be empty."
                )

            else:

                current_user.security_question = (
                    security_question
                )

                current_user.security_answer_hash = (
                    generate_password_hash(
                        security_answer.lower()
                    )
                )

                db.session.commit()

                success = (
                    "Security question and answer "
                    "updated successfully."
                )

        # -------------------------------------------------
        # PASSWORD
        # -------------------------------------------------

        elif form_type == "password":

            current_password = request.form.get(
                "current_password",
                ""
            )

            new_password = request.form.get(
                "new_password",
                ""
            )

            confirm_password = request.form.get(
                "confirm_password",
                ""
            )

            if not check_password_hash(
                current_user.password_hash,
                current_password
            ):

                error = (
                    "Current password is incorrect."
                )

            elif new_password != confirm_password:

                error = (
                    "New passwords do not match."
                )

            else:

                has_minimum_length = (
                    len(new_password) >= 8
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
                        "8 characters long."
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

                    current_user.password_hash = (
                        generate_password_hash(
                            new_password
                        )
                    )

                    db.session.commit()

                    success = (
                        "Password changed successfully."
                    )

        else:

            error = "Invalid account form."

    return render_template(
        "account.html",
        error=error,
        success=success,
        password_strength=password_strength,
        password_score=password_score
    )


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

    if contains_blocked_word(body):
        return redirect(url_for("home"))

    comment = Comment(
        body=body,
        author_id=current_user.id,
        post_id=post.id
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

    