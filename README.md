# Case Management System (CMS)

A web portal where users sign in to open, track and work on cases.
It's built with Flask and stores its data in **PostgreSQL**. SQLite is used
automatically when no database is configured, which is handy for a quick local try-out.

![Login](docs/login.png)

## Features

- **Sign-in:** register, log in and log out. Passwords are stored hashed, and every form has CSRF protection.
- **Roles:** the first account you register becomes the **admin**. Every later account is an **agent**. Only admins can delete cases.
- **Dashboard:** case counts by status, your open cases and recently updated cases.
- **Cases:** create, view and edit cases. Each case has a case number (`CMS-00001`), title, client, description, status, priority, assignee and due date.
- **Search and filters:** search by text, filter by status or priority, or show only cases assigned to you.
- **Notes and activity:** each case has a timeline of notes. Changes to status, priority and assignee are logged automatically.
- **Audit log:** every case-related request is recorded in the database: case created, viewed, listed or searched, updated (with old and new values for each field), note added, deleted (with a snapshot of the case) and refused deletes. So are sign-ins, failed sign-ins, sign-outs and registrations. Each entry stores who, when, IP address, browser, and the request path. Admins can browse and filter it under **Audit log**, or from **Audit trail** on any case.

## Quick start

**Windows:** double-click `start.bat`. **macOS/Linux:** run `./start.sh`.
The first run sets everything up. When the window shows *"CMS is running"*,
open http://127.0.0.1:5000. Keep that window open while you use the app,
because closing it stops the server.

### Manual setup

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

flask --app cms db upgrade         # creates/updates the tables
flask --app cms run --debug        # http://127.0.0.1:5000
```

Open http://127.0.0.1:5000, click **Create one** and register. The first account is the admin.
`run.py` (used by the start scripts) runs `db upgrade` for you on every start.

## Connecting to PostgreSQL

Set `DATABASE_URL`, either as an environment variable or in a `.env` file
in the project folder (copy `.env.example`):

```
DATABASE_URL=postgresql://cms_app:PASSWORD@pg01.corp.local:5432/cms?sslmode=require
```

Then start the app as usual. On the first start it creates all tables in that database.

**Setting up the database on your internal Postgres server** (run once as a DBA):

```sql
CREATE USER cms_app WITH PASSWORD 'choose-a-strong-password';
CREATE DATABASE cms OWNER cms_app;
```

The app only needs this one account, which owns the `cms` database. It doesn't need superuser rights.
The server running the app must be able to reach the database host on port 5432.

**No Postgres server yet?** Run one locally with Docker:

```bash
docker compose up -d
# DATABASE_URL=postgresql://cms_app:cms_dev_pw@localhost:5432/cms
```

### Tables

| Table        | Holds |
|--------------|-------|
| `users`      | accounts, hashed passwords, role (`admin` / `agent`) |
| `cases`      | one row per case |
| `case_notes` | notes and the automatic change timeline for each case |
| `audit_log`  | every case and sign-in request (`action`, `case_id`, `username`, `details` as JSONB, IP, path, time) |
| `alembic_version` | the schema version, managed by migrations |

`audit_log.case_id` is intentionally not a foreign key, and the username is copied into each row,
so the history of a case stays in the log after the case or user is deleted. Example queries:

```sql
-- Full history of one case
SELECT created_at, username, action, details FROM audit_log WHERE case_id = 42 ORDER BY id;

-- Every status change in the last 7 days
SELECT case_id, username, details->'changes'->'status' AS status_change, created_at
FROM audit_log
WHERE action = 'case.updated' AND details->'changes' ? 'status'
  AND created_at > now() - interval '7 days';
```

### Changing the schema later

Edit `cms/models.py`, then generate and apply a migration:

```bash
flask --app cms db migrate -m "describe the change"
flask --app cms db upgrade
```

Commit the new file in `migrations/versions/`. Existing data is kept.

### Configuration

| Variable          | Purpose                                     | Default         |
|-------------------|---------------------------------------------|-----------------|
| `DATABASE_URL`    | PostgreSQL connection URL                   | local SQLite file `instance/cms.sqlite` |
| `CMS_SECRET_KEY`  | Session signing key (**set in production**) | `dev-change-me` |
| `CMS_TRUST_PROXY` | Set to `1` behind a load balancer so the audit log records the real client IP | off |

## Tests

```bash
pip install -r requirements-dev.txt
pytest                                     # uses a temporary SQLite database

# Against a throwaway Postgres database (all its tables are dropped):
TEST_DATABASE_URL=postgresql://cms_app:PASSWORD@localhost:5432/cms_test pytest
```

## Project layout

```
cms/
  __init__.py      app factory, login manager, CSRF
  db.py            SQLAlchemy + migrations setup, DATABASE_URL handling
  models.py        User, Case, CaseNote, AuditLog
  audit.py         log_event() helper + /audit page
  forms.py         WTForms forms
  auth.py          /auth/login, /auth/register, /auth/logout
  cases.py         /dashboard, /cases, case detail/edit/notes/delete
  templates/       Jinja templates
  static/style.css
migrations/        Alembic schema migrations
docker-compose.yml local PostgreSQL for development
tests/             pytest suite
```

## Screenshots

| Dashboard | Case detail |
|---|---|
| ![Dashboard](docs/dashboard.png) | ![Case detail](docs/detail.png) |

![Audit log](docs/audit.png)
