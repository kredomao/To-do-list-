# Todo List アプリ

Googleスプレッドシートに接続するTodoリストアプリケーションです。

## 機能

- ✅ Todoの追加
- ✏️ Todoの編集
- 🗑️ Todoの削除
- 📋 Todoの一覧表示

## セットアップ

### 1. 必要なライブラリのインストール

```bash
pip install -r requirements.txt
```

### 2. Googleスプレッドシートの準備

1. Googleスプレッドシート「To do list」を作成
2. 1行目に以下のヘッダーを設定：
   - `id` | `title` | `description` | `deadline`
3. Google Cloud Consoleでサービスアカウントを作成
4. サービスアカウントのJSONキーをダウンロード
5. `credentials.json`としてプロジェクト直下に配置

### 3. スプレッドシートの共有設定

**重要**: スプレッドシートの「共有」から、サービスアカウントのメールアドレス（`to-do-list@to-do-list-479408.iam.gserviceaccount.com`）を**編集者**として追加してください。

### 4. アプリの起動

```bash
python app.py
```

ブラウザで `http://localhost:5000` にアクセスしてください。

## デプロイ（Render使用時）

1. GitHubにプロジェクトをプッシュ
2. RenderでNew Web Serviceを作成
3. 設定：
   - **Runtime**: Python
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
4. 環境変数に`GOOGLE_CREDENTIALS`を設定（credentials.jsonの内容をJSON形式で）

## 注意事項

- `credentials.json`は機密情報のため、Gitにコミットしないでください
- `.gitignore`に`credentials.json`を追加することを推奨します

