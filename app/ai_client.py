"""外部AIサービスと連携し、動画の要約・クイズを生成するモジュール。

OpenAI互換のChat Completions APIをデフォルトで利用する。
AI_API_KEY が未設定の場合は開発・テスト用のモック応答を返す。
"""
import json

import requests
from flask import current_app

SUMMARY_QUIZ_PROMPT = """あなたは社内研修動画の教材作成アシスタントです。
以下は研修動画の書き起こし（トランスクリプト）または説明文です。
これをもとに、次のJSON形式で日本語で出力してください。JSON以外の文章は一切出力しないでください。

{{
  "summary": "動画全体の要約（300文字程度）",
  "key_points": ["重要ポイント1", "重要ポイント2"],
  "quiz": [
    {{
      "question": "問題文",
      "choice_a": "選択肢A",
      "choice_b": "選択肢B",
      "choice_c": "選択肢C",
      "choice_d": "選択肢D",
      "correct_choice": "a",
      "explanation": "正解の理由"
    }}
  ]
}}

quizは{num_questions}問作成してください。correct_choiceは "a"〜"d" のいずれかです。

--- 動画テキスト ---
{content}
"""


class AIClientError(Exception):
    """外部AI呼び出しに失敗した場合の例外。"""


def _config():
    return {
        "provider": current_app.config.get("AI_PROVIDER", "mock"),
        "base_url": current_app.config.get("AI_API_BASE"),
        "api_key": current_app.config.get("AI_API_KEY"),
        "model": current_app.config.get("AI_MODEL"),
    }


def generate_summary_and_quiz(text, num_questions=4):
    """動画テキストから要約とクイズをAIに生成させる。

    戻り値: {"summary": str, "key_points": [str], "quiz": [dict]}
    """
    cfg = _config()
    provider = cfg["provider"]

    if provider == "mock" or not cfg["api_key"]:
        return _mock_response(text, num_questions)
    if provider in ("openai", "openai_compatible"):
        return _call_openai_compatible(cfg, text, num_questions)

    raise AIClientError(f"未対応のAIプロバイダです: {provider}")


def _call_openai_compatible(cfg, text, num_questions):
    url = f"{cfg['base_url'].rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {cfg['api_key']}",
        "Content-Type": "application/json",
    }
    prompt = SUMMARY_QUIZ_PROMPT.format(
        content=text[:12000], num_questions=num_questions
    )
    payload = {
        "model": cfg["model"],
        "messages": [
            {
                "role": "system",
                "content": "あなたは有能な教材作成アシスタントです。必ずJSONのみを返してください。",
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=120)
        resp.raise_for_status()
    except requests.RequestException as e:
        raise AIClientError(f"外部AI APIへの接続に失敗しました: {e}") from e

    data = resp.json()
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as e:
        raise AIClientError("外部AI APIのレスポンス形式が不正です。") from e

    return _parse_ai_json(content)


def _parse_ai_json(content):
    content = content.strip()
    if content.startswith("```"):
        content = content.strip("`")
        if content.startswith("json"):
            content = content[4:]

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as e:
        raise AIClientError(f"AIの応答をJSONとして解析できませんでした: {e}") from e

    if "summary" not in parsed or "quiz" not in parsed:
        raise AIClientError("AIの応答に必要なフィールドがありません。")

    return parsed


def _mock_response(text, num_questions):
    snippet = (text or "").strip()[:200] or "(説明文なし)"
    quiz = [
        {
            "question": f"[サンプル問題 {i}] この動画の主なテーマは何ですか？",
            "choice_a": "選択肢A",
            "choice_b": "選択肢B",
            "choice_c": "選択肢C",
            "choice_d": "選択肢D",
            "correct_choice": "a",
            "explanation": "AI_API_KEY が未設定のため、サンプル問題を表示しています。",
        }
        for i in range(1, num_questions + 1)
    ]
    return {
        "summary": f"(モック要約) {snippet}",
        "key_points": ["AI_API_KEY が設定されていないため、モック応答です。"],
        "quiz": quiz,
    }
