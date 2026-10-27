import sqlalchemy as sa
from flask import Blueprint, abort, render_template, request
from flask_login import current_user, login_required

from .db import db
from .models import AuditLog

bp = Blueprint("audit", __name__)

PAGE_SIZE = 50


def log_event(action, case_id=None, details=None, user=None):
    """Queue an audit row in the current session.

    The caller commits, so the audit row and the change it describes are
    saved in the same transaction: either both are recorded or neither is.
    """
    if user is None and current_user.is_authenticated:
        user = current_user
    db.session.add(
        AuditLog(
            user_id=user.id if user else None,
            username=user.username if user else None,
            action=action,
            case_id=case_id,
            details=details or None,
            ip_address=request.remote_addr,
            user_agent=(request.user_agent.string or "")[:255],
            method=request.method,
            path=request.full_path.rstrip("?")[:255],
        )
    )


@bp.route("/audit")
@login_required
def audit_log():
    if not current_user.is_admin:
        abort(403)
    action = request.args.get("action", "")
    username = request.args.get("user", "").strip()
    case_id = request.args.get("case_id", type=int)
    page = request.args.get("page", 1, type=int)

    query = sa.select(AuditLog).order_by(AuditLog.id.desc())
    if action:
        query = query.filter(AuditLog.action == action)
    if username:
        query = query.filter(AuditLog.username == username)
    if case_id:
        query = query.filter(AuditLog.case_id == case_id)
    entries = db.paginate(query, page=page, per_page=PAGE_SIZE, error_out=False)

    actions = db.session.scalars(
        sa.select(AuditLog.action).distinct().order_by(AuditLog.action)
    ).all()
    return render_template(
        "audit/list.html",
        entries=entries,
        actions=actions,
        filters={"action": action, "user": username, "case_id": case_id or ""},
    )
