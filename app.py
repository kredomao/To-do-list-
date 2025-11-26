from flask import Flask, render_template, request, redirect, url_for, jsonify
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, date
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
        expected_headers = ['id', 'title', 'description', 'deadline', 'completed', 'priority']
        
        # ヘッダーが正しく設定されていない場合
        if len(first_row) < len(expected_headers) or first_row[:len(expected_headers)] != expected_headers:
            # ヘッダーを設定
            sheet.update('A1:F1', [expected_headers])
            print("ヘッダーを設定しました")
    except Exception as e:
        # エラーが発生した場合もヘッダーを設定
        sheet.update('A1:F1', [['id', 'title', 'description', 'deadline', 'completed', 'priority']])
        print(f"ヘッダー設定中にエラー: {e}")


# アプリ起動時にヘッダーを確認
ensure_headers()


def calculate_days_until_deadline(deadline_str):
    """期日までの日数を計算"""
    if not deadline_str:
        return None
    try:
        deadline = datetime.strptime(deadline_str, '%Y-%m-%d').date()
        today = date.today()
        days = (deadline - today).days
        return days
    except:
        return None


def get_priority(days):
    """期日までの日数に基づいて重要度を判定"""
    if days is None:
        return 'normal'  # 期日未設定
    if days < 0:
        return 'urgent'  # 期限切れ
    elif days <= 3:
        return 'urgent'  # 締め切り間近（3日以内）
    elif days <= 7:
        return 'important'  # 急ぎでないけど重要（4-7日）
    else:
        return 'normal'  # まだ余裕あり（8日以上）


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
        
        # 各Todoに期日までの日数と重要度を追加
        for todo in todos:
            days = calculate_days_until_deadline(todo.get('deadline', ''))
            todo['days_until'] = days
            todo['priority'] = get_priority(days)
            # completedが文字列の場合は変換
            completed = todo.get('completed', '').lower()
            todo['is_completed'] = completed in ['true', '1', 'yes', '完了']
        
        # 重要度順にソート（urgent > important > normal）
        priority_order = {'urgent': 0, 'important': 1, 'normal': 2}
        todos.sort(key=lambda x: (priority_order.get(x.get('priority', 'normal'), 2), 
                                  x.get('days_until') if x.get('days_until') is not None else 999))
        
    except (IndexError, Exception) as e:
        # エラーが発生した場合は空のリストを返す
        print(f"エラー: {e}")
        todos = []
    
    # アラート用のTodo（3日以内）を取得
    alert_todos = [todo for todo in todos if todo.get('days_until') is not None 
                   and 0 <= todo.get('days_until') <= 3 and not todo.get('is_completed')]
    
    return render_template("index.html", todos=todos, alert_todos=alert_todos)


@app.route("/add", methods=["POST"])
def add():
    title = request.form.get("title", "").strip()
    desc = request.form.get("desc", "").strip()
    deadline = request.form.get("deadline", "").strip()
    priority = request.form.get("priority", "").strip()
    
    if not title:
        return redirect(url_for("index"))
    
    # 重要度が選択されていない場合は自動計算
    if not priority:
        days = calculate_days_until_deadline(deadline)
        priority = get_priority(days)
    
    # 重要度の値が正しいか確認
    if priority not in ['urgent', 'important', 'normal']:
        days = calculate_days_until_deadline(deadline)
        priority = get_priority(days)
    
    next_id = get_next_id()
    # 新規追加時は未完了
    sheet.append_row([next_id, title, desc, deadline, 'FALSE', priority])
    return redirect(url_for("index"))


@app.route("/edit/<int:todo_id>", methods=["GET", "POST"])
def edit(todo_id):
    try:
        if request.method == "POST":
            title = request.form.get("title", "").strip()
            desc = request.form.get("desc", "").strip()
            deadline = request.form.get("deadline", "").strip()
            priority = request.form.get("priority", "").strip()
            
            # 該当する行を検索して更新
            todos = sheet.get_all_records()
            for i, todo in enumerate(todos, start=2):  # 2行目から開始（1行目はヘッダー）
                if str(todo.get('id', '')) == str(todo_id):
                    # 重要度が選択されていない場合は自動計算
                    if not priority or priority not in ['urgent', 'important', 'normal']:
                        days = calculate_days_until_deadline(deadline)
                        priority = get_priority(days)
                    # 既存の完了状態を保持
                    completed = todo.get('completed', 'FALSE')
                    
                    sheet.update_cell(i, 2, title)      # title列
                    sheet.update_cell(i, 3, desc)        # description列
                    sheet.update_cell(i, 4, deadline)    # deadline列
                    sheet.update_cell(i, 5, completed)   # completed列（保持）
                    sheet.update_cell(i, 6, priority)    # priority列
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


@app.route("/toggle_complete/<int:todo_id>", methods=["POST"])
def toggle_complete(todo_id):
    """完了状態を切り替え"""
    try:
        todos = sheet.get_all_records()
        for i, todo in enumerate(todos, start=2):
            if str(todo.get('id', '')) == str(todo_id):
                # 現在の完了状態を取得
                completed = todo.get('completed', '').lower()
                # 切り替え
                new_status = 'FALSE' if completed in ['true', '1', 'yes', '完了'] else 'TRUE'
                sheet.update_cell(i, 5, new_status)  # completed列
                break
    except (IndexError, Exception) as e:
        print(f"完了状態切り替えエラー: {e}")
    
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

