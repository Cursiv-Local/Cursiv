---
title: A desktop app window with buttons (tkinter, no installs)
triggers: gui|desktop app|window|tkinter|button|pyqt|app with a window|interface
---
## Question
Make me a small desktop app with a window, a text box and a button.

## Answer
**Where:** Windows (tkinter comes with Python). On WSL first run `sudo apt install -y python3-tk`.

### The program
**counter_app.py**
```python
import tkinter as tk
from tkinter import messagebox


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Word Counter")
        self.geometry("480x320")

        tk.Label(self, text="Type or paste text:").pack(anchor="w", padx=10, pady=(10, 0))
        self.text = tk.Text(self, height=10, wrap="word")
        self.text.pack(fill="both", expand=True, padx=10)

        row = tk.Frame(self)
        row.pack(fill="x", padx=10, pady=10)
        tk.Button(row, text="Count words", command=self.count).pack(side="left")
        tk.Button(row, text="Clear", command=lambda: self.text.delete("1.0", "end")).pack(side="left", padx=6)
        self.result = tk.Label(row, text="")
        self.result.pack(side="right")

    def count(self):
        words = self.text.get("1.0", "end").split()
        if not words:
            messagebox.showinfo("Word Counter", "Nothing to count yet.")
        self.result.config(text=f"{len(words)} words, {sum(map(len, words))} letters")


if __name__ == "__main__":
    App().mainloop()
```

### Run it
```powershell
py counter_app.py
```
**Success:** a window opens; type, click "Count words", the count shows bottom-right.

### Make it a double-click .exe (optional)
In a venv:
```powershell
pip install pyinstaller
```
```powershell
pyinstaller --onefile --windowed counter_app.py
```
The app is in the `dist` folder. (Unsigned .exe files may trigger a SmartScreen warning — click "More info" → "Run anyway".)

### If something goes wrong
- `No module named tkinter` (WSL/Linux) → `sudo apt install -y python3-tk`.
- Window doesn't appear in WSL → `wsl --update` then `wsl --shutdown` (WSLg), or run it on Windows with `py`.
