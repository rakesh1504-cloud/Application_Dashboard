from flask_wtf import FlaskForm
from wtforms import (
    DateField,
    EmailField,
    PasswordField,
    SelectField,
    StringField,
    TextAreaField,
)
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional

from .models import PRIORITIES, STATUSES


class LoginForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])


class RegisterForm(FlaskForm):
    full_name = StringField("Full name", validators=[DataRequired(), Length(max=100)])
    username = StringField("Username", validators=[DataRequired(), Length(3, 40)])
    email = EmailField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=8)])
    confirm = PasswordField(
        "Confirm password",
        validators=[DataRequired(), EqualTo("password", "Passwords must match.")],
    )


class CaseForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired(), Length(max=200)])
    client_name = StringField("Client", validators=[DataRequired(), Length(max=120)])
    description = TextAreaField("Description", validators=[Optional()])
    status = SelectField("Status", choices=STATUSES)
    priority = SelectField("Priority", choices=PRIORITIES, default="Medium")
    assigned_to = SelectField("Assigned to", coerce=int)
    due_date = DateField("Due date", validators=[Optional()])


class NoteForm(FlaskForm):
    body = TextAreaField("Add a note", validators=[DataRequired()])
