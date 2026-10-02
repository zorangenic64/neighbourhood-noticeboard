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
import config

print("Starting Flask app...")
app = Flask(__name__)

# Allow the split route modules to do `from app import app` while the app is
# running as a script, so they register against the same Flask instance.
import sys
sys.modules.setdefault("app", sys.modules[__name__])

from routes import account, auth, comments, posts


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
                ("status", "VARCHAR(20) NOT NULL DEFAULT 'active'"),
                ("is_admin", "BOOLEAN NOT NULL DEFAULT 0")
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


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))



@app.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)


