import sqlalchemy as sa
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy.orm import joinedload

from .audit import log_event
from .db import db
from .forms import CaseForm, NoteForm
from .models import PRIORITIES, STATUSES, Case, CaseNote, User, utcnow

bp = Blueprint("cases", __name__)

# Fields whose before/after values are recorded in the audit log on edit.
TRACKED_FIELDS = ["title", "client_name", "description", "status", "priority", "assigned_to", "due_date"]


def get_case(case_id):
    case = db.session.get(Case, case_id)
    if case is None:
        abort(404)
    return case


def _assignee_choices():
    return [(0, "— Unassigned —")] + [(u.id, u.full_name) for u in User.all()]


def _add_note(case, body):
    db.session.add(CaseNote(case=case, author_id=current_user.id, body=body))


def _jsonable(value):
    return value.isoformat() if hasattr(value, "isoformat") else value


def _recent_cases():
    return sa.select(Case).options(joinedload(Case.assignee)).order_by(Case.updated_at.desc())


@bp.route("/dashboard")
@login_required
def dashboard():
    counts = {s: 0 for s in STATUSES}
    for status, n in db.session.execute(
        sa.select(Case.status, sa.func.count(Case.id)).group_by(Case.status)
    ):
        counts[status] = n
    my_cases = db.session.scalars(
        _recent_cases()
        .filter(Case.assigned_to == current_user.id, Case.status != "Closed")
        .limit(10)
    ).all()
    recent = db.session.scalars(_recent_cases().limit(5)).all()
    return render_template(
        "dashboard.html",
        counts=counts,
        total=sum(counts.values()),
        my_cases=my_cases,
        recent=recent,
    )


@bp.route("/cases")
@login_required
def list_cases():
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "")
    priority = request.args.get("priority", "")
    mine = request.args.get("mine") == "1"

    query = _recent_cases()
    if q:
        like = f"%{q}%"
        query = query.filter(
            sa.or_(Case.title.ilike(like), Case.client_name.ilike(like), Case.description.ilike(like))
        )
    if status in STATUSES:
        query = query.filter(Case.status == status)
    if priority in PRIORITIES:
        query = query.filter(Case.priority == priority)
    if mine:
        query = query.filter(Case.assigned_to == current_user.id)
    cases = db.session.scalars(query).all()

    filters = {"q": q, "status": status, "priority": priority, "mine": mine}
    log_event("case.list_viewed", details={k: v for k, v in filters.items() if v} or None)
    db.session.commit()
    return render_template(
        "cases/list.html", cases=cases, statuses=STATUSES, priorities=PRIORITIES, filters=filters
    )


@bp.route("/cases/new", methods=["GET", "POST"])
@login_required
def create_case():
    form = CaseForm()
    form.assigned_to.choices = _assignee_choices()
    if request.method == "GET":
        form.assigned_to.data = current_user.id
    if form.validate_on_submit():
        case = Case(
            title=form.title.data.strip(),
            client_name=form.client_name.data.strip(),
            description=form.description.data or "",
            status=form.status.data,
            priority=form.priority.data,
            assigned_to=form.assigned_to.data or None,
            created_by=current_user.id,
            due_date=form.due_date.data,
        )
        db.session.add(case)
        _add_note(case, "Case opened.")
        db.session.flush()
        log_event(
            "case.created",
            case_id=case.id,
            details={f: _jsonable(getattr(case, f)) for f in TRACKED_FIELDS},
        )
        db.session.commit()
        flash(f"Case {case.case_number} created.", "success")
        return redirect(url_for("cases.view_case", case_id=case.id))
    return render_template("cases/form.html", form=form, case=None)


@bp.route("/cases/<int:case_id>")
@login_required
def view_case(case_id):
    case = get_case(case_id)
    log_event("case.viewed", case_id=case.id)
    db.session.commit()
    return render_template("cases/detail.html", case=case, notes=case.notes, note_form=NoteForm())


@bp.route("/cases/<int:case_id>/edit", methods=["GET", "POST"])
@login_required
def edit_case(case_id):
    case = get_case(case_id)
    form = CaseForm(obj=case if request.method == "GET" else None)
    form.assigned_to.choices = _assignee_choices()
    if request.method == "GET":
        form.assigned_to.data = case.assigned_to or 0
    if form.validate_on_submit():
        new = {
            "title": form.title.data.strip(),
            "client_name": form.client_name.data.strip(),
            "description": form.description.data or "",
            "status": form.status.data,
            "priority": form.priority.data,
            "assigned_to": form.assigned_to.data or None,
            "due_date": form.due_date.data,
        }
        changes = {
            f: [_jsonable(getattr(case, f)), _jsonable(v)]
            for f, v in new.items()
            if getattr(case, f) != v
        }

        timeline = []
        if "status" in changes:
            timeline.append(f"Status: {case.status} → {new['status']}")
        if "priority" in changes:
            timeline.append(f"Priority: {case.priority} → {new['priority']}")
        if "assigned_to" in changes:
            names = dict(form.assigned_to.choices)
            timeline.append(
                f"Reassigned: {case.assignee_name or 'Unassigned'}"
                f" → {names.get(new['assigned_to'] or 0, 'Unassigned')}"
            )

        if changes:
            for f, v in new.items():
                setattr(case, f, v)
            case.updated_at = utcnow()
            if timeline:
                _add_note(case, "; ".join(timeline))
            log_event("case.updated", case_id=case.id, details={"changes": changes})
            db.session.commit()
            flash("Case updated.", "success")
        else:
            flash("No changes to save.", "info")
        return redirect(url_for("cases.view_case", case_id=case.id))
    return render_template("cases/form.html", form=form, case=case)


@bp.route("/cases/<int:case_id>/notes", methods=["POST"])
@login_required
def add_note(case_id):
    case = get_case(case_id)
    form = NoteForm()
    if form.validate_on_submit():
        note = CaseNote(case=case, author_id=current_user.id, body=form.body.data.strip())
        db.session.add(note)
        case.updated_at = utcnow()
        db.session.flush()
        log_event("case.note_added", case_id=case.id, details={"note_id": note.id})
        db.session.commit()
        flash("Note added.", "success")
    else:
        flash("Note cannot be empty.", "error")
    return redirect(url_for("cases.view_case", case_id=case.id))


@bp.route("/cases/<int:case_id>/delete", methods=["POST"])
@login_required
def delete_case(case_id):
    case = get_case(case_id)
    if not current_user.is_admin:
        log_event("case.delete_denied", case_id=case.id)
        db.session.commit()
        abort(403)
    snapshot = {f: _jsonable(getattr(case, f)) for f in TRACKED_FIELDS}
    snapshot["note_count"] = len(case.notes)
    number = case.case_number
    db.session.delete(case)
    log_event("case.deleted", case_id=case_id, details=snapshot)
    db.session.commit()
    flash(f"Case {number} deleted.", "info")
    return redirect(url_for("cases.list_cases"))
