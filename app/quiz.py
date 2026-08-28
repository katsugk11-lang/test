from flask import Blueprint, abort, g, redirect, render_template, request, url_for

from .auth import login_required
from .db import get_db

bp = Blueprint("quiz", __name__, url_prefix="/quiz")


def get_quiz_or_404(quiz_id):
    db = get_db()
    quiz = db.execute(
        "SELECT q.*, v.title AS video_title FROM quiz q"
        " JOIN video v ON q.video_id = v.id WHERE q.id = ?",
        (quiz_id,),
    ).fetchone()
    if quiz is None:
        abort(404, f"クイズ id {quiz_id} は存在しません。")
    return quiz


@bp.route("/<int:quiz_id>", methods=("GET", "POST"))
@login_required
def take(quiz_id):
    db = get_db()
    quiz = get_quiz_or_404(quiz_id)
    questions = db.execute(
        "SELECT * FROM quiz_question WHERE quiz_id = ?", (quiz_id,)
    ).fetchall()

    if request.method == "POST":
        score = 0
        answers = []
        for question in questions:
            selected = request.form.get(f"question_{question['id']}")
            is_correct = selected == question["correct_choice"]
            if is_correct:
                score += 1
            answers.append((question["id"], selected, is_correct))

        cur = db.execute(
            "INSERT INTO quiz_attempt (quiz_id, user_id, score, total) VALUES (?, ?, ?, ?)",
            (quiz_id, g.user["id"], score, len(questions)),
        )
        attempt_id = cur.lastrowid
        for question_id, selected, is_correct in answers:
            db.execute(
                "INSERT INTO quiz_answer (attempt_id, question_id, selected_choice, is_correct)"
                " VALUES (?, ?, ?, ?)",
                (attempt_id, question_id, selected, int(is_correct)),
            )
        db.commit()
        return redirect(url_for("quiz.result", attempt_id=attempt_id))

    return render_template("quiz/take.html", quiz=quiz, questions=questions)


@bp.route("/result/<int:attempt_id>")
@login_required
def result(attempt_id):
    db = get_db()
    attempt = db.execute(
        "SELECT a.*, q.video_id, v.title AS video_title FROM quiz_attempt a"
        " JOIN quiz q ON a.quiz_id = q.id"
        " JOIN video v ON q.video_id = v.id"
        " WHERE a.id = ?",
        (attempt_id,),
    ).fetchone()
    if attempt is None or attempt["user_id"] != g.user["id"]:
        abort(404)

    answers = db.execute(
        "SELECT ans.*, qq.question, qq.choice_a, qq.choice_b, qq.choice_c, qq.choice_d,"
        " qq.correct_choice, qq.explanation"
        " FROM quiz_answer ans JOIN quiz_question qq ON ans.question_id = qq.id"
        " WHERE ans.attempt_id = ?",
        (attempt_id,),
    ).fetchall()

    return render_template("quiz/result.html", attempt=attempt, answers=answers)
