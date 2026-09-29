"""Word Guess Game - Flask + SQLite."""
import os
import random
import re
import sqlite3
from collections import Counter
from datetime import date
from functools import wraps

from flask import (Flask, flash, g, jsonify, redirect, render_template,
                   request, session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

MAX_GAMES_PER_DAY = 3
MAX_GUESSES = 5
WORDS = ["CRANE", "SLATE", "PLANT", "BRAVE", "CHAIR", "HOUSE", "WATER",
         "LIGHT", "MUSIC", "PIZZA", "TIGER", "APPLE", "BEACH", "DREAM",
         "GRAPE", "SMILE", "STONE", "TRAIN", "WORLD", "YOUTH"]
ADMIN_USER = os.environ.get("ADMIN_USER", "Admin")
ADMIN_PASS = os.environ.get("ADMIN_PASS", "Admin$123")

SCHEMA = """
CREATE TABLE IF NOT EXISTS users(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  role TEXT NOT NULL CHECK(role IN ('admin','player')));
CREATE TABLE IF NOT EXISTS words(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  word TEXT UNIQUE NOT NULL);
CREATE TABLE IF NOT EXISTS games(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL REFERENCES users(id),
  word_id INTEGER NOT NULL REFERENCES words(id),
  play_date TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'in_progress'
         CHECK(status IN ('in_progress','won','lost')));
CREATE TABLE IF NOT EXISTS guesses(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  game_id INTEGER NOT NULL REFERENCES games(id),
  guess_no INTEGER NOT NULL,
  guess TEXT NOT NULL,
  guessed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
"""


def validate_username(u):
    if not re.fullmatch(r"[A-Za-z]{5,}", u or ""):
        return "Username must be at least 5 letters (A-Z, a-z only)."


def validate_password(p):
    p = p or ""
    if (len(p) < 5 or not re.search(r"[A-Za-z]", p) or not re.search(r"\d", p)
            or not re.search(r"[$%*)]", p)):
        return ("Password must be at least 5 characters with a letter, a "
                "digit and one of $ % * )")


def evaluate(guess, answer):
    """Return per-letter colours: green / orange / grey (handles repeats)."""
    result = ["grey"] * len(answer)
    left = Counter()
    for i, (g_, a) in enumerate(zip(guess, answer)):
        if g_ == a:
            result[i] = "green"
        else:
            left[a] += 1
    for i, g_ in enumerate(guess):
        if result[i] != "green" and left[g_] > 0:
            result[i] = "orange"
            left[g_] -= 1
    return result


def create_app(db_path=None):
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-change-me")
    app.config["DB_PATH"] = db_path or os.path.join(app.root_path, "game.db")

    def get_db():
        if "db" not in g:
            g.db = sqlite3.connect(app.config["DB_PATH"])
            g.db.row_factory = sqlite3.Row
        return g.db

    @app.teardown_appcontext
    def close_db(_):
        db = g.pop("db", None)
        if db:
            db.close()

    def init_db():
        db = sqlite3.connect(app.config["DB_PATH"])
        db.executescript(SCHEMA)
        if not db.execute("SELECT 1 FROM words").fetchone():
            db.executemany("INSERT INTO words(word) VALUES(?)",
                           [(w,) for w in WORDS])
        if not db.execute("SELECT 1 FROM users WHERE role='admin'").fetchone():
            db.execute("INSERT INTO users(username,password_hash,role) "
                       "VALUES(?,?,'admin')",
                       (ADMIN_USER, generate_password_hash(ADMIN_PASS)))
        db.commit()
        db.close()

    init_db()

    def login_required(role=None, api=False):
        def deco(f):
            @wraps(f)
            def wrapper(*a, **kw):
                if "user_id" not in session:
                    return (jsonify(error="Login required"), 401) if api \
                        else redirect(url_for("login"))
                if role and session.get("role") != role:
                    return (jsonify(error="Forbidden"), 403) if api \
                        else redirect(url_for("home"))
                return f(*a, **kw)
            return wrapper
        return deco

    # ---------- auth ----------
    @app.route("/")
    def home():
        if "user_id" not in session:
            return redirect(url_for("login"))
        return redirect(url_for("admin" if session["role"] == "admin"
                                else "game"))

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "POST":
            u = request.form.get("username", "").strip()
            p = request.form.get("password", "")
            err = validate_username(u) or validate_password(p)
            db = get_db()
            if not err and db.execute(
                    "SELECT 1 FROM users WHERE lower(username)=lower(?)",
                    (u,)).fetchone():
                err = "Username already taken."
            if err:
                flash(err)
            else:
                db.execute("INSERT INTO users(username,password_hash,role) "
                           "VALUES(?,?,'player')",
                           (u, generate_password_hash(p)))
                db.commit()
                flash("Registered! Please log in.")
                return redirect(url_for("login"))
        return render_template("register.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            row = get_db().execute(
                "SELECT * FROM users WHERE username=?",
                (request.form.get("username", "").strip(),)).fetchone()
            if row and check_password_hash(row["password_hash"],
                                           request.form.get("password", "")):
                session.clear()
                session.update(user_id=row["id"], username=row["username"],
                               role=row["role"])
                return redirect(url_for("home"))
            flash("Invalid username or password.")
        return render_template("login.html")

    @app.route("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"))

    # ---------- game ----------
    def games_today(uid):
        return get_db().execute(
            "SELECT COUNT(*) FROM games WHERE user_id=? AND play_date=?",
            (uid, date.today().isoformat())).fetchone()[0]

    def current_game(uid):
        return get_db().execute(
            "SELECT g.*, w.word FROM games g JOIN words w ON w.id=g.word_id "
            "WHERE g.user_id=? AND g.status='in_progress' "
            "ORDER BY g.id DESC LIMIT 1", (uid,)).fetchone()

    def game_state(game):
        rows = get_db().execute(
            "SELECT guess FROM guesses WHERE game_id=? ORDER BY guess_no",
            (game["id"],)).fetchall()
        state = {
            "status": game["status"], "max_guesses": MAX_GUESSES,
            "guesses": [{"word": r["guess"],
                         "colors": evaluate(r["guess"], game["word"])}
                        for r in rows]}
        if game["status"] != "in_progress":
            state["answer"] = game["word"]
        return state

    @app.route("/game")
    @login_required("player")
    def game():
        return render_template("game.html")

    @app.route("/api/status")
    @login_required("player", api=True)
    def api_status():
        used = games_today(session["user_id"])
        cur = current_game(session["user_id"])
        return jsonify(games_played_today=used, max_games=MAX_GAMES_PER_DAY,
                       remaining=max(0, MAX_GAMES_PER_DAY - used),
                       in_progress=bool(cur),
                       game=game_state(cur) if cur else None)

    @app.route("/api/start", methods=["POST"])
    @login_required("player", api=True)
    def api_start():
        uid, db = session["user_id"], get_db()
        cur = current_game(uid)
        if cur:  # resume unfinished game (doesn't consume another slot)
            return jsonify(game_state(cur))
        if games_today(uid) >= MAX_GAMES_PER_DAY:
            return jsonify(error=f"You can play only {MAX_GAMES_PER_DAY} "
                                 "words per day. Come back tomorrow!"), 403
        w = random.choice(db.execute("SELECT id FROM words").fetchall())
        db.execute("INSERT INTO games(user_id,word_id,play_date) "
                   "VALUES(?,?,?)", (uid, w["id"], date.today().isoformat()))
        db.commit()
        return jsonify(game_state(current_game(uid)))

    @app.route("/api/guess", methods=["POST"])
    @login_required("player", api=True)
    def api_guess():
        uid, db = session["user_id"], get_db()
        game = current_game(uid)
        if not game:
            return jsonify(error="No active game. Start a new one."), 400
        word = ((request.get_json(silent=True) or {}).get("guess") or "")
        if not re.fullmatch(r"[A-Z]{5}", word):
            return jsonify(error="Enter a 5-letter word in UPPER CASE."), 400
        n = db.execute("SELECT COUNT(*) FROM guesses WHERE game_id=?",
                       (game["id"],)).fetchone()[0] + 1
        db.execute("INSERT INTO guesses(game_id,guess_no,guess) "
                   "VALUES(?,?,?)", (game["id"], n, word))
        status = "in_progress"
        if word == game["word"]:
            status = "won"
        elif n >= MAX_GUESSES:
            status = "lost"
        db.execute("UPDATE games SET status=? WHERE id=?",
                   (status, game["id"]))
        db.commit()
        state = game_state(db.execute(
            "SELECT g.*, w.word FROM games g JOIN words w ON w.id=g.word_id "
            "WHERE g.id=?", (game["id"],)).fetchone())
        return jsonify(state)

    # ---------- admin reports ----------
    @app.route("/admin")
    @login_required("admin")
    def admin():
        db = get_db()
        ctx = {"day": request.args.get("day", ""),
               "user": request.args.get("user", "").strip(),
               "day_report": None, "user_report": None, "user_error": None}
        if ctx["day"]:
            ctx["day_report"] = db.execute(
                "SELECT COUNT(DISTINCT user_id) AS users, "
                "COALESCE(SUM(status='won'),0) AS correct "
                "FROM games WHERE play_date=?", (ctx["day"],)).fetchone()
        if ctx["user"]:
            u = db.execute("SELECT id FROM users WHERE lower(username)="
                           "lower(?) AND role='player'",
                           (ctx["user"],)).fetchone()
            if not u:
                ctx["user_error"] = "No such player."
            else:
                ctx["user_report"] = db.execute(
                    "SELECT play_date, COUNT(*) AS tried, "
                    "SUM(status='won') AS correct FROM games "
                    "WHERE user_id=? GROUP BY play_date "
                    "ORDER BY play_date DESC", (u["id"],)).fetchall()
        return render_template("admin.html", **ctx)

    return app


if __name__ == "__main__":
    create_app().run(debug=True)
