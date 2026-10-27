import pytest

from cms import create_app
from cms.db import init_db


@pytest.fixture
def app(tmp_path):
    app = create_app({
        "TESTING": True,
        "DATABASE": str(tmp_path / "test.sqlite"),
        "WTF_CSRF_ENABLED": False,
        "SECRET_KEY": "test",
    })
    with app.app_context():
        init_db()
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


class AuthActions:
    def __init__(self, client):
        self._client = client

    def register(self, username="alice", full_name="Alice Admin", email=None, password="password123"):
        return self._client.post("/auth/register", data={
            "full_name": full_name,
            "username": username,
            "email": email or f"{username}@example.com",
            "password": password,
            "confirm": password,
        }, follow_redirects=True)

    def login(self, username="alice", password="password123"):
        return self._client.post("/auth/login", data={
            "username": username, "password": password,
        }, follow_redirects=True)

    def logout(self):
        return self._client.post("/auth/logout", follow_redirects=True)


@pytest.fixture
def auth(client):
    return AuthActions(client)
