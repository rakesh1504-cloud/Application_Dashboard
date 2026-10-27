import sqlalchemy as sa

from cms.db import db
from cms.models import AuditLog
from test_cases import _create_case


def _actions(app, **filters):
    with app.app_context():
        q = sa.select(AuditLog).filter_by(**filters).order_by(AuditLog.id)
        return [(e.action, e.case_id, e.details, e.username) for e in db.session.scalars(q)]


def test_auth_events_are_logged(app, auth):
    auth.register()
    auth.logout()
    auth.login(password="wrong-password")
    auth.login()
    actions = [a[0] for a in _actions(app)]
    assert actions == ["auth.register", "auth.logout", "auth.login_failed", "auth.login"]
    failed = _actions(app, action="auth.login_failed")[0]
    assert failed[2] == {"username": "alice"} and failed[3] is None


def test_case_lifecycle_is_logged(app, auth, client):
    auth.register()
    _create_case(client)
    client.get("/cases?status=Open")
    client.post("/cases/1/edit", data={
        "title": "Billing dispute", "client_name": "Acme Corp", "description": "",
        "status": "Closed", "priority": "High", "assigned_to": "1", "due_date": "",
    })
    client.post("/cases/1/notes", data={"body": "Refund issued."})
    client.post("/cases/1/delete")

    events = _actions(app, case_id=1)
    actions = [e[0] for e in events]
    assert actions[0] == "case.created"
    assert "case.viewed" in actions
    assert "case.updated" in actions and "case.note_added" in actions
    assert actions[-1] == "case.deleted"

    created = events[0][2]
    assert created["title"] == "Billing dispute" and created["status"] == "Open"
    updated = next(e for e in events if e[0] == "case.updated")[2]["changes"]
    assert updated["status"] == ["Open", "Closed"]
    assert updated["description"] == ["Customer disputes invoice #42.", ""]
    deleted = events[-1][2]
    assert deleted["status"] == "Closed" and deleted["note_count"] >= 2

    listed = _actions(app, action="case.list_viewed")
    assert listed[0][2] == {"status": "Open"}


def test_denied_delete_is_logged(app, auth, client):
    auth.register("alice")
    _create_case(client)
    auth.logout()
    auth.register("bob", full_name="Bob Agent")
    assert client.post("/cases/1/delete").status_code == 403
    denied = _actions(app, action="case.delete_denied")
    assert denied == [("case.delete_denied", 1, None, "bob")]


def test_audit_page_admin_only(auth, client):
    auth.register("alice")
    _create_case(client)
    resp = client.get("/audit?case_id=1")
    assert resp.status_code == 200
    assert b"case.created" in resp.data
    auth.logout()
    auth.register("bob", full_name="Bob Agent")
    assert client.get("/audit").status_code == 403
