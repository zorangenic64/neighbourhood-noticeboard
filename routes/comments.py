from flask import Flask, render_template, request, redirect, url_for, abort, jsonify, session, flash, get_flashed_messages

from app import app

from flask_login import (
    LoginManager,
    login_user,
    logout_user,
    current_user,
    login_required
)

from utils.validation import validate_comment

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

    if validate_comment(body):
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

        else:
            error = validate_comment(body)
            if not error and contains_blocked_word(body):
                error = (
                    "The comment contains a word "
                    "that is not allowed."
                )

        if not error:
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

