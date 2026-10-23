---
title: A small web app with Flask (form + saved data)
triggers: flask|web ?app|website|web server|localhost|html form|backend|api endpoint
---
## Question
Build me a simple web app where I can add notes and see them in the browser.

## Answer
**Where:** any terminal; examples use PowerShell (WSL commands in brackets).

### One-time setup
```powershell
mkdir $HOME\projects\notes; cd $HOME\projects\notes
```
```powershell
py -m venv .venv
```
```powershell
.\.venv\Scripts\Activate.ps1
```
[WSL: `python3 -m venv .venv` then `source .venv/bin/activate`]
```powershell
pip install flask
```

### Files
**app.py**
```python
import json
from pathlib import Path
from flask import Flask, redirect, render_template_string, request

app = Flask(__name__)
DATA = Path(__file__).with_name("notes.json")

PAGE = """<!doctype html>
<title>Notes</title>
<style>body{font-family:system-ui;max-width:640px;margin:40px auto} li{margin:6px 0}</style>
<h1>Notes</h1>
<form method="post" action="/add">
  <input name="text" placeholder="Write a note" required style="width:70%">
  <button>Add</button>
</form>
<ul>{% for n in notes %}<li>{{ n }}</li>{% endfor %}</ul>
"""


def load() -> list[str]:
    return json.loads(DATA.read_text(encoding="utf-8")) if DATA.exists() else []


@app.get("/")
def index():
    return render_template_string(PAGE, notes=load())


@app.post("/add")
def add():
    notes = load()
    notes.append(request.form["text"].strip())
    DATA.write_text(json.dumps(notes, indent=2), encoding="utf-8")
    return redirect("/")


if __name__ == "__main__":
    app.run(debug=True, port=5000)
```

### Run it (venv active, in the project folder)
```powershell
python app.py
```
**Success:** the terminal shows `Running on http://127.0.0.1:5000`. Open that address in your browser, add a note, refresh — it stays (saved in `notes.json`). Stop the server with Ctrl+C.

### Every new terminal
`cd $HOME\projects\notes` then `.\.venv\Scripts\Activate.ps1` before `python app.py`.

### If something goes wrong
- `No module named 'flask'` → venv not active in this terminal.
- `Address already in use` / port busy → another server is running; stop it or change `port=5001`.
- Page doesn't load from your phone → `debug` server only listens on this PC. For other devices on your Wi-Fi use `app.run(host="0.0.0.0", port=5000)` and open `http://<PC's IP>:5000` (allow it in the Windows firewall prompt).
- Don't use the debug server for a public website.
