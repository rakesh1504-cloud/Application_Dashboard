"""Case Management System (CMS) - a small Flask web portal."""
import os

from flask import Flask, redirect, url_for
from flask_login import LoginManager, current_user
from flask_wtf import CSRFProtect

from . import db
from .models import User

login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message_category = "info"
csrf = CSRFProtect()


@login_manager.user_loader
def load_user(user_id):
    return User.get(int(user_id))


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("CMS_SECRET_KEY", "dev-change-me"),
        DATABASE=os.path.join(app.instance_path, "cms.sqlite"),
    )
    if test_config is not None:
        app.config.update(test_config)

    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    from . import auth, cases

    app.register_blueprint(auth.bp)
    app.register_blueprint(cases.bp)

    @app.route("/")
    def index():
        if current_user.is_authenticated:
            return redirect(url_for("cases.dashboard"))
        return redirect(url_for("auth.login"))

    @app.context_processor
    def inject_globals():
        return {"portal_name": "Case Management System"}

    return app
