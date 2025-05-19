# flask_reply_ui_full.py
import os
import json
import datetime
from flask import Flask, render_template_string, request, redirect, url_for, send_file

app = Flask(__name__)

# ======== データファイルパス ========
REPLIES_FILE = "approved_replies.json"
FETCHED_FILE = "fetched_reviews.json"
REPLIES_OUT = "replies.json"

# ======== テンプレートHTML ========
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <title>AI返信管理</title>
    <style>
        body { font-family: sans-serif; background: #f7f7f7; padding: 2em; }
        h1 { color: #1d2f4f; }
        .reply-box { background: white; border-radius: 10px; padding: 1em; margin-bottom: 1em; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
        .meta { font-size: 0.9em; color: #555; }
        .buttons { margin-top: 1em; }
        .btn { padding: 0.5em 1em; border: none; border-radius: 5px; cursor: pointer; margin-right: 5px; }
        .post-btn { background-color: #3a5b83; color: white; }
        .delete-btn { background-color: #ccc; }
        .posted { background-color: #d4edda; }
        form.inline { display: inline; }
    </style>
</head>
<body>
    <h1>AI返信一覧</h1>
    <form action="/refresh" method="post">
        <button class="btn" type="submit">🔄 レビュー取得＆返信生成</button>
    </form>
    <hr>
    {% for r in replies %}
    <div class="reply-box {% if r.posted %}posted{% endif %}">
        <div class="meta">⭐ {{ r.get('starRating', '') }}｜{{ r.author }}</div>
        <div class="meta">{{ r.comment }}</div>
        <div>{{ r.reply }}</div>
        <div class="buttons">
            <form class="inline" action="/post" method="post">
                <input type="hidden" name="reviewId" value="{{ r.reviewId }}">
                <input type="hidden" name="locationId" value="{{ r.locationId }}">
                <input type="hidden" name="reply" value="{{ r.reply }}">
                <button class="btn post-btn" type="submit">投稿</button>
            </form>
            <form class="inline" action="/delete" method="post">
                <input type="hidden" name="reviewId" value="{{ r.reviewId }}">
                <button class="btn delete-btn" type="submit">削除</button>
            </form>
        </div>
    </div>
    {% endfor %}
</body>
</html>
'''

# ======== データ読込 ========
def load_replies():
    if os.path.exists(REPLIES_FILE):
        with open(REPLIES_FILE, encoding="utf-8") as f:
            return json.load(f)
    return []

# ======== ルート定義 ========
@app.route("/")
def index():
    replies = load_replies()
    return render_template_string(HTML_TEMPLATE, replies=replies)

@app.route("/refresh", methods=["POST"])
def refresh():
    # Step 1: fetch_reviews_v2.py を呼び出す
    os.system("python fetch_reviews_v2.py")

    # Step 2: reply_manager.py を呼び出す
    os.system("python reply_manager.py")

    return redirect(url_for("index"))

@app.route("/post", methods=["POST"])
def post():
    review_id = request.form["reviewId"]
    location_id = request.form["locationId"]
    reply_text = request.form["reply"]

    headers = {
        "Authorization": f"Bearer {get_token()}",
        "Content-Type": "application/json"
    }
    url = f"https://mybusiness.googleapis.com/v4/{location_id}/reviews/{review_id}/reply"
    payload = {"comment": reply_text}
    res = requests.patch(url, headers=headers, json=payload)

    if res.status_code == 200:
        mark_as_posted(review_id)

    return redirect(url_for("index"))

@app.route("/delete", methods=["POST"])
def delete():
    review_id = request.form["reviewId"]
    replies = load_replies()
    replies = [r for r in replies if r["reviewId"] != review_id]
    with open(REPLIES_FILE, "w", encoding="utf-8") as f:
        json.dump(replies, f, ensure_ascii=False, indent=2)
    return redirect(url_for("index"))

# ======== 投稿済みマーク ========
def mark_as_posted(review_id):
    replies = load_replies()
    for r in replies:
        if r["reviewId"] == review_id:
            r["posted"] = True
    with open(REPLIES_FILE, "w", encoding="utf-8") as f:
        json.dump(replies, f, ensure_ascii=False, indent=2)

# ======== トークン取得 ========
def get_token():
    with open("token.pickle", "rb") as f:
        creds = pickle.load(f)
    return creds.token

# ======== 実行エントリポイント ========
if __name__ == "__main__":
    app.run(debug=True, port=5000)
