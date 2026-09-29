const $ = id => document.getElementById(id);
const post = (url, body) => fetch(url, {method: "POST",
  headers: {"Content-Type": "application/json"}, body: JSON.stringify(body || {})})
  .then(async r => ({ok: r.ok, data: await r.json()}));

const ROWS = ["QWERTYUIOP", "ASDFGHJKL", "ZXCVBNM"];
const RANK = {grey: 0, orange: 1, green: 2};
let keyState = {};

function showMsg(t) { $("msg").textContent = t; $("msg").hidden = !t; }

function buildKeyboard() {
  const kb = $("keyboard"); kb.innerHTML = "";
  ROWS.forEach(row => {
    const r = document.createElement("div"); r.className = "krow";
    [...row].forEach(letter => {
      const k = document.createElement("div");
      k.className = "key"; k.textContent = letter; k.id = "key-" + letter;
      r.appendChild(k);
    });
    kb.appendChild(r);
  });
}

function updateKeyboard(guesses) {
  keyState = {};
  guesses.forEach(g => {
    [...g.word].forEach((letter, i) => {
      const c = g.colors[i];
      if (!(letter in keyState) || RANK[c] > RANK[keyState[letter]]) keyState[letter] = c;
    });
  });
  Object.keys(keyState).forEach(letter => {
    const el = $("key-" + letter);
    if (el) el.className = "key " + keyState[letter];
  });
}

function render(game, animateLast) {
  const board = $("board"); board.innerHTML = "";
  for (let i = 0; i < game.max_guesses; i++) {
    const row = document.createElement("div"); row.className = "row";
    const g = game.guesses[i];
    for (let j = 0; j < 5; j++) {
      const c = document.createElement("div");
      c.className = "cell" + (g ? " filled" : "");
      c.textContent = g ? g.word[j] : "";
      row.appendChild(c);
      if (g) {
        const delay = animateLast && i === game.guesses.length - 1 ? j * 90 : 0;
        setTimeout(() => {
          c.classList.add(g.colors[j], "reveal");
        }, delay);
      }
    }
    board.appendChild(row);
  }
  updateKeyboard(game.guesses);
  $("entry").hidden = game.status !== "in_progress";
  if (!$("entry").hidden) $("guess").focus();
}

function openModal(title, text) {
  $("modalTitle").textContent = title;
  $("modalText").textContent = text;
  $("overlay").hidden = false;
}
$("modalOk").onclick = () => { $("overlay").hidden = true; refresh(); };

async function refresh() {
  buildKeyboard();
  const s = await (await fetch("/api/status")).json();
  $("playedCount").textContent = s.games_played_today;
  $("start").hidden = s.in_progress || s.remaining === 0;
  showMsg(!s.in_progress && s.remaining === 0
    ? "Daily limit reached — you've played 3 words today. Come back tomorrow!" : "");
  if (s.game) render(s.game, false);
  else { $("board").innerHTML = ""; $("entry").hidden = true; }
}

$("start").onclick = async () => {
  showMsg("");
  const {ok, data} = await post("/api/start");
  if (!ok) return showMsg(data.error);
  await refresh();
};

async function submitGuess() {
  const word = $("guess").value.toUpperCase();
  if (word.length !== 5) return showMsg("Enter a 5-letter word.");
  $("guess").value = "";
  const {ok, data} = await post("/api/guess", {guess: word});
  if (!ok) return showMsg(data.error);
  showMsg("");
  render(data, true);
  if (data.status === "won")
    setTimeout(() => openModal("You got it!", "Congratulations — you guessed the word."), 650);
  else if (data.status === "lost")
    setTimeout(() => openModal("Better luck next time", "The word was " + data.answer + "."), 650);
}
$("submit").onclick = submitGuess;
$("guess").addEventListener("keydown", e => { if (e.key === "Enter") submitGuess(); });
$("guess").addEventListener("input", e => e.target.value = e.target.value.toUpperCase().replace(/[^A-Z]/g, ""));

buildKeyboard();
refresh();
