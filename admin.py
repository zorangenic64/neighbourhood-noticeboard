from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.security import generate_password_hash

from models.models import (
    db,
    User,
    Post,
    Comment,
    PostPick,
    AuditLog,
    AuditLogRotationState,
)


admin_app = Flask(__name__)
admin_app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///noticeboard.db"
admin_app.config["SQLALCHEMY_BINDS"] = {
    "logs": "sqlite:///nnb_logs.db",
}
admin_app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
admin_app.config["SECRET_KEY"] = "8c10d156b76463f19d63d50d542b558404cb744a2f15f14a72f0bdeb38e553ce"

db.init_app(admin_app)


with admin_app.app_context():
    db.create_all()
    db.create_all(bind_key="logs")
    if not db.session.get(AuditLogRotationState, 1):
        db.session.add(AuditLogRotationState(id=1))
        db.session.commit()


def user_summary(user):
    return {
        "id": user.id,
        "username": user.username,
        "default_location": user.default_location,
        "created_at": user.created_at,
        "last_login": user.last_login,
        "last_successful_login_datetime": user.last_successful_login_datetime,
        "login_fail_count": user.login_fail_count,
        "login_last_attempt_status": user.login_last_attempt_status,
        "login_last_failed_datetime": user.login_last_failed_datetime,
        "login_retry_after_datetime": user.login_retry_after_datetime,
        "security_fail_count": user.security_fail_count,
        "security_last_attempt_status": user.security_last_attempt_status,
        "security_last_failed_datetime": user.security_last_failed_datetime,
        "security_retry_after_datetime": user.security_retry_after_datetime,
        "status": user.status,
        "is_admin": user.is_admin,
        "posts_count": Post.query.filter_by(author_id=user.id).count(),
        "comments_count": Comment.query.filter_by(author_id=user.id).count(),
    }


@admin_app.route("/")
def index():
    return redirect(url_for("users"))


@admin_app.route("/users")
def users():
    user_id = request.args.get("user_id", type=int)
    user_query = User.query.order_by(User.id)
    if user_id is not None:
        user_query = user_query.filter_by(id=user_id)
    user_rows = [user_summary(user) for user in user_query.all()]
    return render_template("admin_users.html", users=user_rows)


@admin_app.route("/posts")
def posts_browser():
    user_id = request.args.get("user_id", type=int)
    post_id = request.args.get("post_id", type=int)
    post_query = Post.query.order_by(Post.created_at.desc(), Post.id.desc())

    if user_id is not None:
        post_query = post_query.filter_by(author_id=user_id)
    if post_id is not None:
        post_query = post_query.filter_by(id=post_id)

    filter_user = db.session.get(User, user_id) if user_id is not None else None
    return render_template(
        "admin_posts.html",
        posts=post_query.all(),
        filter_user=filter_user,
        filter_post_id=post_id,
    )


@admin_app.route("/comments")
def comments_browser():
    user_id = request.args.get("user_id", type=int)
    post_id = request.args.get("post_id", type=int)
    comment_query = Comment.query.order_by(Comment.created_at.desc(), Comment.id.desc())

    if user_id is not None:
        comment_query = comment_query.filter_by(author_id=user_id)
    if post_id is not None:
        comment_query = comment_query.filter_by(post_id=post_id)

    filter_user = db.session.get(User, user_id) if user_id is not None else None
    return render_template(
        "admin_comments.html",
        comments=comment_query.all(),
        filter_user=filter_user,
        filter_post_id=post_id,
    )


@admin_app.route("/logs")
def logs_browser():
    logs = AuditLog.query.order_by(
        AuditLog.created_at.desc(),
        AuditLog.id.desc(),
    ).all()
    return render_template("admin_logs.html", logs=logs)


@admin_app.route("/posts/<int:post_id>/delete", methods=["GET", "POST"])
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)

    if request.method == "POST":
        Comment.query.filter_by(post_id=post.id).delete(synchronize_session=False)
        PostPick.query.filter_by(post_id=post.id).delete(synchronize_session=False)
        db.session.delete(post)
        db.session.commit()
        flash("Post and its comments deleted successfully.", "success")
        return redirect(url_for("posts_browser"))

    return render_template(
        "admin_confirm_delete.html",
        title="Delete Post",
        record_name=post.title,
        message="This will also permanently delete all comments on this post.",
        cancel_url=url_for("posts_browser"),
    )


@admin_app.route("/comments/<int:comment_id>/delete", methods=["GET", "POST"])
def delete_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)

    if request.method == "POST":
        db.session.delete(comment)
        db.session.commit()
        flash("Comment deleted successfully.", "success")
        return redirect(url_for("comments_browser"))

    return render_template(
        "admin_confirm_delete.html",
        title="Delete Comment",
        record_name=f"Comment #{comment.id}",
        message="This comment will be permanently deleted.",
        cancel_url=url_for("comments_browser"),
    )


@admin_app.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
def edit_user(user_id):
    user = User.query.get_or_404(user_id)

    if request.method == "POST":
        new_password = request.form.get("new_password", "").strip()
        new_status = request.form.get("status", "active")
        is_admin = request.form.get("is_admin") == "1"

        if new_status not in {"active", "suspended"}:
            new_status = "active"

        user.status = new_status
        user.is_admin = is_admin

        if new_password:
            user.password_hash = generate_password_hash(new_password)

        db.session.commit()
        flash("User updated successfully.", "success")
        return redirect(url_for("users"))

    return render_template("admin_edit_user.html", user=user_summary(user))


@admin_app.route("/users/<int:user_id>/delete", methods=["GET", "POST"]) 
def delete_user(user_id):
    user = User.query.get_or_404(user_id)

    if request.method == "POST":
        user_posts = Post.query.filter_by(author_id=user.id).all()
        for post in user_posts:
            PostPick.query.filter_by(post_id=post.id).delete()
            Comment.query.filter_by(post_id=post.id).delete()
            db.session.delete(post)

        PostPick.query.filter_by(user_id=user.id).delete()
        Comment.query.filter_by(author_id=user.id).delete()
        db.session.delete(user)
        db.session.commit()
        flash("User deleted successfully.", "success")
        return redirect(url_for("users"))

    return render_template("admin_delete_user.html", user=user_summary(user))


if __name__ == "__main__":
    admin_app.run(host="0.0.0.0", port=5001, debug=True)
