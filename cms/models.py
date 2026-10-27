from datetime import datetime, timezone

import sqlalchemy as sa
from flask_login import UserMixin
from sqlalchemy.dialects.postgresql import JSONB
from werkzeug.security import check_password_hash, generate_password_hash

from .db import db

STATUSES = ["Open", "In Progress", "Pending", "Closed"]
PRIORITIES = ["Low", "Medium", "High", "Critical"]


def utcnow():
    return datetime.now(timezone.utc)


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(40), unique=True, nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(10), nullable=False, default="agent")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (sa.CheckConstraint("role IN ('admin', 'agent')", name="ck_users_role"),)

    @property
    def is_admin(self):
        return self.role == "admin"

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @staticmethod
    def get_by_username(username):
        return db.session.scalar(sa.select(User).filter_by(username=username))

    @staticmethod
    def create(username, full_name, email, password):
        """Create a user; the very first account becomes the admin."""
        is_first = db.session.scalar(sa.select(sa.func.count(User.id))) == 0
        user = User(
            username=username,
            full_name=full_name,
            email=email,
            password_hash=generate_password_hash(password),
            role="admin" if is_first else "agent",
        )
        db.session.add(user)
        return user

    @staticmethod
    def all():
        return db.session.scalars(sa.select(User).order_by(User.full_name)).all()


class Case(db.Model):
    __tablename__ = "cases"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False, default="")
    client_name = db.Column(db.String(120), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="Open", index=True)
    priority = db.Column(db.String(10), nullable=False, default="Medium")
    assigned_to = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    due_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    assignee = db.relationship("User", foreign_keys=[assigned_to])
    creator = db.relationship("User", foreign_keys=[created_by])
    notes = db.relationship(
        "CaseNote",
        back_populates="case",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="(CaseNote.created_at.desc(), CaseNote.id.desc())",
    )

    @property
    def assignee_name(self):
        return self.assignee.full_name if self.assignee else None

    @property
    def creator_name(self):
        return self.creator.full_name

    @property
    def case_number(self):
        return f"CMS-{self.id:05d}"


class CaseNote(db.Model):
    __tablename__ = "case_notes"

    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(
        db.Integer, db.ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True
    )
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    case = db.relationship("Case", back_populates="notes")
    author = db.relationship("User")

    @property
    def author_name(self):
        return self.author.full_name


class AuditLog(db.Model):
    """Append-only record of every case- and sign-in-related request.

    ``case_id`` is deliberately not a foreign key, and ``username`` is copied,
    so the trail survives deletion of the case or the user.
    """

    __tablename__ = "audit_log"

    id = db.Column(db.BigInteger().with_variant(db.Integer, "sqlite"), primary_key=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), index=True)
    username = db.Column(db.String(40))
    action = db.Column(db.String(40), nullable=False, index=True)
    case_id = db.Column(db.Integer, index=True)
    details = db.Column(db.JSON(none_as_null=True).with_variant(JSONB(none_as_null=True), "postgresql"))
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(255))
    method = db.Column(db.String(10))
    path = db.Column(db.String(255))
