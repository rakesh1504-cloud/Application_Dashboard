from urllib.parse import urlsplit

import sqlalchemy as sa
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from .audit import log_event
from .db import db
from .forms import LoginForm, RegisterForm
from .models import User

bp = Blueprint("auth", __name__, url_prefix="/auth")


def _safe_next(target):
    # Only allow relative redirects to stay on this site.
    if target and not urlsplit(target).netloc and target.startswith("/"):
        return target
    return url_for("cases.dashboard")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("cases.dashboard"))
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data.strip()
        user = User.get_by_username(username)
        if user and user.check_password(form.password.data):
            login_user(user)
            log_event("auth.login", user=user)
            db.session.commit()
            flash(f"Welcome back, {user.full_name}!", "success")
            return redirect(_safe_next(request.args.get("next")))
        log_event("auth.login_failed", details={"username": username[:40]})
        db.session.commit()
        flash("Invalid username or password.", "error")
    return render_template("auth/login.html", form=form)


@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("cases.dashboard"))
    form = RegisterForm()
    if form.validate_on_submit():
        username = form.username.data.strip()
        email = form.email.data.strip().lower()
        if db.session.scalar(sa.select(User.id).filter_by(username=username)):
            form.username.errors.append("That username is taken.")
        elif db.session.scalar(sa.select(User.id).filter_by(email=email)):
            form.email.errors.append("That email is already registered.")
        else:
            user = User.create(username, form.full_name.data.strip(), email, form.password.data)
            db.session.flush()
            log_event("auth.register", user=user, details={"role": user.role})
            db.session.commit()
            login_user(user)
            flash("Account created. Welcome to CMS!", "success")
            return redirect(url_for("cases.dashboard"))
    return render_template("auth/register.html", form=form)


@bp.route("/logout", methods=["POST"])
@login_required
def logout():
    log_event("auth.logout")
    db.session.commit()
    logout_user()
    flash("You have been signed out.", "info")
    return redirect(url_for("auth.login"))
