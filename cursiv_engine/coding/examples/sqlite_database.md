---
title: Save data in a database with SQLite (built into Python)
triggers: database|sqlite|\bsql\b|store data|save records|table|inventory|contacts
---
## Question
I want to keep a list of contacts in a database from Python.

## Answer
No installs — `sqlite3` comes with Python. The whole database is one file (`contacts.db`).

### The program
**contacts.py**
```python
import sqlite3
import sys
from pathlib import Path

DB = Path(__file__).with_name("contacts.db")


def connect() -> sqlite3.Connection:
    con = sqlite3.connect(DB)
    con.execute("""CREATE TABLE IF NOT EXISTS contacts (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        phone TEXT,
        email TEXT UNIQUE
    )""")
    return con


def add(name: str, phone: str = "", email: str | None = None) -> None:
    with connect() as con:                       # commits automatically
        con.execute("INSERT INTO contacts (name, phone, email) VALUES (?, ?, ?)", (name, phone, email))


def find(text: str) -> list[tuple]:
    with connect() as con:
        return con.execute("SELECT id, name, phone, email FROM contacts WHERE name LIKE ? ORDER BY name",
                           (f"%{text}%",)).fetchall()


def delete(contact_id: int) -> None:
    with connect() as con:
        con.execute("DELETE FROM contacts WHERE id = ?", (contact_id,))


if __name__ == "__main__":
    cmd, *rest = sys.argv[1:] or ["list"]
    if cmd == "add" and rest:
        add(*rest[:3])
        print("Added", rest[0])
    elif cmd == "delete" and rest:
        delete(int(rest[0]))
        print("Deleted", rest[0])
    else:
        for row in find(rest[0] if rest else ""):
            print(*row, sep=" | ")
```

### Use it
```bash
python contacts.py add "Jane Doe" 555-0100 jane@example.com
```
```bash
python contacts.py list
```
```bash
python contacts.py list jane
```
```bash
python contacts.py delete 1
```

### Important
- Always use `?` placeholders (as above), never f-strings inside SQL — that prevents SQL injection and quoting bugs.
- To look inside the file visually: install "DB Browser for SQLite" (`winget install DBBrowserForSQLite.DBBrowserForSQLite`).

### If something goes wrong
- `UNIQUE constraint failed: contacts.email` → that email is already saved.
- `database is locked` → another program (e.g. DB Browser) has unsaved changes open; close or save it.
