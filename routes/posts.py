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
    validate_post_title,
    validate_post_body,
    validate_expiry_days,
)

from flask_wtf.csrf import CSRFProtect

from werkzeug.security import (
    check_password_hash,
    generate_password_hash
)

from models.models import db, Post, User, PostPick, Comment


from datetime import datetime, timedelta

from zxcvbn import zxcvbn

from utils.posts_filter import contains_blocked_word
from utils.audit_log import write_audit_log

from utils.location_data import load_location_choices

from utils.proximity import post_is_within_distance

from sqlalchemy import and_, inspect, or_, text
from threading import Lock

import config

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
                expiry_choices=config.POST_EXPIRY_CHOICES,
                selected_expiry_days=expires_in_days,
                is_edit=False,
                error="Post contains blocked words. Please remove the disallowed text and try again."
            )

        if not title or not body:
            error = "Title and body are required."
        else:
            error = validate_post_title(title)
            if not error:
                error = validate_post_body(body)
            if not error:
                error = validate_expiry_days(expires_in_days)
        if not error:
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
            write_audit_log(
                "POST_ADD",
                "SUCCESS",
                user_id=current_user.id,
                post_id=post.id,
            )
            return redirect(url_for("home"))

    return render_template(
        "post_form.html",
        post=None,
        locations=locations,
        current_user=current_user,
        expiry_choices=config.POST_EXPIRY_CHOICES,
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
        else:
            error = validate_post_title(title)
            if not error:
                error = validate_post_body(body)
        if not error:
            db.session.commit()
            write_audit_log(
                "POST_EDIT",
                "SUCCESS",
                user_id=current_user.id,
                post_id=post.id,
            )
            return redirect(url_for("home"))

    return render_template(
        "post_form.html",
        post=post,
        locations=locations,
        current_user=current_user,
        is_edit=True,
        expiry_choices=config.POST_EXPIRY_CHOICES,
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

    deleted_post_id = post.id
    db.session.delete(post)
    db.session.commit()
    write_audit_log(
        "POST_DELETE",
        "SUCCESS",
        user_id=current_user.id,
        post_id=deleted_post_id,
    )

    return redirect(url_for("home"))
