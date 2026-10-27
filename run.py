"""Start the CMS locally: brings the database schema up to date, then serves it."""
from flask_migrate import upgrade

from cms import create_app

app = create_app()

if __name__ == "__main__":
    with app.app_context():
        upgrade()
    print("CMS is running - open http://127.0.0.1:5000 (press Ctrl+C to stop)")
    app.run(host="127.0.0.1", port=5000)
