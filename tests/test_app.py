import sqlite3
from datetime import date
import pytest
from app import create_app, evaluate, validate_password, validate_username


@pytest.fixture
def client(tmp_path):
    app = create_app(str(tmp_path / "t.db"))
    app.config["TESTING"] = True
    return app.test_client(), app


def reg_login(c, u="Player", p="abc12$"):
    c.post("/register", data={"username": u, "password": p})
    c.post("/login", data={"username": u, "password": p})


def test_validators():
    assert validate_username("abcde") is None
    assert validate_username("abcd") and validate_username("abc12")
    assert validate_password("ab1$x") is None
    for bad in ["ab1$", "abcde$", "abc123", "12345$", "ab12#x"]:
        assert validate_password(bad)


def test_evaluate_repeats():
    assert evaluate("CRANE", "CRANE") == ["green"] * 5
    assert evaluate("SPEED", "ABIDE") == ["grey", "grey", "orange", "grey", "orange"]
    assert evaluate("LLAMA", "HELLO")[:2] == ["orange", "orange"]


def test_seed_words(client):
    _, app = client
    db = sqlite3.connect(app.config["DB_PATH"])
    ws = [r[0] for r in db.execute("SELECT word FROM words")]
    assert len(ws) == 20 and all(len(w) == 5 and w.isupper() for w in ws)


def test_win_flow(client):
    c, app = client
    reg_login(c)
    assert c.post("/api/start").status_code == 200
    assert c.post("/api/guess", json={"guess": "abc"}).status_code == 400
    assert c.post("/api/guess", json={"guess": "abcde"}).status_code == 400
    db = sqlite3.connect(app.config["DB_PATH"])
    ans = db.execute("SELECT w.word FROM games g JOIN words w ON w.id=g.word_id").fetchone()[0]
    r = c.post("/api/guess", json={"guess": ans}).get_json()
    assert r["status"] == "won" and r["answer"] == ans


def test_daily_limit_and_reports(client):
    c, app = client
    reg_login(c)
    for _ in range(3):
        assert c.post("/api/start").status_code == 200
        for _ in range(5):
            r = c.post("/api/guess", json={"guess": "ZZZZZ"}).get_json()
        assert r["status"] == "lost"
    assert c.post("/api/start").status_code == 403
    c.get("/logout")
    c.post("/login", data={"username": "Admin", "password": "Admin$123"})
    html = c.get(f"/admin?day={date.today().isoformat()}").get_data(as_text=True)
    assert "<td>1</td>" in html
    html = c.get("/admin?user=Player").get_data(as_text=True)
    assert "<td>3</td>" in html


def test_role_protection(client):
    c, _ = client
    reg_login(c)
    assert c.get("/admin").status_code == 302
