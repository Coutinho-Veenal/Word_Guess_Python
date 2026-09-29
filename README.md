# Word Guess Game

Wordle-style game built with **Python / Flask / SQLite**.

## Run
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python app.py            # http://127.0.0.1:5000
pytest                   # run tests
```

## Users
* **Player** – self-registers at `/register`.
  Username: 5+ letters (A-Z/a-z). Password: 5+ chars with a letter, a digit and one of `$ % * )`.
* **Admin** – seeded on first start: `Admin` / `Admin$123`
  (override with env vars `ADMIN_USER`, `ADMIN_PASS`). Set `SECRET_KEY` in production.

## Rules implemented
* 20 five-letter upper-case words seeded in the `words` table.
* Starting a game picks a random word; max **3 words per user per day**
  (an unfinished game is resumed and doesn't use another slot).
* Max **5 guesses**, upper-case 5-letter input; colours: green (right spot),
  orange (wrong spot), grey (absent). Duplicate letters handled correctly.
* Win → congratulations pop-up; 5 misses → "Better luck next time" pop-up; after OK the game stops.
* Words given and guesses are stored (`games`, `guesses`) with date.
* Admin reports at `/admin`: per-day (users, correct guesses) and per-user (date, words tried, correct).

## Schema
`users(id, username, password_hash, role)` · `words(id, word)` ·
`games(id, user_id, word_id, play_date, status)` · `guesses(id, game_id, guess_no, guess, guessed_at)`
