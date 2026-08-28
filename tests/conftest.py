import os
import tempfile

import pytest
from werkzeug.security import generate_password_hash

from app import create_app
from app.db import get_db, init_db


@pytest.fixture
def app():
    db_fd, db_path = tempfile.mkstemp()
    upload_dir = tempfile.mkdtemp()

    app = create_app(
        {
            "TESTING": True,
            "DATABASE": db_path,
            "UPLOAD_FOLDER": upload_dir,
            "AI_PROVIDER": "mock",
            "AI_API_KEY": "",
        }
    )

    with app.app_context():
        init_db()
        db = get_db()
        db.execute(
            "INSERT INTO user (username, password_hash) VALUES (?, ?)",
            ("testuser", generate_password_hash("password")),
        )
        db.commit()

    yield app

    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def runner(app):
    return app.test_cli_runner()


class AuthActions:
    def __init__(self, client):
        self._client = client

    def register(self, username="newuser", password="password"):
        return self._client.post(
            "/auth/register", data={"username": username, "password": password}
        )

    def login(self, username="testuser", password="password"):
        return self._client.post(
            "/auth/login", data={"username": username, "password": password}
        )

    def logout(self):
        return self._client.get("/auth/logout")


@pytest.fixture
def auth(client):
    return AuthActions(client)
