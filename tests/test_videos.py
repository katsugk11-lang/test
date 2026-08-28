import io

from app.db import get_db


def test_index_accessible_without_login(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "まだ動画がアップロードされていません".encode("utf-8") in response.data


def test_upload_requires_login(client):
    response = client.get("/videos/upload")
    assert response.headers["Location"] == "/auth/login"


def test_upload(client, auth, app):
    auth.login()
    data = {
        "title": "テスト動画",
        "description": "これはテスト用の動画説明です。",
        "transcript": "",
        "video_file": (io.BytesIO(b"fake video content"), "sample.mp4"),
    }
    response = client.post(
        "/videos/upload", data=data, content_type="multipart/form-data"
    )
    assert response.headers["Location"] == "/"

    with app.app_context():
        video = get_db().execute("SELECT * FROM video").fetchone()
        assert video["title"] == "テスト動画"
        assert video["status"] == "uploaded"


def test_upload_rejects_bad_extension(client, auth):
    auth.login()
    data = {
        "title": "テスト動画",
        "video_file": (io.BytesIO(b"not a video"), "sample.txt"),
    }
    response = client.post(
        "/videos/upload", data=data, content_type="multipart/form-data"
    )
    assert "対応していないファイル形式です。".encode("utf-8") in response.data


def test_detail_404(client):
    response = client.get("/videos/999")
    assert response.status_code == 404


def test_process_generates_summary_and_quiz(client, auth, app):
    auth.login()
    client.post(
        "/videos/upload",
        data={
            "title": "AIテスト",
            "description": "研修動画の説明文です。",
            "transcript": "",
            "video_file": (io.BytesIO(b"fake video content"), "sample.mp4"),
        },
        content_type="multipart/form-data",
    )

    with app.app_context():
        video_id = get_db().execute("SELECT id FROM video").fetchone()["id"]

    response = client.post(f"/videos/{video_id}/process")
    assert response.status_code == 302

    with app.app_context():
        db = get_db()
        video = db.execute("SELECT * FROM video WHERE id = ?", (video_id,)).fetchone()
        assert video["status"] == "completed"

        summary = db.execute(
            "SELECT * FROM video_summary WHERE video_id = ?", (video_id,)
        ).fetchone()
        assert summary is not None

        questions = db.execute(
            "SELECT qq.* FROM quiz_question qq JOIN quiz q ON qq.quiz_id = q.id"
            " WHERE q.video_id = ?",
            (video_id,),
        ).fetchall()
        assert len(questions) > 0


def test_process_without_text_fails_gracefully(client, auth, app):
    auth.login()
    client.post(
        "/videos/upload",
        data={
            "title": "説明なし動画",
            "video_file": (io.BytesIO(b"fake"), "sample.mp4"),
        },
        content_type="multipart/form-data",
    )

    with app.app_context():
        video_id = get_db().execute("SELECT id FROM video").fetchone()["id"]

    response = client.post(f"/videos/{video_id}/process", follow_redirects=True)
    assert "要約・クイズ生成には".encode("utf-8") in response.data


def test_delete_requires_owner(client, auth, app):
    auth.login()
    client.post(
        "/videos/upload",
        data={
            "title": "削除テスト",
            "description": "desc",
            "video_file": (io.BytesIO(b"fake"), "sample.mp4"),
        },
        content_type="multipart/form-data",
    )
    with app.app_context():
        video_id = get_db().execute("SELECT id FROM video").fetchone()["id"]

    auth.logout()
    auth.register(username="other", password="password")
    auth.login(username="other", password="password")

    response = client.post(f"/videos/{video_id}/delete")
    assert response.status_code == 403
