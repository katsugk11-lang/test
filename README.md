# 社内向け eラーニングツール

研修動画の保存・視聴、外部AIによる動画要約・理解度クイズの自動生成を行う社内向けWebアプリです。
Flask（flaskrパターンのアプリケーションファクトリ構成）と SQLite で構成されています。

## 主な機能

- ユーザー登録・ログイン（セッションベース認証）
- 研修動画のアップロード・保存・視聴
- 外部AI APIと連携した動画要約・理解度クイズの自動生成
- クイズの受験・自動採点・結果表示

## ディレクトリ構成

```
app/
  __init__.py     アプリケーションファクトリ
  db.py           SQLite接続・初期化（flask init-db コマンド）
  schema.sql      テーブル定義
  auth.py         ユーザー登録・ログイン・ログアウト
  videos.py       動画アップロード・一覧・詳細・AI処理・削除
  quiz.py         クイズ受験・採点・結果表示
  ai_client.py    外部AI連携クライアント（OpenAI互換API / モック）
  templates/      Jinja2テンプレート
  static/         CSS
tests/            pytestテストスイート
wsgi.py           アプリ起動エントリポイント
```

## セットアップ

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# .env を編集し、AI_PROVIDER / AI_API_KEY 等を設定

flask init-db     # データベースを初期化
flask run
```

`http://127.0.0.1:5000/` にアクセスすると動画一覧画面が表示されます。

## 外部AI連携の設定

`.env` の `AI_PROVIDER` で連携先を切り替えます。

| AI_PROVIDER        | 説明                                                                 |
|---------------------|----------------------------------------------------------------------|
| `mock`（既定値）    | 外部APIを呼び出さず、開発・テスト用のサンプル要約/クイズを返す        |
| `openai_compatible` | OpenAI互換の Chat Completions API（`/v1/chat/completions`）を呼び出す |

`AI_API_KEY` が未設定の場合は自動的に `mock` 動作にフォールバックします。
`AI_API_BASE` を変更することで、OpenAI以外にも OpenAI互換のAPIエンドポイント
（Azure OpenAI、自社ホストのLLMサーバー等）に接続できます。

動画アップロード時に入力した「書き起こし（トランスクリプト）」または「説明文」を元に、
動画詳細ページの「AIで要約・クイズを生成する」ボタンから要約とクイズ（4問）を生成します。

## テスト

```bash
pytest
```

テストはすべて `AI_PROVIDER=mock` で実行され、外部APIへの通信は発生しません。

## データベーススキーマ概要

- `user`: ユーザー情報
- `video`: 動画メタデータ（タイトル、説明、保存ファイル名、書き起こし、ステータス）
- `video_summary`: AIが生成した要約・重要ポイント
- `quiz` / `quiz_question`: AIが生成したクイズと設問
- `quiz_attempt` / `quiz_answer`: ユーザーのクイズ受験結果・回答履歴

## 注意事項

- 動画ファイルは `instance/uploads/` にローカル保存されます（本番運用時はS3等の外部ストレージへの
  切り替えを推奨します）。
- 動画の音声からのテキスト化（文字起こし）は含まれていません。AIによる要約・クイズ生成の精度を
  上げるには、アップロード時に書き起こしテキストを入力してください。
