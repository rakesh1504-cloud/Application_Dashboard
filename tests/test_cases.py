from cms.db import get_db


def _create_case(client, **overrides):
    data = {
        "title": "Billing dispute",
        "client_name": "Acme Corp",
        "description": "Customer disputes invoice #42.",
        "status": "Open",
        "priority": "High",
        "assigned_to": "1",
        "due_date": "",
    }
    data.update(overrides)
    return client.post("/cases/new", data=data, follow_redirects=True)


def test_create_and_view_case(auth, client):
    auth.register()
    resp = _create_case(client)
    assert b"CMS-00001" in resp.data
    assert b"Billing dispute" in resp.data
    assert b"Case opened." in resp.data


def test_create_case_requires_title(auth, client):
    auth.register()
    resp = _create_case(client, title="")
    assert b"This field is required." in resp.data


def test_list_filters(auth, client):
    auth.register()
    _create_case(client, title="Alpha issue", status="Open")
    _create_case(client, title="Beta issue", status="Closed", client_name="Globex")
    resp = client.get("/cases?status=Closed")
    assert b"Beta issue" in resp.data and b"Alpha issue" not in resp.data
    resp = client.get("/cases?q=Globex")
    assert b"Beta issue" in resp.data and b"Alpha issue" not in resp.data


def test_edit_case_logs_changes(auth, client):
    auth.register()
    _create_case(client)
    resp = client.post("/cases/1/edit", data={
        "title": "Billing dispute", "client_name": "Acme Corp", "description": "",
        "status": "In Progress", "priority": "Critical", "assigned_to": "0", "due_date": "2026-12-01",
    }, follow_redirects=True)
    assert b"Case updated." in resp.data
    assert "Status: Open → In Progress".encode() in resp.data
    assert "Priority: High → Critical".encode() in resp.data
    assert b"Unassigned" in resp.data
    assert b"01 Dec 2026" in resp.data


def test_add_note(auth, client):
    auth.register()
    _create_case(client)
    resp = client.post("/cases/1/notes", data={"body": "Called the customer."}, follow_redirects=True)
    assert b"Called the customer." in resp.data


def test_dashboard_counts(auth, client):
    auth.register()
    _create_case(client)
    _create_case(client, status="Closed")
    resp = client.get("/dashboard")
    assert b"Total cases" in resp.data
    assert b"Billing dispute" in resp.data


def test_only_admin_can_delete(app, auth, client):
    auth.register("alice")
    _create_case(client)
    auth.logout()
    auth.register("bob", full_name="Bob Agent")
    assert client.post("/cases/1/delete").status_code == 403
    auth.logout()
    auth.login("alice")
    resp = client.post("/cases/1/delete", follow_redirects=True)
    assert b"deleted" in resp.data
    with app.app_context():
        assert get_db().execute("SELECT COUNT(*) FROM case_note").fetchone()[0] == 0


def test_missing_case_404(auth, client):
    auth.register()
    assert client.get("/cases/999").status_code == 404
