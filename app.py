from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, date
import os
import json

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # フラッシュメッセージ用

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
        expected_headers = ['id', 'title', 'description', 'deadline', 'completed', 'priority', 
                           'start_date', 'start_time', 'end_time', 'category', 'type']
        
        # ヘッダーが正しく設定されていない場合
        if len(first_row) < len(expected_headers) or first_row[:len(expected_headers)] != expected_headers:
            # ヘッダーを設定（既存の列を保持しつつ新しい列を追加）
            current_headers = first_row if first_row else []
            # 不足している列を追加
            for i, header in enumerate(expected_headers):
                if i >= len(current_headers) or current_headers[i] != header:
                    # 列を追加または更新
                    if i < len(current_headers):
                        sheet.update_cell(1, i + 1, header)
                    else:
                        # 新しい列を追加
                        col_letter = chr(65 + i)  # A, B, C...
                        sheet.update(f'{col_letter}1', [[header]])
            print("ヘッダーを設定しました")
    except Exception as e:
        # エラーが発生した場合もヘッダーを設定
        expected_headers = [['id', 'title', 'description', 'deadline', 'completed', 'priority', 
                            'start_date', 'start_time', 'end_time', 'category', 'type']]
        sheet.update('A1:K1', expected_headers)
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
        all_items = sheet.get_all_records()
        # idが空の場合は除外
        all_items = [item for item in all_items if item.get('id')]
        
        # Todoと予定を分離
        todos = []
        events = []
        
        for item in all_items:
            item_type = item.get('type', 'todo')
            if item_type == 'event':
                events.append(item)
            else:
                todos.append(item)
        
        # 各Todoに期日までの日数と重要度を追加
        for todo in todos:
            days = calculate_days_until_deadline(todo.get('deadline', ''))
            todo['days_until'] = days
            # 重要度が設定されていない場合は自動計算
            if not todo.get('priority'):
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
        events = []
    
    # アラート用のTodo（3日以内）を取得（予定は除外）
    alert_todos = [todo for todo in todos if todo.get('days_until') is not None 
                   and 0 <= todo.get('days_until') <= 3 and not todo.get('is_completed')]
    
    # カレンダー用：日付ごとにTodoと予定をグループ化
    todos_by_date = {}
    # Todoを追加
    for todo in todos:
        deadline = todo.get('deadline', '')
        if deadline:
            if deadline not in todos_by_date:
                todos_by_date[deadline] = []
            todos_by_date[deadline].append(todo)
    # 予定を追加
    for event in events:
        start_date = event.get('start_date', '') or event.get('deadline', '')
        if start_date:
            if start_date not in todos_by_date:
                todos_by_date[start_date] = []
            todos_by_date[start_date].append(event)
    
    # URLパラメータからビューを取得
    view = request.args.get('view', 'list')
    
    return render_template("index.html", todos=todos, alert_todos=alert_todos, 
                         todos_by_date=todos_by_date, current_view=view)


@app.route("/add", methods=["POST"])
def add():
    title = request.form.get("title", "").strip()
    desc = request.form.get("desc", "").strip()
    deadline = request.form.get("deadline", "").strip()
    priority = request.form.get("priority", "").strip()
    start_date = request.form.get("start_date", "").strip()
    start_time = request.form.get("start_time", "").strip()
    end_time = request.form.get("end_time", "").strip()
    category = request.form.get("category", "").strip()
    item_type = request.form.get("type", "todo").strip()  # 'todo' or 'event'
    
    if not title:
        return redirect(url_for("index"))
    
    next_id = get_next_id()
    
    # 予定の場合
    if item_type == 'event':
        # 予定の場合はstart_dateをdeadlineとしても使用（カレンダー表示用）
        if not deadline and start_date:
            deadline = start_date
        if not priority:
            priority = 'normal'
    else:
        # Todoの場合
        # 重要度が選択されていない場合は自動計算
        if not priority:
            days = calculate_days_until_deadline(deadline)
            priority = get_priority(days)
        
        # 重要度の値が正しいか確認
        if priority not in ['urgent', 'important', 'normal']:
            days = calculate_days_until_deadline(deadline)
            priority = get_priority(days)
    
    # 新規追加時は未完了
    # [id, title, description, deadline, completed, priority, start_date, start_time, end_time, category, type]
    sheet.append_row([next_id, title, desc, deadline, 'FALSE', priority, 
                     start_date, start_time, end_time, category, item_type])
    
    # 成功メッセージをフラッシュ（JavaScriptで表示）
    if item_type == 'event':
        flash('予定を追加できました！', 'success')
    else:
        flash('Todoを追加できました！', 'success')
    
    # カレンダーから追加した場合はカレンダービューを維持
    view = request.form.get("view", "list")
    if view == "calendar":
        return redirect(url_for("index") + "?view=calendar")
    
    return redirect(url_for("index"))


@app.route("/edit/<int:todo_id>", methods=["GET", "POST"])
def edit(todo_id):
    try:
        if request.method == "POST":
            title = request.form.get("title", "").strip()
            desc = request.form.get("desc", "").strip()
            deadline = request.form.get("deadline", "").strip()
            priority = request.form.get("priority", "").strip()
            start_date = request.form.get("start_date", "").strip()
            start_time = request.form.get("start_time", "").strip()
            end_time = request.form.get("end_time", "").strip()
            category = request.form.get("category", "").strip()
            item_type = request.form.get("type", "todo").strip()
            
            # 該当する行を検索して更新
            todos = sheet.get_all_records()
            for i, todo in enumerate(todos, start=2):  # 2行目から開始（1行目はヘッダー）
                if str(todo.get('id', '')) == str(todo_id):
                    # 予定の場合
                    if item_type == 'event':
                        if not deadline and start_date:
                            deadline = start_date
                        if not priority:
                            priority = 'normal'
                    else:
                        # Todoの場合：重要度が選択されていない場合は自動計算
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
                    sheet.update_cell(i, 7, start_date)  # start_date列
                    sheet.update_cell(i, 8, start_time) # start_time列
                    sheet.update_cell(i, 9, end_time)   # end_time列
                    sheet.update_cell(i, 10, category)  # category列
                    sheet.update_cell(i, 11, item_type) # type列
                    break
            
            flash('更新しました！', 'success')
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
                flash('削除しました！', 'success')
                break
    except (IndexError, Exception) as e:
        print(f"削除エラー: {e}")
        flash('削除に失敗しました', 'error')
    
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(port=5000, debug=True)

