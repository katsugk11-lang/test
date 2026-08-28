import os

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    g,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from werkzeug.utils import secure_filename

from . import ai_client
from .auth import login_required
from .db import get_db

bp = Blueprint("videos", __name__)


def allowed_file(filename):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in current_app.config["ALLOWED_VIDEO_EXTENSIONS"]


@bp.route("/")
def index():
    db = get_db()
    videos = db.execute(
        "SELECT v.*, u.username AS uploader_name"
        " FROM video v JOIN user u ON v.uploaded_by = u.id"
        " ORDER BY v.created_at DESC"
    ).fetchall()
    return render_template("videos/index.html", videos=videos)


@bp.route("/videos/upload", methods=("GET", "POST"))
@login_required
def upload():
    if request.method == "POST":
        title = request.form["title"]
        description = request.form.get("description", "")
        transcript = request.form.get("transcript", "")
        file = request.files.get("video_file")
        error = None

        if not title:
            error = "タイトルを入力してください。"
        elif not file or file.filename == "":
            error = "動画ファイルを選択してください。"
        elif not allowed_file(file.filename):
            error = "対応していないファイル形式です。"

        if error is None:
            filename = secure_filename(file.filename)
            stored_name = f"{os.urandom(8).hex()}_{filename}"
            file.save(os.path.join(current_app.config["UPLOAD_FOLDER"], stored_name))

            db = get_db()
            db.execute(
                "INSERT INTO video (title, description, filename, transcript, uploaded_by)"
                " VALUES (?, ?, ?, ?, ?)",
                (title, description, stored_name, transcript, g.user["id"]),
            )
            db.commit()
            flash("動画をアップロードしました。")
            return redirect(url_for("videos.index"))

        flash(error)

    return render_template("videos/upload.html")


def get_video_or_404(video_id):
    db = get_db()
    video = db.execute(
        "SELECT v.*, u.username AS uploader_name"
        " FROM video v JOIN user u ON v.uploaded_by = u.id"
        " WHERE v.id = ?",
        (video_id,),
    ).fetchone()
    if video is None:
        abort(404, f"動画 id {video_id} は存在しません。")
    return video


@bp.route("/videos/<int:video_id>")
def detail(video_id):
    db = get_db()
    video = get_video_or_404(video_id)
    summary = db.execute(
        "SELECT * FROM video_summary WHERE video_id = ?", (video_id,)
    ).fetchone()
    quiz = db.execute(
        "SELECT * FROM quiz WHERE video_id = ?", (video_id,)
    ).fetchone()
    questions = []
    if quiz:
        questions = db.execute(
            "SELECT * FROM quiz_question WHERE quiz_id = ?", (quiz["id"],)
        ).fetchall()
    return render_template(
        "videos/detail.html",
        video=video,
        summary=summary,
        quiz=quiz,
        questions=questions,
    )


@bp.route("/videos/<int:video_id>/file")
def stream(video_id):
    video = get_video_or_404(video_id)
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], video["filename"])


@bp.route("/videos/<int:video_id>/process", methods=("POST",))
@login_required
def process(video_id):
    db = get_db()
    video = get_video_or_404(video_id)

    source_text = (video["transcript"] or video["description"] or "").strip()
    if not source_text:
        flash("要約・クイズ生成には、説明文または書き起こしテキストが必要です。")
        return redirect(url_for("videos.detail", video_id=video_id))

    db.execute("UPDATE video SET status = 'processing' WHERE id = ?", (video_id,))
    db.commit()

    try:
        result = ai_client.generate_summary_and_quiz(source_text)
    except ai_client.AIClientError as e:
        db.execute("UPDATE video SET status = 'failed' WHERE id = ?", (video_id,))
        db.commit()
        flash(f"AI処理に失敗しました: {e}")
        return redirect(url_for("videos.detail", video_id=video_id))

    key_points = "\n".join(result.get("key_points", []))
    db.execute(
        "INSERT INTO video_summary (video_id, summary, key_points)"
        " VALUES (?, ?, ?)"
        " ON CONFLICT(video_id) DO UPDATE SET summary = excluded.summary,"
        " key_points = excluded.key_points, created_at = CURRENT_TIMESTAMP",
        (video_id, result["summary"], key_points),
    )

    existing_quiz = db.execute(
        "SELECT id FROM quiz WHERE video_id = ?", (video_id,)
    ).fetchone()
    if existing_quiz:
        db.execute("DELETE FROM quiz_question WHERE quiz_id = ?", (existing_quiz["id"],))
        quiz_id = existing_quiz["id"]
    else:
        cur = db.execute("INSERT INTO quiz (video_id) VALUES (?)", (video_id,))
        quiz_id = cur.lastrowid

    for q in result.get("quiz", []):
        db.execute(
            "INSERT INTO quiz_question"
            " (quiz_id, question, choice_a, choice_b, choice_c, choice_d, correct_choice, explanation)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                quiz_id,
                q["question"],
                q["choice_a"],
                q["choice_b"],
                q["choice_c"],
                q["choice_d"],
                q["correct_choice"],
                q.get("explanation", ""),
            ),
        )

    db.execute("UPDATE video SET status = 'completed' WHERE id = ?", (video_id,))
    db.commit()

    flash("要約とクイズを生成しました。")
    return redirect(url_for("videos.detail", video_id=video_id))


@bp.route("/videos/<int:video_id>/delete", methods=("POST",))
@login_required
def delete(video_id):
    db = get_db()
    video = get_video_or_404(video_id)
    if video["uploaded_by"] != g.user["id"] and g.user["role"] != "admin":
        abort(403)

    try:
        os.remove(os.path.join(current_app.config["UPLOAD_FOLDER"], video["filename"]))
    except OSError:
        pass

    db.execute("DELETE FROM video WHERE id = ?", (video_id,))
    db.commit()
    flash("動画を削除しました。")
    return redirect(url_for("videos.index"))
