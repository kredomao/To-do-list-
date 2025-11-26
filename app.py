from flask import Flask, render_template, request, redirect, url_for
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import os
import json

app = Flask(__name__)

# ===== Google sheets authorize ==========
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

# Render環境変数から認証情報を取得、なければローカルファイルから
if os.getenv("GOOGLE_CREDENTIALS"):
    # Render環境: 環境変数からJSONを読み込む
    creds_info = json.loads(os.getenv("GOOGLE_CREDENTIALS"))
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_info, scope)
else:
    # ローカル環境: ファイルから読み込む
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)

client = gspread.authorize(creds)

# スプレッドシートIDで開く（より確実）
SPREADSHEET_ID = "1LVBUTr7OrMYxsrwL6hU2g0flhi5EjLg0DugqL-g9ZyA"
spreadsheet = client.open_by_key(SPREADSHEET_ID)
sheet = spreadsheet.sheet1


def ensure_headers():
    """ヘッダー行が正しく設定されているか確認し、設定されていなければ追加"""
    try:
        # 1行目を取得
        first_row = sheet.row_values(1)
        expected_headers = ['id', 'title', 'description', 'deadline']
        
        # ヘッダーが正しく設定されていない場合
        if first_row != expected_headers:
            # ヘッダーを設定
            sheet.update('A1:D1', [expected_headers])
            print("ヘッダーを設定しました")
    except Exception as e:
        # エラーが発生した場合もヘッダーを設定
        sheet.update('A1:D1', [['id', 'title', 'description', 'deadline']])
        print(f"ヘッダー設定中にエラー: {e}")


# アプリ起動時にヘッダーを確認
ensure_headers()


def get_next_id():
    """次のIDを取得（既存の最大ID + 1）"""
    try:
        todos = sheet.get_all_records()
        if not todos:
            return 1
        ids = [int(todo.get('id', 0)) for todo in todos if todo.get('id')]
        return max(ids) + 1 if ids else 1
    except (IndexError, Exception):
        return 1


@app.route("/")
def index():
    try:
        todos = sheet.get_all_records()
        # idが空の場合は除外
        todos = [todo for todo in todos if todo.get('id')]
    except (IndexError, Exception) as e:
        # エラーが発生した場合は空のリストを返す
        print(f"エラー: {e}")
        todos = []
    return render_template("index.html", todos=todos)


@app.route("/add", methods=["POST"])
def add():
    title = request.form.get("title", "").strip()
    desc = request.form.get("desc", "").strip()
    deadline = request.form.get("deadline", "").strip()
    
    if not title:
        return redirect(url_for("index"))
    
    next_id = get_next_id()
    sheet.append_row([next_id, title, desc, deadline])
    return redirect(url_for("index"))


@app.route("/edit/<int:todo_id>", methods=["GET", "POST"])
def edit(todo_id):
    try:
        if request.method == "POST":
            title = request.form.get("title", "").strip()
            desc = request.form.get("desc", "").strip()
            deadline = request.form.get("deadline", "").strip()
            
            # 該当する行を検索して更新
            todos = sheet.get_all_records()
            for i, todo in enumerate(todos, start=2):  # 2行目から開始（1行目はヘッダー）
                if str(todo.get('id', '')) == str(todo_id):
                    sheet.update_cell(i, 2, title)      # title列
                    sheet.update_cell(i, 3, desc)        # description列
                    sheet.update_cell(i, 4, deadline)    # deadline列
                    break
            
            return redirect(url_for("index"))
        
        # GETリクエスト: 編集フォームを表示
        todos = sheet.get_all_records()
        todo = next((t for t in todos if str(t.get('id', '')) == str(todo_id)), None)
        
        if not todo:
            return redirect(url_for("index"))
        
        return render_template("edit.html", todo=todo)
    except (IndexError, Exception) as e:
        print(f"編集エラー: {e}")
        return redirect(url_for("index"))


@app.route("/delete/<int:todo_id>", methods=["POST"])
def delete(todo_id):
    try:
        # 該当する行を検索して削除
        todos = sheet.get_all_records()
        for i, todo in enumerate(todos, start=2):  # 2行目から開始
            if str(todo.get('id', '')) == str(todo_id):
                sheet.delete_rows(i)
                break
    except (IndexError, Exception) as e:
        print(f"削除エラー: {e}")
    
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(port=5000, debug=True)

