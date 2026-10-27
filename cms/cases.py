from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from .db import get_db
from .forms import CaseForm, NoteForm
from .models import PRIORITIES, STATUSES, User

bp = Blueprint("cases", __name__)

CASE_SELECT = """
    SELECT c.*, a.full_name AS assignee_name, cr.full_name AS creator_name
    FROM cases c
    LEFT JOIN user a ON a.id = c.assigned_to
    JOIN user cr ON cr.id = c.created_by
"""


def get_case(case_id):
    case = get_db().execute(CASE_SELECT + " WHERE c.id = ?", (case_id,)).fetchone()
    if case is None:
        abort(404)
    return case


def _assignee_choices():
    return [(0, "— Unassigned —")] + [(u["id"], u["full_name"]) for u in User.all()]


def _add_note(case_id, body):
    get_db().execute(
        "INSERT INTO case_note (case_id, author_id, body) VALUES (?, ?, ?)",
        (case_id, current_user.id, body),
    )


@bp.route("/dashboard")
@login_required
def dashboard():
    db = get_db()
    counts = {s: 0 for s in STATUSES}
    for row in db.execute("SELECT status, COUNT(*) AS n FROM cases GROUP BY status"):
        counts[row["status"]] = row["n"]
    my_cases = db.execute(
        CASE_SELECT + " WHERE c.assigned_to = ? AND c.status != 'Closed'"
        " ORDER BY c.updated_at DESC LIMIT 10",
        (current_user.id,),
    ).fetchall()
    recent = db.execute(CASE_SELECT + " ORDER BY c.updated_at DESC LIMIT 5").fetchall()
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

    clauses, params = [], []
    if q:
        clauses.append("(c.title LIKE ? OR c.client_name LIKE ? OR c.description LIKE ?)")
        params += [f"%{q}%"] * 3
    if status in STATUSES:
        clauses.append("c.status = ?")
        params.append(status)
    if priority in PRIORITIES:
        clauses.append("c.priority = ?")
        params.append(priority)
    if mine:
        clauses.append("c.assigned_to = ?")
        params.append(current_user.id)

    sql = CASE_SELECT
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY c.updated_at DESC"
    cases = get_db().execute(sql, params).fetchall()
    return render_template(
        "cases/list.html",
        cases=cases,
        statuses=STATUSES,
        priorities=PRIORITIES,
        filters={"q": q, "status": status, "priority": priority, "mine": mine},
    )


@bp.route("/cases/new", methods=["GET", "POST"])
@login_required
def create_case():
    form = CaseForm()
    form.assigned_to.choices = _assignee_choices()
    if request.method == "GET":
        form.assigned_to.data = current_user.id
    if form.validate_on_submit():
        db = get_db()
        cur = db.execute(
            "INSERT INTO cases (title, client_name, description, status, priority,"
            " assigned_to, created_by, due_date) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                form.title.data.strip(),
                form.client_name.data.strip(),
                form.description.data or "",
                form.status.data,
                form.priority.data,
                form.assigned_to.data or None,
                current_user.id,
                form.due_date.data,
            ),
        )
        _add_note(cur.lastrowid, "Case opened.")
        db.commit()
        flash(f"Case CMS-{cur.lastrowid:05d} created.", "success")
        return redirect(url_for("cases.view_case", case_id=cur.lastrowid))
    return render_template("cases/form.html", form=form, case=None)


@bp.route("/cases/<int:case_id>")
@login_required
def view_case(case_id):
    case = get_case(case_id)
    notes = get_db().execute(
        "SELECT n.*, u.full_name AS author_name FROM case_note n"
        " JOIN user u ON u.id = n.author_id WHERE n.case_id = ?"
        " ORDER BY n.created_at DESC, n.id DESC",
        (case_id,),
    ).fetchall()
    return render_template("cases/detail.html", case=case, notes=notes, note_form=NoteForm())


@bp.route("/cases/<int:case_id>/edit", methods=["GET", "POST"])
@login_required
def edit_case(case_id):
    case = get_case(case_id)
    form = CaseForm(data=None if request.method == "POST" else {
        "title": case["title"],
        "client_name": case["client_name"],
        "description": case["description"],
        "status": case["status"],
        "priority": case["priority"],
        "assigned_to": case["assigned_to"] or 0,
        "due_date": case["due_date"],
    })
    form.assigned_to.choices = _assignee_choices()
    if form.validate_on_submit():
        db = get_db()
        changes = []
        if form.status.data != case["status"]:
            changes.append(f"Status: {case['status']} → {form.status.data}")
        if form.priority.data != case["priority"]:
            changes.append(f"Priority: {case['priority']} → {form.priority.data}")
        if (form.assigned_to.data or None) != case["assigned_to"]:
            names = dict(form.assigned_to.choices)
            changes.append(
                f"Reassigned: {case['assignee_name'] or 'Unassigned'}"
                f" → {names.get(form.assigned_to.data, 'Unassigned')}"
            )
        db.execute(
            "UPDATE cases SET title = ?, client_name = ?, description = ?, status = ?,"
            " priority = ?, assigned_to = ?, due_date = ?, updated_at = CURRENT_TIMESTAMP"
            " WHERE id = ?",
            (
                form.title.data.strip(),
                form.client_name.data.strip(),
                form.description.data or "",
                form.status.data,
                form.priority.data,
                form.assigned_to.data or None,
                form.due_date.data,
                case_id,
            ),
        )
        if changes:
            _add_note(case_id, "; ".join(changes))
        db.commit()
        flash("Case updated.", "success")
        return redirect(url_for("cases.view_case", case_id=case_id))
    return render_template("cases/form.html", form=form, case=case)


@bp.route("/cases/<int:case_id>/notes", methods=["POST"])
@login_required
def add_note(case_id):
    get_case(case_id)
    form = NoteForm()
    if form.validate_on_submit():
        db = get_db()
        _add_note(case_id, form.body.data.strip())
        db.execute("UPDATE cases SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", (case_id,))
        db.commit()
        flash("Note added.", "success")
    else:
        flash("Note cannot be empty.", "error")
    return redirect(url_for("cases.view_case", case_id=case_id))


@bp.route("/cases/<int:case_id>/delete", methods=["POST"])
@login_required
def delete_case(case_id):
    get_case(case_id)
    if not current_user.is_admin:
        abort(403)
    db = get_db()
    db.execute("DELETE FROM cases WHERE id = ?", (case_id,))
    db.commit()
    flash(f"Case CMS-{case_id:05d} deleted.", "info")
    return redirect(url_for("cases.list_cases"))
