from flask import Flask, render_template, request, redirect, url_for, abort, jsonify, session, flash, get_flashed_messages

from app import app

from flask_login import (
    LoginManager,
    login_user,
    logout_user,
    current_user,
    login_required
)

from utils.validation import (
    validate_password,
    validate_security_question,
    validate_security_answer,
)
from utils.audit_log import write_audit_log

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

import config


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
            else:
                error = validate_password(new_password)
                if not error and new_password != confirm_password:
                    error = "Passwords do not match."
                elif not error:
                    current_user.password_hash = generate_password_hash(new_password)
                    db.session.commit()
                    write_audit_log(
                        "ACCOUNT_PWD_CHANGE",
                        "SUCCESS",
                        user_id=current_user.id,
                    )
                    success = "Password changed successfully."
                    success_type = "password"

        elif form_type == "security":
            security_question = request.form.get("security_question", "")
            security_answer = request.form.get("security_answer", "").strip().lower()

            error = validate_security_question(security_question)
            if not error:
                error = validate_security_answer(security_answer)
            if not error:
                current_user.security_question = security_question
                current_user.security_answer_hash = generate_password_hash(security_answer)
                db.session.commit()
                write_audit_log(
                    "ACCOUNT_SECURITY_CHANGE",
                    "SUCCESS",
                    user_id=current_user.id,
                )
                success = "Security details saved successfully."
                success_type = "security"

        else:
            chosen = request.form.get("default_location", current_user.default_location)

            if chosen in locations:
                current_user.default_location = chosen
                db.session.commit()
                write_audit_log(
                    "ACCOUNT_LOCATION_CHANGE",
                    "SUCCESS",
                    user_id=current_user.id,
                    notes=f"location={chosen}",
                )
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
    posts_deleted = Post.query.filter_by(author_id=user_id).count()
    comments_deleted = Comment.query.filter_by(author_id=user_id).count()

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
    write_audit_log(
        "ACCOUNT_SELF_DELETE",
        "SUCCESS",
        user_id=user_id,
        notes=(
            f"posts_deleted={posts_deleted}; "
            f"comments_deleted={comments_deleted}"
        ),
    )

    return redirect(url_for("home"))

