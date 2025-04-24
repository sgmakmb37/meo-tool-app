from flask import Flask, render_template_string, request, redirect, url_for, send_file
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin, current_user
import json, os, io, csv

app = Flask(__name__)
app.secret_key = "secret_key"

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# 🔐 ダミーユーザー
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
    u = users.get(user_id)
    return User(user_id, u["store_ids"]) if u else None

DATA_FILE = "approved_replies.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# 🔽 HTMLテンプレート
TEMPLATE = """
<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <title>返信管理</title>
  <link rel="apple-touch-icon" href="/static/icon.png">
  <link rel="icon" type="image/png" href="/static/icon.png">
  <link rel="manifest" href="/static/manifest.json">
  <meta name="theme-color" content="#5b6b8a">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    body {
      font-family: "Segoe UI", sans-serif;
      background: #f4f6f9;
      color: #1d2f4f;
      margin: 0;
      padding: 2rem;
    }

    h2 {
      color: #5b6b8a;
      text-align: center;
      margin-bottom: 1.5rem;
    }

    .top-bar {
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 1rem;
    }

    .top-controls {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 1rem;
    }

    .top-bar a {
      text-decoration: none;
      margin-left: 1rem;
      color: #5b6b8a;
      font-weight: bold;
    }

    select {
      padding: 0.5rem;
      border: 1px solid #c9d1db;
      border-radius: 6px;
      background: #fff;
      font-size: 1rem;
    }

    button {
      padding: 0.5rem 1rem;
      background: #5b6b8a;
      color: white;
      border: none;
      border-radius: 6px;
      cursor: pointer;
      font-weight: bold;
      transition: background 0.3s ease;
    }

    button:hover {
      background: #8a9bbf;
    }

    .danger-button {
      background-color: #d9534f;
    }

    .danger-button:hover {
      background-color: #c9302c;
    }

    .card {
      background: white;
      padding: 1rem;
      border-left: 5px solid #8a9bbf;
      margin-bottom: 1rem;
      border-radius: 8px;
      box-shadow: 0 3px 6px rgba(0,0,0,0.08);
      animation: fadeInUp 0.4s ease-in-out;
    }

    .posted {
      border-left-color: #28a745;
    }

    .deleted {
      display: none;
    }

    .reply {
      background: #f4f6f9;
      padding: 0.8rem;
      border-radius: 6px;
      white-space: pre-wrap;
      margin: 0.5rem 0;
      font-size: 0.95rem;
    }

    textarea {
      width: 100%;
      height: 100px;
      font-size: 1rem;
      padding: 0.5rem;
      border: 1px solid #c9d1db;
      border-radius: 6px;
      resize: vertical;
    }

    .actions button {
      margin-right: 0.5rem;
    }

    @keyframes fadeInUp {
      from { opacity: 0; transform: translateY(20px); }
      to { opacity: 1; transform: translateY(0); }
    }

    @media (max-width: 600px) {
      body {
        padding: 1rem;
      }
      .top-bar {
        flex-direction: column;
        align-items: flex-start;
        gap: 1rem;
      }
      .top-controls {
        flex-direction: column;
        align-items: flex-start;
      }
    }
  </style>
</head>
<body>
  <h2>返信管理画面（{{ current_user.id }}）</h2>

  <form method="get" class="top-bar">
    <div class="top-controls">
      <label>店舗：
        <select name="store">
          {% for sid in current_user.store_ids %}
            <option value="{{ sid }}" {% if sid == selected_store %}selected{% endif %}>{{ sid }}</option>
          {% endfor %}
        </select>
      </label>
      <label>表示：
        <select name="filter">
          <option value="all" {% if selected_filter == "all" %}selected{% endif %}>すべて</option>
          <option value="unposted" {% if selected_filter == "unposted" %}selected{% endif %}>未投稿のみ</option>
          <option value="posted" {% if selected_filter == "posted" %}selected{% endif %}>投稿済みのみ</option>
        </select>
      </label>
      <button formaction="/post_all?store={{ selected_store }}&filter={{ selected_filter }}" formmethod="post">✅ 一括投稿</button>
    </div>
    <div class="top-controls">
      <button type="button" class="danger-button" onclick="location.href='/logout'">🚪 ログアウト</button>
      <button type="button" onclick="location.href='/download?store={{ selected_store }}'">📥 CSV出力</button>
    </div>
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
    filter_mode = request.args.get("filter", "all")
    data = load_data()

    # ⭐ starRating を英語→数字に変換
    rating_map = {"ONE": "1", "TWO": "2", "THREE": "3", "FOUR": "4", "FIVE": "5"}
    for r in data:
        if r.get("starRating") in rating_map:
            r["starRating"] = rating_map[r["starRating"]]

    # ✅ フィルター処理（未投稿、投稿済みなど）
    filtered = [
        (i, r) for i, r in enumerate(data)
        if r.get("store_id") == store and not r.get("deleted")
        and (
            filter_mode == "all"
            or (filter_mode == "unposted" and not r.get("posted"))
            or (filter_mode == "posted" and r.get("posted"))
        )
    ]

    # ✅ 新着順（データの末尾が新しいと仮定）
    filtered = list(reversed(filtered))

    return render_template_string(
        TEMPLATE,
        replies=filtered,
        selected_store=store,
        selected_filter=filter_mode,
        edit_index=None
    )

@app.route("/edit/<int:index>", methods=["POST"])
@login_required
def edit_reply(index):
    store = request.args.get("store") or current_user.current_store
    filter_mode = request.args.get("filter", "all")
    data = load_data()
    filtered = [(i, r) for i, r in enumerate(data) if r.get("store_id") == store and not r.get("deleted")]
    return render_template_string(TEMPLATE, replies=filtered, selected_store=store, selected_filter=filter_mode, edit_index=index)

@app.route("/save/<int:index>", methods=["POST"])
@login_required
def save_reply(index):
    data = load_data()
    if index < len(data):
        data[index]["reply"] = request.form["reply"]
        save_data(data)
    return redirect(f"/?store={current_user.current_store}")

@app.route("/post/<int:index>", methods=["POST"])
@login_required
def post_reply(index):
    data = load_data()
    if index < len(data):
        data[index]["posted"] = True
        save_data(data)
    return redirect(f"/?store={current_user.current_store}")

@app.route("/delete/<int:index>", methods=["POST"])
@login_required
def delete_reply(index):
    data = load_data()
    if index < len(data):
        data[index]["deleted"] = True
        save_data(data)
    return redirect(f"/?store={current_user.current_store}")

@app.route("/post_all", methods=["POST"])
@login_required
def post_all():
    store = request.args.get("store") or current_user.current_store
    filter_mode = request.args.get("filter", "all")
    data = load_data()
    for r in data:
        if r.get("store_id") == store and not r.get("deleted"):
            r["posted"] = True
    save_data(data)
    return redirect(f"/?store={store}&filter={filter_mode}")

@app.route("/refresh", methods=["POST"])
@login_required
def refresh_reviews():
    store = request.args.get("store") or current_user.current_store
    filter_mode = request.args.get("filter", "all")

    # ダミーの新着口コミを1件追加（将来はAPI連携に差し替え）
    data = load_data()
    data.append({
        "author": "新規ユーザー",
        "starRating": "FIVE",
        "comment": "新しく投稿された口コミです！",
        "reply": "ご利用ありがとうございます！スタッフ一同、またのご来店をお待ちしております。",
        "posted": False,
        "deleted": False,
        "store_id": store
    })
    save_data(data)

    return redirect(f"/?store={store}&filter={filter_mode}")

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
<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>ログイン</title>
  <link rel="apple-touch-icon" href="/static/icon.png">
  <link rel="icon" type="image/png" href="/static/icon.png">
  <style>
    body {
      margin: 0;
      padding: 0;
      background: #f4f6f9;
      font-family: "Segoe UI", sans-serif;
      display: flex;
      justify-content: center;
      align-items: center;
      height: 100vh;
    }

    .login-box {
      background: #ffffff;
      padding: 2rem;
      border-radius: 10px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.08);
      width: 100%;
      max-width: 340px;
      animation: fadeIn 0.6s ease-in-out;
    }

    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(20px); }
      to { opacity: 1; transform: translateY(0); }
    }

    h2 {
      color: #5b6b8a;
      text-align: center;
      margin-bottom: 1.5rem;
    }

    label {
      display: block;
      margin-bottom: 1rem;
      color: #5b6b8a;
      font-weight: 600;
      font-size: 0.95rem;
    }

    input {
      width: 100%;
      padding: 0.7rem;
      border: 1px solid #c9d1db;
      border-radius: 6px;
      font-size: 1rem;
      background: #f9fafc;
    }

    input:focus {
      outline: none;
      border-color: #8a9bbf;
      background: #ffffff;
    }

    button {
      width: 100%;
      padding: 0.8rem;
      background: #5b6b8a;
      color: white;
      font-weight: bold;
      border: none;
      border-radius: 6px;
      cursor: pointer;
      margin-top: 1rem;
      transition: background 0.3s ease;
    }

    button:hover {
      background: #8a9bbf;
    }

    .error {
      color: red;
      margin-bottom: 1rem;
      text-align: center;
    }

    @media (max-width: 400px) {
      .login-box {
        padding: 1.5rem;
        max-width: 280px;
      }
    }
  </style>
</head>
<body>
  <div class="login-box">
    <h2>ログイン</h2>
    {% if error %}<p class="error">{{ error }}</p>{% endif %}
    <form method="post">
      <label>ユーザー名:
        <input name="username" required>
      </label>
      <label>パスワード:
        <input name="password" type="password" required>
      </label>
      <button type="submit">ログイン</button>
    </form>
  </div>
</body>
</html>
""", error=error)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect("/login")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
