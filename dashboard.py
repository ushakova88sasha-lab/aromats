import os
import re
import sqlite3
from collections import Counter
from flask import Flask, render_template, jsonify

app = Flask(__name__)

DB_PATH = os.getenv("DB_PATH", "responses.db")

AROMAS = [
    "Красное вино", "Мамины объятия", "Земля", "Запах денег",
    "Яблочный апероль", "Груша в бренди", "Бурбон со сливками",
    "Кашемир и мускус", "Плитка шоколада", "Конопляное масло",
    "Патрики", "Холодил. в цветоч."
]


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_stats():
    conn = get_db()
    cur = conn.cursor()

    # Средние оценки и количество ответов по каждому аромату
    cur.execute("""
        SELECT aroma,
               COUNT(*) as total,
               ROUND(AVG(like_score), 1) as avg_like,
               ROUND(AVG(bright_score), 1) as avg_bright
        FROM responses
        WHERE like_score IS NOT NULL
        GROUP BY aroma
        ORDER BY avg_like DESC
    """)
    aroma_stats = [dict(row) for row in cur.fetchall()]

    # Статистика "Запах денег"
    cur.execute("""
        SELECT variant, COUNT(*) as count
        FROM responses
        WHERE aroma = 'Запах денег' AND variant IS NOT NULL
        GROUP BY variant
    """)
    money_stats = [dict(row) for row in cur.fetchall()]

    # Топ 3 слова из ответов про комнату
    cur.execute("""
        SELECT aroma, room FROM responses
        WHERE room IS NOT NULL AND room != ''
    """)
    STOP_WORDS = {'в','на','и','с','по','для','из','что','как','не','это','бы'}
    word_counts = {}
    for row in cur.fetchall():
        aroma = row["aroma"]
        words = re.findall(r'[а-яёА-ЯЁa-zA-Z]{3,}', row["room"])
        if aroma not in word_counts:
            word_counts[aroma] = Counter()
        for w in words:
            wl = w.lower()
            if wl not in STOP_WORDS:
                word_counts[aroma][wl] += 1

    rooms = {aroma: [w for w, _ in cnt.most_common(3)]
             for aroma, cnt in word_counts.items()}

    # Общее количество пользователей
    cur.execute("SELECT COUNT(DISTINCT user_id) as users FROM responses")
    total_users = cur.fetchone()["users"]

    # Общее количество ответов
    cur.execute("SELECT COUNT(*) as total FROM responses")
    total_responses = cur.fetchone()["total"]

    conn.close()

    return {
        "aroma_stats": aroma_stats,
        "money_stats": money_stats,
        "rooms": rooms,
        "total_users": total_users,
        "total_responses": total_responses,
    }


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/stats")
def api_stats():
    return jsonify(get_stats())


@app.route("/api/responses")
def api_responses():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, created_at, first_name, username, aroma,
               like_score, bright_score, room, variant
        FROM responses
        ORDER BY created_at DESC
    """)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return jsonify(rows)


if __name__ == "__main__":
    port = int(os.getenv("DASHBOARD_PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
