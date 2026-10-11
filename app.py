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

from models.models import (
    db,
    Post,
    User,
    PostPick,
    Comment,
    AuditLogRotationState,
)


from datetime import datetime, timedelta
from pathlib import Path

from zxcvbn import zxcvbn

from utils.text_filter import contains_blocked_word
from utils.url_links import linkify_urls
from utils.audit_log import write_audit_log

from utils.location_data import load_location_choices

from utils.proximity import post_is_within_distance

from sqlalchemy import and_, inspect, or_, text
from threading import Lock
import config

print("Starting Flask app...")
app = Flask(__name__)
app.add_template_filter(linkify_urls, "linkify_urls")

# Allow the split route modules to do `from app import app` while the app is
# running as a script, so they register against the same Flask instance.
import sys
sys.modules.setdefault("app", sys.modules[__name__])

from routes import account, auth, comments, posts


app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///noticeboard.db"
app.config["SQLALCHEMY_BINDS"] = {
    "logs": "sqlite:///nnb_logs.db",
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Required for Flask sessions/login
app.config["SECRET_KEY"] = config.get_secret_key()


# Session cookie security
app.config["SESSION_COOKIE_SECURE"] = True
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"


csrf = CSRFProtect(app)

db.init_app(app)

with app.app_context():
    db.create_all(bind_key="logs")
    if not db.session.get(AuditLogRotationState, 1):
        db.session.add(AuditLogRotationState(id=1))
        db.session.commit()

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
        if inspector.has_table("user"):
            user_columns = {column["name"] for column in inspector.get_columns("user")}
            user_schema_updates = [
                ("last_successful_login_datetime", "DATETIME"),
                ("login_fail_count", "INTEGER NOT NULL DEFAULT 0"),
                ("login_last_attempt_status", "VARCHAR(20) NOT NULL DEFAULT 'SUCCESS'"),
                ("login_last_failed_datetime", "DATETIME"),
                ("login_retry_after_datetime", "DATETIME"),
                ("security_fail_count", "INTEGER NOT NULL DEFAULT 0"),
                ("security_last_attempt_status", "VARCHAR(20) NOT NULL DEFAULT 'SUCCESS'"),
                ("security_last_failed_datetime", "DATETIME"),
                ("security_retry_after_datetime", "DATETIME"),
                ("status", "VARCHAR(20) NOT NULL DEFAULT 'active'")
                
            ]
            with db.engine.begin() as connection:
                for column_name, column_sql in user_schema_updates:
                    if column_name not in user_columns:
                        connection.execute(text(
                            f"ALTER TABLE user ADD COLUMN {column_name} {column_sql}"
                        ))

        if inspector.has_table("post"):
            columns = {column["name"] for column in inspector.get_columns("post")}
            if "expires_in_days" not in columns:
                with db.engine.begin() as connection:
                    connection.execute(text(
                        "ALTER TABLE post ADD COLUMN expires_in_days "
                        "INTEGER NOT NULL DEFAULT 7"
                    ))

        _post_expiry_schema_checked = True



@app.after_request
def add_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = (
        "strict-origin-when-cross-origin"
    )
    response.headers["Permissions-Policy"] = (
        "camera=(), microphone=(), geolocation=()"
    )

    # Diagnostic CSP: reports violations without blocking page behaviour.
    response.headers["Content-Security-Policy-Report-Only"] = (
        "default-src 'self'; "
        "script-src 'self' https://cdnjs.cloudflare.com; "
        "style-src 'self'; "
        "img-src 'self' data: https:; "
        "font-src 'self' data: https:; "
        "connect-src 'self'; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "frame-ancestors 'self'; "
        "form-action 'self'"
    )

    # Additional browser security headers.
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
    response.headers["Cross-Origin-Embedder-Policy"] = "require-corp"

    # HTTPS is used by this application.
    response.headers["Strict-Transport-Security"] = (
        "max-age=31536000"
    )

    return response


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))



@app.route("/logout", methods=["POST"])
@login_required
def logout():
    user_id = current_user.id
    logout_user()
    write_audit_log("LOGOUT", "SUCCESS", user_id=user_id)
    return redirect(url_for("login"))


if __name__ == "__main__":
    certificate_dir = Path(__file__).resolve().parent
    ssl_certificate = certificate_dir / "cert.pem"
    ssl_private_key = certificate_dir / "key.pem"
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True,
        ssl_context=(str(ssl_certificate), str(ssl_private_key)),
    )
