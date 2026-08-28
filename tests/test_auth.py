import pytest
from flask import g, session

from app.db import get_db


def test_register(client, app):
    response = client.post("/auth/register", data={"username": "a", "password": "a"})
    assert response.headers["Location"] == "/auth/login"

    with app.app_context():
        assert (
            get_db().execute("SELECT * FROM user WHERE username = 'a'").fetchone()
            is not None
        )


@pytest.mark.parametrize(
    ("username", "password", "message"),
    (
        ("", "", "ユーザー名を入力してください。".encode("utf-8")),
        ("a", "", "パスワードを入力してください。".encode("utf-8")),
        ("testuser", "password", "既に登録されています".encode("utf-8")),
    ),
)
def test_register_validate_input(client, username, password, message):
    response = client.post(
        "/auth/register", data={"username": username, "password": password}
    )
    assert message in response.data


def test_login(client, auth):
    response = auth.login()
    assert response.headers["Location"] == "/"

    with client:
        client.get("/")
        assert session["user_id"] == 1
        assert g.user["username"] == "testuser"


def test_login_validate_input(client, auth):
    response = auth.login(username="wrong", password="wrong")
    assert "ユーザー名またはパスワードが正しくありません。".encode("utf-8") in response.data


def test_logout(client, auth):
    auth.login()

    with client:
        auth.logout()
        assert "user_id" not in session
