import os

from flask import Flask


def create_app(test_config=None):
    """アプリケーションファクトリ。"""
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("FLASK_SECRET_KEY", "dev"),
        DATABASE=os.path.join(app.instance_path, "elearning.sqlite"),
        UPLOAD_FOLDER=os.path.join(app.instance_path, "uploads"),
        MAX_CONTENT_LENGTH=500 * 1024 * 1024,  # 500MB
        ALLOWED_VIDEO_EXTENSIONS={"mp4", "mov", "avi", "mkv", "webm"},
        AI_PROVIDER=os.environ.get("AI_PROVIDER", "mock"),
        AI_API_BASE=os.environ.get("AI_API_BASE", "https://api.openai.com/v1"),
        AI_API_KEY=os.environ.get("AI_API_KEY", ""),
        AI_MODEL=os.environ.get("AI_MODEL", "gpt-4o-mini"),
    )

    if test_config is None:
        app.config.from_pyfile("config.py", silent=True)
    else:
        app.config.update(test_config)

    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    from . import db

    db.init_app(app)

    from . import auth

    app.register_blueprint(auth.bp)

    from . import videos

    app.register_blueprint(videos.bp)

    from . import quiz

    app.register_blueprint(quiz.bp)

    return app
