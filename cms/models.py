from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from .db import get_db

STATUSES = ["Open", "In Progress", "Pending", "Closed"]
PRIORITIES = ["Low", "Medium", "High", "Critical"]


class User(UserMixin):
    def __init__(self, row):
        self.id = row["id"]
        self.username = row["username"]
        self.full_name = row["full_name"]
        self.email = row["email"]
        self.role = row["role"]
        self._password_hash = row["password_hash"]

    @property
    def is_admin(self):
        return self.role == "admin"

    def check_password(self, password):
        return check_password_hash(self._password_hash, password)

    @staticmethod
    def get(user_id):
        row = get_db().execute("SELECT * FROM user WHERE id = ?", (user_id,)).fetchone()
        return User(row) if row else None

    @staticmethod
    def get_by_username(username):
        row = get_db().execute(
            "SELECT * FROM user WHERE username = ?", (username,)
        ).fetchone()
        return User(row) if row else None

    @staticmethod
    def create(username, full_name, email, password):
        """Create a user; the very first account becomes the admin."""
        db = get_db()
        is_first = db.execute("SELECT COUNT(*) FROM user").fetchone()[0] == 0
        cur = db.execute(
            "INSERT INTO user (username, full_name, email, password_hash, role)"
            " VALUES (?, ?, ?, ?, ?)",
            (
                username,
                full_name,
                email,
                generate_password_hash(password),
                "admin" if is_first else "agent",
            ),
        )
        db.commit()
        return User.get(cur.lastrowid)

    @staticmethod
    def all():
        return get_db().execute(
            "SELECT id, full_name FROM user ORDER BY full_name"
        ).fetchall()
