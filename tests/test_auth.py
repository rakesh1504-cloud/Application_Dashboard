from cms.models import User


def test_root_redirects_to_login(client):
    resp = client.get("/")
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["Location"]


def test_login_page_shows_portal_name(client):
    resp = client.get("/auth/login")
    assert b"Case Management System" in resp.data


def test_protected_pages_require_login(client):
    for path in ("/dashboard", "/cases", "/cases/new"):
        resp = client.get(path)
        assert resp.status_code == 302
        assert "/auth/login" in resp.headers["Location"]


def test_first_user_is_admin_next_is_agent(app, auth):
    auth.register("alice")
    auth.logout()
    auth.register("bob", full_name="Bob Agent")
    with app.app_context():
        assert User.get_by_username("alice").role == "admin"
        assert User.get_by_username("bob").role == "agent"


def test_register_logs_in_and_shows_dashboard(auth):
    resp = auth.register()
    assert b"Dashboard" in resp.data
    assert b"Alice Admin" in resp.data


def test_duplicate_username_rejected(auth):
    auth.register()
    auth.logout()
    resp = auth.register(email="other@example.com")
    assert b"That username is taken." in resp.data


def test_password_mismatch_rejected(client):
    resp = client.post("/auth/register", data={
        "full_name": "X", "username": "xyz", "email": "x@example.com",
        "password": "password123", "confirm": "different1",
    })
    assert b"Passwords must match." in resp.data


def test_login_logout(auth, client):
    auth.register()
    auth.logout()
    resp = auth.login(password="wrong-password")
    assert b"Invalid username or password." in resp.data
    resp = auth.login()
    assert b"Welcome back" in resp.data
    auth.logout()
    assert client.get("/dashboard").status_code == 302


def test_login_ignores_external_next(auth, client):
    auth.register()
    auth.logout()
    resp = client.post("/auth/login?next=https://evil.example/",
                       data={"username": "alice", "password": "password123"})
    assert resp.headers["Location"] == "/dashboard"
