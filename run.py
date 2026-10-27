"""Start the CMS locally: creates the database on first run, then serves it."""
import os

from cms import create_app
from cms.db import init_db

app = create_app()

if __name__ == "__main__":
    if not os.path.exists(app.config["DATABASE"]):
        with app.app_context():
            init_db()
        print("Created a new CMS database.")
    print("CMS is running - open http://127.0.0.1:5000 (press Ctrl+C to stop)")
    app.run(host="127.0.0.1", port=5000)
