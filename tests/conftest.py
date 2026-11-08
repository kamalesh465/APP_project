import os

os.environ["SECRET_KEY"] = "pytest-test-secret-key"

import pytest

from config import Config
from app import create_app
from app.extensions import db


class TestConfig(Config):
    TESTING = True
    SECRET_KEY = os.environ["SECRET_KEY"]
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


@pytest.fixture
def app():
    application = create_app(TestConfig)
    with application.app_context():
        db.drop_all()
        db.create_all()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()
