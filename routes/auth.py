from flask import Flask, render_template, request, redirect, url_for, abort, jsonify, session, flash, get_flashed_messages

from app import app

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

from utils.validation import (
    validate_username,
    validate_password,
    validate_security_question,
    validate_security_answer,
)

import config

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

    username_error = validate_username(username)
    if username_error:
        return jsonify({
            "valid": False,
            "message": username_error
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

        else:
            error = validate_username(username)

            if not error:
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

        else:
            security_answer_error = validate_security_answer(security_answer)
            if security_answer_error:
                error = security_answer_error
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

        elif len(new_password) > config.PASSWORD_MAX_LENGTH:

            error = "Password must be no more than 25 characters long."

        elif new_password != confirm_password:

            error = "Passwords do not match."

        else:

            has_minimum_length = (
                len(new_password) >= config.RESET_PASSWORD_MIN_LENGTH
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
                    f"{config.RESET_PASSWORD_MIN_LENGTH} characters long."
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

        error = validate_username(username)
        if not error:
            error = validate_password(password)
        if not error:
            error = validate_security_question(security_question)
        if not error:
            error = validate_security_answer(security_answer)
        if not error and password != confirm_password:
            error = "Passwords do not match."

        if not error:
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
