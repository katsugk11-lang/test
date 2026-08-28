from unittest.mock import patch

import pytest

from app import ai_client


def test_mock_response_shape(app):
    with app.app_context():
        app.config["AI_PROVIDER"] = "mock"
        result = ai_client.generate_summary_and_quiz("テストテキストです。")

    assert "summary" in result
    assert "quiz" in result
    assert len(result["quiz"]) == 4
    for q in result["quiz"]:
        assert q["correct_choice"] in ("a", "b", "c", "d")
        assert q["question"]


def test_unsupported_provider_raises(app):
    with app.app_context():
        app.config["AI_PROVIDER"] = "unknown"
        app.config["AI_API_KEY"] = "dummy"
        with pytest.raises(ai_client.AIClientError):
            ai_client.generate_summary_and_quiz("テキスト")


def test_openai_compatible_success(app):
    fake_content = (
        '{"summary": "要約です", "key_points": ["ポイント1"], '
        '"quiz": [{"question": "Q1", "choice_a": "A", "choice_b": "B", '
        '"choice_c": "C", "choice_d": "D", "correct_choice": "a", "explanation": "解説"}]}'
    )

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content": fake_content}}]}

    with app.app_context():
        app.config["AI_PROVIDER"] = "openai_compatible"
        app.config["AI_API_KEY"] = "dummy-key"

        with patch("app.ai_client.requests.post", return_value=FakeResponse()):
            result = ai_client.generate_summary_and_quiz("テキスト")

    assert result["summary"] == "要約です"
    assert result["quiz"][0]["correct_choice"] == "a"


def test_openai_compatible_connection_error(app):
    import requests

    with app.app_context():
        app.config["AI_PROVIDER"] = "openai_compatible"
        app.config["AI_API_KEY"] = "dummy-key"

        with patch(
            "app.ai_client.requests.post",
            side_effect=requests.RequestException("boom"),
        ):
            with pytest.raises(ai_client.AIClientError):
                ai_client.generate_summary_and_quiz("テキスト")
