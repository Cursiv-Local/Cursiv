---
title: Put a project on GitHub for the first time
triggers: github|\bgit\b|push|commit|repo(sitory)?|version control|upload (my )?code
---
## Question
How do I put my project on GitHub?

## Answer
**Where:** a terminal in your project folder.

### One-time (per computer)
1. Install Git (Windows): `winget install Git.Git`, then close and reopen the terminal. (WSL: `sudo apt install -y git`.)
2. Tell Git who you are:
```bash
git config --global user.name "Your Name"
```
```bash
git config --global user.email "you@example.com"
```
3. Install the GitHub CLI and log in (easiest way to authenticate): `winget install GitHub.cli`, reopen the terminal, then
```bash
gh auth login
```
Choose GitHub.com → HTTPS → log in with a web browser.

### First upload (per project)
1. Go to the project folder:
```bash
cd path/to/your/project
```
2. Make a `.gitignore` so secrets and junk never upload. Minimum for Python:
```
.venv/
__pycache__/
.env
*.log
```
3. Start tracking and make the first commit:
```bash
git init -b main
```
```bash
git add .
```
```bash
git commit -m "First version"
```
4. Create the GitHub repo and push in one step:
```bash
gh repo create my-project --private --source . --push
```
**Success:** it prints the repo URL; open it in your browser to see your files.

### Every change after that
```bash
git add .
```
```bash
git commit -m "Describe what changed"
```
```bash
git push
```

### If something goes wrong
- `Author identity unknown` → step 2 of one-time setup.
- You committed a secret → change the key at the provider right away; deleting the file later doesn't remove it from history.
- `rejected ... fetch first` → someone (or another PC) pushed first: `git pull --rebase` then `git push`.
