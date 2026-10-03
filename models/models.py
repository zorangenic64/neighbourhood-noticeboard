from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_login import UserMixin

db = SQLAlchemy()


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(
        db.String(80),
        unique=True,
        nullable=False
    )

    password_hash = db.Column(
        db.String(255),
        nullable=False
    )

    default_location = db.Column(
        db.String(120),
        nullable=False,
        default="Unknown"
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    last_login = db.Column(
        db.DateTime,
        nullable=True
    )

    last_successful_login_datetime = db.Column(
        db.DateTime,
        nullable=True
    )

    login_fail_count = db.Column(
        db.Integer,
        nullable=False,
        default=0
    )

    login_last_attempt_status = db.Column(
        db.String(20),
        nullable=False,
        default="SUCCESS"
    )

    login_last_failed_datetime = db.Column(
        db.DateTime,
        nullable=True
    )

    login_retry_after_datetime = db.Column(
        db.DateTime,
        nullable=True
    )

    security_fail_count = db.Column(
        db.Integer,
        nullable=False,
        default=0
    )

    security_last_attempt_status = db.Column(
        db.String(20),
        nullable=False,
        default="SUCCESS"
    )

    security_last_failed_datetime = db.Column(
        db.DateTime,
        nullable=True
    )

    security_retry_after_datetime = db.Column(
        db.DateTime,
        nullable=True
    )

    status = db.Column(
        db.String(20),
        nullable=False,
        default="active"
    )

    is_admin = db.Column(
        db.Boolean,
        nullable=False,
        default=False
    )

    security_question = db.Column(
        db.String(255),
        nullable=False
    )

    security_answer_hash = db.Column(
        db.String(255),
        nullable=False
    )

    posts = db.relationship(
        "Post",
        backref="author",
        lazy=True
    )

    picked_posts = db.relationship(
        "PostPick",
        backref="user",
        lazy=True,
        cascade="all, delete-orphan"
    )

    comments = db.relationship(
        "Comment",
        backref="author",
        lazy=True,
        cascade="all, delete-orphan"
    )


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    title = db.Column(
        db.String(200),
        nullable=False
    )

    body = db.Column(
        db.Text,
        nullable=False
    )

    category = db.Column(
        db.String(50),
        nullable=False
    )

    location = db.Column(
        db.String(120),
        nullable=False,
        default="Unknown"
    )

    visibility = db.Column(
        db.String(20),
        nullable=False,
        default="public"
    )

    comments_enabled = db.Column(
        db.Boolean,
        nullable=False,
        default=False
    )

    expires_in_days = db.Column(
        db.Integer,
        nullable=False,
        default=7,
        server_default="7"
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    author_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    picks = db.relationship(
        "PostPick",
        backref="post",
        lazy=True,
        cascade="all, delete-orphan"
    )

    comments = db.relationship(
        "Comment",
        backref="post",
        lazy=True,
        cascade="all, delete-orphan"
    )


class PostPick(db.Model):
    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    post_id = db.Column(
        db.Integer,
        db.ForeignKey("post.id"),
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    __table_args__ = (
        db.UniqueConstraint(
            "user_id",
            "post_id",
            name="unique_user_post_pick"
        ),
    )


class Comment(db.Model):
    id = db.Column(
        db.Integer,
        primary_key=True
    )

    body = db.Column(
        db.Text,
        nullable=False
    )

    location = db.Column(
        db.String(120),
        nullable=False,
        default="Unknown"
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    author_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    post_id = db.Column(
        db.Integer,
        db.ForeignKey("post.id"),
        nullable=False
    )


class AuditLog(db.Model):
    __bind_key__ = "logs"

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    event_name = db.Column(db.String(40), nullable=False)
    outcome = db.Column(db.String(20), nullable=False)
    user_id = db.Column(db.Integer)
    post_id = db.Column(db.Integer)
    comment_id = db.Column(db.Integer)
    notes = db.Column(db.Text)
    generation = db.Column(db.Integer, nullable=False)


class AuditLogRotationState(db.Model):
    __bind_key__ = "logs"

    id = db.Column(db.Integer, primary_key=True)
    current_generation = db.Column(db.Integer, nullable=False, default=1)
    rows_in_generation = db.Column(db.Integer, nullable=False, default=0)