import io

from app.db import get_db


def _create_video_with_quiz(client, auth, app):
    auth.login()
    client.post(
        "/videos/upload",
        data={
            "title": "クイズ用動画",
            "description": "研修内容の説明。",
            "video_file": (io.BytesIO(b"fake"), "sample.mp4"),
        },
        content_type="multipart/form-data",
    )

    with app.app_context():
        video_id = get_db().execute("SELECT id FROM video").fetchone()["id"]

    client.post(f"/videos/{video_id}/process")

    with app.app_context():
        quiz_id = (
            get_db()
            .execute("SELECT id FROM quiz WHERE video_id = ?", (video_id,))
            .fetchone()["id"]
        )
    return quiz_id


def test_take_quiz_requires_login(client):
    response = client.get("/quiz/1")
    assert response.headers["Location"] == "/auth/login"


def test_take_quiz_404(client, auth):
    auth.login()
    response = client.get("/quiz/999")
    assert response.status_code == 404


def test_take_and_submit_quiz(client, auth, app):
    quiz_id = _create_video_with_quiz(client, auth, app)

    response = client.get(f"/quiz/{quiz_id}")
    assert response.status_code == 200

    with app.app_context():
        questions = get_db().execute(
            "SELECT * FROM quiz_question WHERE quiz_id = ?", (quiz_id,)
        ).fetchall()

    form_data = {f"question_{q['id']}": q["correct_choice"] for q in questions}
    response = client.post(f"/quiz/{quiz_id}", data=form_data)
    assert response.status_code == 302

    with app.app_context():
        attempt = get_db().execute("SELECT * FROM quiz_attempt").fetchone()
        assert attempt["score"] == len(questions)
        assert attempt["total"] == len(questions)

    result_response = client.get(response.headers["Location"])
    assert result_response.status_code == 200
