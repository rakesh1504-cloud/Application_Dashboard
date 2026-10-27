import os

import pytest

from cms import create_app
from cms.db import database_url, db

# Set TEST_DATABASE_URL (e.g. a throwaway Postgres database) to run the suite
# against that database instead of a temporary SQLite file. All its tables
# are dropped and recreated for every test.
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")


@pytest.fixture
def app(tmp_path):
    if TEST_DATABASE_URL:
        uri = database_url("", {"DATABASE_URL": TEST_DATABASE_URL})
    else:
        uri = f"sqlite:///{tmp_path / 'test.sqlite'}"
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": uri,
        "WTF_CSRF_ENABLED": False,
        "SECRET_KEY": "test",
    })
    with app.app_context():
        db.drop_all()
        db.create_all()
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()
        db.engine.dispose()


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
