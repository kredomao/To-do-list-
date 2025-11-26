# Render デプロイ手順

## 📋 事前準備

### 1. GitHubアカウントの準備
- [GitHub](https://github.com) にアカウントを作成（まだの場合）

### 2. Gitリポジトリの初期化
プロジェクトフォルダで以下を実行：

```bash
git init
git add .
git commit -m "Initial commit"
```

### 3. GitHubにリポジトリを作成
1. GitHubにログイン
2. 右上の「+」→「New repository」
3. リポジトリ名を入力（例: `todo-list-app`）
4. 「Create repository」をクリック

### 4. ローカルリポジトリをGitHubにプッシュ
```bash
git remote add origin https://github.com/あなたのユーザー名/todo-list-app.git
git branch -M main
git push -u origin main
```

---

## 🚀 Renderでのデプロイ

### Step 1: Renderアカウント作成
1. [Render](https://render.com) にアクセス
2. 「Get Started for Free」をクリック
3. 「Sign up with GitHub」を選択してGitHubアカウントでログイン
4. GitHubの認証を許可

### Step 2: 新しいWebサービスを作成
1. Renderダッシュボードで「New +」→「Web Service」をクリック
2. GitHubリポジトリを選択（先ほど作成したリポジトリ）
3. 「Connect」をクリック

### Step 3: サービス設定
以下の設定を入力：

| 項目 | 値 |
|------|-----|
| **Name** | `todo-list-app`（任意の名前） |
| **Region** | `Singapore`（最寄りのリージョン） |
| **Branch** | `main` |
| **Root Directory** | （空欄のまま） |
| **Runtime** | `Python 3` |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `gunicorn app:app` |

### Step 4: 環境変数の設定（重要！）

1. 「Environment Variables」セクションを開く
2. 「Add Environment Variable」をクリック
3. 以下の設定を追加：

   **Key:** `GOOGLE_CREDENTIALS`
   
   **Value:** `credentials.json` の内容をそのまま貼り付け
   
   **取得方法:**
   ```bash
   # ローカルで実行（PowerShell）
   Get-Content credentials.json
   ```
   
   または、テキストエディタで `credentials.json` を開いて、**すべての内容をコピー**して貼り付け

   ⚠️ **注意:** JSONの改行やスペースはそのまま保持してください

### Step 5: デプロイ開始
1. 画面下部の「Create Web Service」をクリック
2. デプロイが開始されます（数分かかります）

### Step 6: デプロイ完了の確認
1. デプロイが完了すると、URLが表示されます（例: `https://todo-list-app.onrender.com`）
2. そのURLをクリックしてアプリが動作するか確認

---

## 🔧 トラブルシューティング

### デプロイが失敗する場合

1. **Build Logを確認**
   - Renderダッシュボードの「Logs」タブを確認
   - エラーメッセージを確認

2. **環境変数の確認**
   - `GOOGLE_CREDENTIALS` が正しく設定されているか
   - JSON形式が正しいか（コピペミスがないか）

3. **requirements.txtの確認**
   - すべての依存関係が記載されているか

### アプリが起動しない場合

1. **Start Commandの確認**
   - `gunicorn app:app` が正しいか

2. **ポート設定の確認**
   - Renderは自動でポートを設定するため、コード側のポート指定は不要

---

## 📝 補足情報

### 無料プランの制限
- 15分間アクセスがないとスリープします
- 次回アクセス時に自動で起動します（30秒程度かかります）

### カスタムドメイン
- 有料プランでカスタムドメインを設定可能

### ログの確認
- Renderダッシュボードの「Logs」タブでリアルタイムログを確認可能

---

## ✅ デプロイ後の確認事項

- [ ] アプリが正常に表示される
- [ ] Todoの追加ができる
- [ ] Todoの編集ができる
- [ ] Todoの削除ができる
- [ ] Googleスプレッドシートにデータが保存される

---

問題が発生した場合は、Renderのログを確認して、エラーメッセージを教えてください！

