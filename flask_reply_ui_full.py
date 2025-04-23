from flask import Flask, render_template_string, request, redirect, url_for, send_file
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin, current_user
import json, os, io, csv

app = Flask(__name__)
app.secret_key = "secret_key"

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# 🔐 ダミーユーザー（複数店舗対応）
users = {
    "admin": {"password": "adminpass", "store_ids": ["store001", "store002"]}
}

class User(UserMixin):
    def __init__(self, id, store_ids):
        self.id = id
        self.store_ids = store_ids
        self.current_store = store_ids[0]

@login_manager.user_loader
def load_user(user_id):
    user = users.get(user_id)
    if user:
        return User(user_id, user["store_ids"])
    return None
DATA_FILE = "approved_replies.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

TEMPLATE = """
<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <title>返信管理</title>
  <style>
    body { font-family: sans-serif; padding: 2rem; background: #f9f9f9; }
    .card { background: white; padding: 1rem; margin-bottom: 1rem;
            box-shadow: 0 0 8px rgba(0,0,0,0.1); border-left: 6px solid #ccc; border-radius: 8px; }
    .posted { border-left-color: #28a745; }
    .deleted { display: none; }
    textarea { width: 100%; height: 100px; margin-bottom: 1rem; }
    .reply { white-space: pre-wrap; margin-bottom: 1rem; }
    .actions { margin-top: 0.5rem; }
    select { padding: 0.3rem; margin-bottom: 1rem; }
  </style>
</head>
<body>
  <h2>返信管理画面（ログイン中：{{ current_user.id }}）</h2>
  <form method="get">
    <label>表示する店舗：</label>
    <select name="store" onchange="this.form.submit()">
      {% for sid in current_user.store_ids %}
        <option value="{{ sid }}" {% if sid == selected_store %}selected{% endif %}>{{ sid }}</option>
      {% endfor %}
    </select>
    <a href="/logout">ログアウト</a> ｜ 
    <a href="/download?store={{ selected_store }}">CSV出力</a>
  </form>
  {% for i, item in replies %}
    <div class="card {% if item.posted %}posted{% endif %} {% if item.deleted %}deleted{% endif %}">
      <strong>{{ item.author }}｜⭐ {{ item.starRating }}</strong><br>
      <em>{{ item.comment }}</em><br>
      {% if edit_index == i %}
        <form method="post" action="/save/{{ i }}?store={{ selected_store }}">
          <textarea name="reply">{{ item.reply }}</textarea>
          <div class="actions">
            <button type="submit">保存</button>
            <a href="/">キャンセル</a>
          </div>
        </form>
      {% else %}
        <div class="reply">{{ item.reply }}</div>
        <div class="actions">
          <form method="post" action="/post/{{ i }}?store={{ selected_store }}" style="display:inline;">
            <button>✅ 投稿</button>
          </form>
          <form method="post" action="/delete/{{ i }}?store={{ selected_store }}" style="display:inline;">
            <button>🗑️ 削除</button>
          </form>
          <form method="post" action="/edit/{{ i }}?store={{ selected_store }}" style="display:inline;">
            <button>✏️ 編集</button>
          </form>
        </div>
      {% endif %}
    </div>
  {% endfor %}
</body>
</html>
"""

@app.route("/")
@login_required
def index():
    store = request.args.get("store") or current_user.current_store
    current_user.current_store = store
    data = load_data()
    filtered = [(i, r) for i, r in enumerate(data) if r.get("store_id") == store and not r.get("deleted")]
    return render_template_string(TEMPLATE, replies=filtered, selected_store=store, edit_index=None)
@app.route("/edit/<int:index>", methods=["POST"])
@login_required
def edit_reply(index):
    store = request.args.get("store") or current_user.current_store
    data = load_data()
    filtered = [(i, r) for i, r in enumerate(data) if r.get("store_id") == store and not r.get("deleted")]
    return render_template_string(TEMPLATE, replies=filtered, selected_store=store, edit_index=index)

@app.route("/save/<int:index>", methods=["POST"])
@login_required
def save_reply(index):
    data = load_data()
    if index < len(data):
        data[index]["reply"] = request.form["reply"]
        save_data(data)
    return redirect("/?store=" + current_user.current_store)

@app.route("/post/<int:index>", methods=["POST"])
@login_required
def post_reply(index):
    data = load_data()
    if index < len(data):
        data[index]["posted"] = True
        save_data(data)
    return redirect("/?store=" + current_user.current_store)

@app.route("/delete/<int:index>", methods=["POST"])
@login_required
def delete_reply(index):
    data = load_data()
    if index < len(data):
        data[index]["deleted"] = True
        save_data(data)
    return redirect("/?store=" + current_user.current_store)

@app.route("/download")
@login_required
def download_csv():
    store = request.args.get("store") or current_user.current_store
    data = load_data()
    filtered = [r for r in data if r.get("store_id") == store and not r.get("deleted")]

    si = io.StringIO()
    writer = csv.writer(si)
    writer.writerow(["author", "starRating", "comment", "reply", "posted"])
    for r in filtered:
        writer.writerow([r["author"], r["starRating"], r["comment"], r["reply"], r.get("posted", False)])
    
    output = io.BytesIO()
    output.write(si.getvalue().encode("utf-8-sig"))
    output.seek(0)
    return send_file(output, mimetype="text/csv", as_attachment=True, download_name="approved_replies.csv")

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        u = users.get(request.form["username"])
        if u and u["password"] == request.form["password"]:
            login_user(User(request.form["username"], u["store_ids"]))
            return redirect("/")
        error = "ログイン失敗"
    return render_template_string("""
    <h2>ログイン</h2>
    {% if error %}<p style="color:red;">{{ error }}</p>{% endif %}
    <form method="post">
      <label>ユーザー名: <input name="username"></label><br>
      <label>パスワード: <input name="password" type="password"></label><br>
      <button type="submit">ログイン</button>
    </form>
    """, error=error)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect("/login")

if __name__ == "__main__":
    app.run(port=8080)
