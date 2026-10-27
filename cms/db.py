from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
# Batch mode lets Alembic alter tables on SQLite (used for local dev/tests).
migrate = Migrate(render_as_batch=True)


def database_url(instance_path, env):
    """Resolve the SQLAlchemy URL: DATABASE_URL if set, else a local SQLite file.

    Plain ``postgres://`` / ``postgresql://`` URLs are pointed at the psycopg 3 driver.
    """
    url = env.get("DATABASE_URL")
    if not url:
        return "sqlite:///" + f"{instance_path}/cms.sqlite"
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url
