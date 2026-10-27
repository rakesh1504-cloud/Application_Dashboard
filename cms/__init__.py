"""Case Management System (CMS) - a small Flask web portal."""
import os

from flask import Flask, redirect, url_for
from flask_login import LoginManager, current_user
from flask_wtf import CSRFProtect

from .db import database_url, db, migrate

login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message_category = "info"
csrf = CSRFProtect()


@login_manager.user_loader
def load_user(user_id):
    from .models import User

    return db.session.get(User, int(user_id))


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    os.makedirs(app.instance_path, exist_ok=True)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("CMS_SECRET_KEY", "dev-change-me"),
        SQLALCHEMY_DATABASE_URI=database_url(app.instance_path, os.environ),
        # Drop dead pooled connections (e.g. after a DB restart or failover).
        SQLALCHEMY_ENGINE_OPTIONS={"pool_pre_ping": True},
    )
    if test_config is not None:
        app.config.update(test_config)

    if os.environ.get("CMS_TRUST_PROXY") == "1":
        # Behind a load balancer / reverse proxy: take the client IP recorded
        # in the audit log from X-Forwarded-For instead of the proxy's address.
        from werkzeug.middleware.proxy_fix import ProxyFix

        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    from . import audit, auth, cases

    app.register_blueprint(auth.bp)
    app.register_blueprint(cases.bp)
    app.register_blueprint(audit.bp)

    @app.route("/")
    def index():
        if current_user.is_authenticated:
            return redirect(url_for("cases.dashboard"))
        return redirect(url_for("auth.login"))

    @app.context_processor
    def inject_globals():
        return {"portal_name": "Case Management System"}

    return app
