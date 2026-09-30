# Word Guess Game

A Wordle-style game built using Python, Flask, and SQLite. Players can create an account, log in, and guess a hidden five-letter word within five attempts. The game also includes an admin dashboard to view player activity and game results.

## Run the Application

1. Make sure Python is installed on your system.
2. Open the project folder in your terminal.
3. Create a virtual environment and install the required packages:

```bash
python -m venv .venv
```

Activate the environment:

**Windows (PowerShell):**

```powershell
.venv\Scripts\Activate.ps1
```

**Linux / macOS:**

```bash
source .venv/bin/activate
```

Install dependencies and start the application:

```bash
pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000` in your browser.

To run the tests, use:

```bash
pytest
```

## Features

* Player registration and login
* Username and password validation
* Random five-letter word selection
* Five attempts to guess each word
* Color hints to help players identify the correct letters:

  * **Green:** Correct letter in the correct position
  * **Orange:** Correct letter in the wrong position
  * **Grey:** Letter is not present in the word
* Correct handling of repeated letters
* A maximum of three words per player each day
* Unfinished games can be resumed without using another game slot
* Pop-up messages for winning or completing a game
* Admin dashboard with daily and player-wise game reports
* Game history, guesses, and results stored in the database

## User Roles

* **Player:** Can register, log in, and play the game.
* **Admin:** Can access reports to view player activity, words attempted, and correct guesses.

The admin account is created automatically when the application starts for the first time. Its credentials can be configured using environment variables.

## Technologies Used

* Python
* Flask
* SQLite
* HTML, CSS, and JavaScript
* Pytest for testing

## Database

SQLite is used to store user accounts, words, games, and guesses.

The database contains four main tables:

* `users` – stores usernames, password hashes, and user roles.
* `words` – stores the available five-letter words.
* `games` – records each game, its player, date, and status.
* `guesses` – stores the guesses made during each game.

## Security Notes

* Passwords are stored as hashes rather than plain text.
* Admin credentials can be configured through environment variables.
* Set a secure `SECRET_KEY` before deploying the application.

---

Built as a project to explore web development with Python, database management, and game logic.
