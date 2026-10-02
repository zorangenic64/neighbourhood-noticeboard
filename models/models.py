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