from flask import Flask

from config import Config
from .extensions import db


def create_app(config_class=Config):
    """Application factory: creates the app and registers all blueprints."""
    app = Flask(__name__)
    app.config.from_object(config_class)
    db.init_app(app)

    from .blueprints import main, students, attendance, marks, analytics

    app.register_blueprint(main.bp)
    app.register_blueprint(students.bp, url_prefix="/students")
    app.register_blueprint(attendance.bp, url_prefix="/attendance")
    app.register_blueprint(marks.bp, url_prefix="/marks")
    app.register_blueprint(analytics.bp, url_prefix="/analytics")

    with app.app_context():
        db.create_all()

    return app
