---
title: Start a new Python project the right way (venv + requirements)
triggers: new (python )?project|start (a )?project|set ?up python|install python|requirements\.txt|virtual env|venv|pip install
---
## Question
How do I set up a new Python project and install packages?

## Answer
Which terminal are you in? Steps for both:

### A) Windows PowerShell
1. Check Python is installed (should print `Python 3.x`):
```powershell
py --version
```
If not found: `winget install Python.Python.3.12`, then close and reopen PowerShell.
2. Make the project folder and go into it:
```powershell
mkdir $HOME\projects\myapp; cd $HOME\projects\myapp
```
3. Create a venv inside the project (one time):
```powershell
py -m venv .venv
```
4. Activate it — **every time you open a new terminal for this project**:
```powershell
.\.venv\Scripts\Activate.ps1
```
Prompt now starts with `(.venv)`. If you see "running scripts is disabled":
```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```
5. Install packages (inside the venv):
```powershell
pip install requests
```
6. Record them so the project can be rebuilt later:
```powershell
pip freeze > requirements.txt
```

### B) WSL / Ubuntu / Linux
```bash
sudo apt update && sudo apt install -y python3-full python3-venv
```
```bash
mkdir -p ~/projects/myapp && cd ~/projects/myapp
```
```bash
python3 -m venv .venv
```
Every new terminal:
```bash
source .venv/bin/activate
```
```bash
pip install requests
```
```bash
pip freeze > requirements.txt
```

### Run your code
With the venv active, from the project folder:
```bash
python main.py
```

### Rebuild on another computer
Create + activate a venv (steps 3–4), then:
```bash
pip install -r requirements.txt
```

### If something goes wrong
- `externally-managed-environment` → you're outside the venv. Activate it first; never `sudo pip`.
- `No module named X` → wrong terminal / venv not active, or package not installed in this venv.
- `python` opens the Microsoft Store → use `py`, or reinstall Python with "Add to PATH" ticked.
- Add `.venv/` to `.gitignore` — never commit the venv.
