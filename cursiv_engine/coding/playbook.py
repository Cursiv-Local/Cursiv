"""
The practical knowledge a coding answer must not skip.

PLAYBOOKS — "what actually has to be done" for common setups. Picked by
trigger words in the question / pasted terminal text and given to the model
as ground truth, so answers include the real steps (activate the venv in every
new terminal, no `sudo pip`, which terminal to type in, ...).

ERRORS — known terminal errors -> what it means and the exact fix. Matched
against pasted output so the answer diagnoses the actual error first.
"""
from __future__ import annotations

import re

# (id, title, trigger regex, body)
PLAYBOOKS: list[tuple[str, str, str, str]] = [
    ("python-venv", "Python packages need a virtual environment (venv)",
     r"\bpip3?\b|\bvenv\b|virtualenv|install\s+\w+|module ?not ?found|no module named|externally.managed|pybullet|numpy|requirements\.txt",
     """\
- Install Python packages inside a virtual environment (venv), never with `sudo pip`.
  Ubuntu/Debian/WSL block system-wide pip ("externally-managed-environment").
- One-time setup (Linux / WSL):
    sudo apt update && sudo apt install -y python3-full python3-venv build-essential
    python3 -m venv ~/<name>            (e.g. ~/robot)
- One-time setup (Windows PowerShell):
    py -m venv $HOME\\<name>
- EVERY NEW TERMINAL, before running anything:
    Linux/WSL:   source ~/<name>/bin/activate
    PowerShell:  & $HOME\\<name>\\Scripts\\Activate.ps1
    cmd.exe:     %USERPROFILE%\\<name>\\Scripts\\activate.bat
  The prompt then starts with (<name>). Forgetting this is the #1 cause of
  "No module named ..." after a successful install.
- Inside an active venv: plain `pip install <package>` and `python script.py` -- no sudo, no pip3/python3 needed.
- Leave it with `deactivate`. A broken venv is safe to delete and recreate.
- Save dependencies: `pip freeze > requirements.txt`; restore: `pip install -r requirements.txt`."""),

    ("wsl", "WSL (Linux inside Windows)",
     r"\bwsl\b|/mnt/c|ubuntu|@\w+:[~/]|apt(-get)?\b|\bsudo\b",
     """\
- A prompt like `name@PC:/mnt/c/Users/name$` is WSL (Ubuntu). Commands there are Linux commands, not PowerShell.
- Windows drives live under /mnt/c/...; the Linux home is ~ (/home/<user>). Projects run faster from ~ than from /mnt/c.
- `sudo` asks for the WSL password (typing shows nothing -- that's normal). Use sudo for apt, never for pip.
- System packages: `sudo apt update && sudo apt install -y <pkg>`.
- GUI windows (pybullet GUI, matplotlib, tkinter) need WSLg (Windows 11 built-in). If no window appears: in PowerShell run `wsl --update`, then `wsl --shutdown`, reopen Ubuntu.
- Open the current folder in Windows Explorer: `explorer.exe .`
- Windows paths DON'T work in WSL. C:\\Users\\me\\Desktop\\a.py is /mnt/c/Users/me/Desktop/a.py (forward slashes).
  OneDrive Desktop: /mnt/c/Users/<user>/OneDrive/Desktop/. Convert any path: `wslpath 'C:\\path\\file.py'`.
- Linux names are case-sensitive: Robotic_Arm.py and robotic_arm.py are different files. Use Tab to autocomplete names."""),

    ("linux-commands", "Linux command basics people trip on",
     r"command not found|\binstall\b|missing (destination|file) operand|\bchmod\b|permission denied|\./",
     """\
- `install` is a Linux FILE-COPY command, not a package installer. Packages: `sudo apt install <pkg>` (system) or `pip install <pkg>` (Python, inside a venv).
- `-m` only works after python: `python3 -m venv ...`, `python -m pip ...`. A line starting with `-m` fails with "command not found".
- "command not found" = the program isn't installed or isn't on PATH (or the venv isn't activated).
- Run a script in the current folder: `./script.sh` (after `chmod +x script.sh`) or `bash script.sh`.
- "Permission denied" on a file you own: `chmod +x file`; on system folders: you're outside your home -- work in ~ instead of using sudo."""),

    ("powershell", "Windows PowerShell",
     r"powershell|\bPS [A-Z]:\\|\.ps1|execution polic|\bwinget\b|cmd\.exe|[A-Z]:\\\\?Users",
     """\
- Python on Windows: `py` (the launcher) or `python`. If `python` opens the Microsoft Store, install Python from python.org (tick "Add to PATH") or use `py`.
- Activating a venv can fail with "running scripts is disabled": run once
    Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
- Install programs: `winget install <Name>` (e.g. `winget install Git.Git`). Close and reopen the terminal afterwards so PATH updates.
- Paths use backslashes; quote paths with spaces: "C:\\Program Files\\...".
- PowerShell is not bash: no `export`, `source`, `sudo`, `&&` on old versions; env vars are $env:NAME."""),

    ("pybullet", "PyBullet robot simulation",
     r"pybullet|urdf|robot(ic)? arm|kuka|physics sim",
     """\
- Install inside a venv: `pip install pybullet` (may compile for a few minutes; Linux/WSL needs build-essential, Windows needs "Microsoft C++ Build Tools" if no wheel exists for the Python version).
- Verify: `python -c "import pybullet; print('pybullet works')"`.
- Sample robots ship in `pybullet_data`: `p.setAdditionalSearchPath(pybullet_data.getDataPath())`, then `p.loadURDF('plane.urdf')`, `p.loadURDF('kuka_iiwa/model.urdf')`.
- `p.connect(p.GUI)` opens a window (WSL needs WSLg); `p.connect(p.DIRECT)` runs headless.
- Keep the script alive (loop with `p.stepSimulation()` + `time.sleep(1/240)`) or the window closes immediately.
- `pybullet_envs` examples are deprecated -- don't suggest them."""),

    ("node", "Node.js / npm",
     r"\bnpm\b|\bnode\b|\bnpx\b|package\.json|javascript|typescript|react|vite|next\.js",
     """\
- Install Node LTS: Windows `winget install OpenJS.NodeJS.LTS`; WSL/Ubuntu use nvm (`curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash`, reopen terminal, `nvm install --lts`).
- In a project folder: `npm install` once (creates node_modules), then `npm run dev` / `npm start` as package.json says.
- Never `sudo npm install -g` -- with nvm global installs need no sudo.
- "EADDRINUSE" = the port is busy: stop the other server or use another port."""),

    ("git", "Git basics",
     r"\bgit\b|github|commit|push|clone|merge conflict",
     """\
- First time: `git config --global user.name "Name"` and `git config --global user.email "you@example.com"`.
- Daily: `git status` -> `git add <files>` -> `git commit -m "message"` -> `git push`.
- New repo from a folder: `git init`, add/commit, create the repo on GitHub, `git remote add origin <url>`, `git push -u origin main`.
- Never commit secrets (.env, keys). Add them to .gitignore first."""),

    ("gpu", "GPU / CUDA / local AI",
     r"\bcuda\b|\bgpu\b|nvidia|torch|tensorflow|ollama|out of memory|\bvram\b",
     """\
- Check the GPU: `nvidia-smi` (Windows or WSL). A 4 GB GPU fits ~7B models; bigger ones spill to CPU and get slow.
- PyTorch with CUDA: use the exact command from pytorch.org's selector; a plain `pip install torch` may be CPU-only.
- "CUDA out of memory": smaller model/batch size, or close other GPU programs (Ollama keeps models loaded for a few minutes)."""),

    ("running-code", "Running a script",
     r"\brun\b|\bexecute\b|\.py\b|script|how do i start",
     """\
- Say WHERE to run it (which terminal: PowerShell, WSL/Ubuntu, VS Code terminal) and FROM WHICH folder (`cd` into it first).
- Activate the venv first if the project uses one.
- `python file.py` (Windows/inside venv) or `python3 file.py` (Linux without venv).
- Show what successful output looks like so the user can tell it worked."""),
]


# (trigger regex on pasted output, meaning + fix)
ERRORS: list[tuple[str, str]] = [
    (r"externally.managed.environment",
     "Ubuntu/Debian protect the system Python. Don't use sudo pip or --break-system-packages: create a venv "
     "(`sudo apt install -y python3-full python3-venv`, `python3 -m venv ~/env`, `source ~/env/bin/activate`), then `pip install` inside it."),
    (r"install: missing destination file operand|install: cannot stat",
     "`install` is the Linux file-copy command, not a package installer. Use `pip install <pkg>` inside an activated venv (or `sudo apt install <pkg>` for system packages)."),
    (r"^-m: command not found|-m: command not found",
     "`-m` only works after python (`python3 -m venv ...`). The line must start with `python3`."),
    (r"No module named ['\"]?(\w+)",
     "The package isn't installed in the Python that ran the script -- usually the venv isn't activated in this terminal. Activate it (`source ~/env/bin/activate` / `.\\env\\Scripts\\Activate.ps1`), then `pip install <package>` if still missing."),
    (r"(\w[\w.-]*): command not found|is not recognized as (an internal or external command|the name of a cmdlet)",
     "The program isn't installed or isn't on PATH (on Windows: reopen the terminal after installing). If it's a Python tool, activate the venv."),
    (r"running scripts is disabled on this system",
     "PowerShell blocks scripts by default. Run once: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, then activate again."),
    (r"Permission denied",
     "No permission for that file/folder. For your own scripts: `chmod +x file`. For system folders: work inside your home folder instead of using sudo."),
    (r"error: command '(gcc|x86_64-linux-gnu-gcc|cl\.exe)' failed|Microsoft Visual C\+\+ 14\.0 or greater is required|Failed building wheel",
     "The package needs to compile C code. Linux/WSL: `sudo apt install -y build-essential python3-dev`. Windows: install 'Microsoft C++ Build Tools' (Desktop development with C++), or use a Python version that has a prebuilt wheel."),
    (r"EADDRINUSE|address already in use",
     "Another program is using that port. Stop the other server (Ctrl+C in its terminal) or start on a different port."),
    (r"can't open file '/mnt/[a-z]/[^']*[A-Z]:\\\\",
     "A Windows path (C:\\...) was given in WSL, which only understands Linux paths. C:\\Users\\me\\Desktop\\file.py is "
     "/mnt/c/Users/me/Desktop/file.py -- or convert it: python \"$(wslpath 'C:\\path\\file.py')\"."),
    (r"can't open file .*No such file or directory|\[Errno 2\] No such file or directory",
     "Python can't find the file in the current folder. `cd` to the folder that holds it (or give the full path), "
     "check the exact spelling and capital letters (Linux is case-sensitive; `ls` lists the files), and in WSL use "
     "/mnt/c/... paths, not C:\\... (OneDrive Desktop is /mnt/c/Users/<user>/OneDrive/Desktop)."),
    (r"SyntaxError|IndentationError",
     "The Python file itself has a typo/indentation problem at the line shown. Python files must be run with `python file.py`, not pasted into the shell."),
    (r"cannot connect to X server|qt\.qpa\.xcb|could not connect to display|cannot open display",
     "No display for GUI windows in WSL. Update WSL (`wsl --update` in PowerShell, then `wsl --shutdown`), or use a headless mode (e.g. pybullet `p.DIRECT`)."),
    (r"CUDA out of memory|out of memory",
     "The GPU ran out of memory. Use a smaller model/batch, or close other GPU users (including Ollama models)."),
    (r"\[sudo\][^\n]*password|sudo: authenticate",
     "That prompt wants your WSL/Linux account password; nothing shows while typing -- type it and press Enter."),
]


def _hits(pattern: str, text: str) -> int:
    try:
        return len(re.findall(pattern, text, re.I | re.M))
    except re.error:
        return 0


def match_playbooks(text: str, limit: int = 3) -> list[tuple[str, str]]:
    """Most relevant playbooks for this text: [(title, body)]."""
    scored = [(_hits(trig, text), title, body) for _id, title, trig, body in PLAYBOOKS]
    scored = [s for s in scored if s[0] > 0]
    scored.sort(key=lambda s: -s[0])
    return [(t, b) for _n, t, b in scored[:limit]]


def diagnose(text: str) -> list[tuple[str, str]]:
    """Known errors found in pasted terminal output: [(matched line, fix)]."""
    found, seen = [], set()
    for pattern, fix in ERRORS:
        m = re.search(pattern, text, re.I | re.M)
        if m and fix not in seen:
            seen.add(fix)
            line = text[text.rfind("\n", 0, m.start()) + 1: (text.find("\n", m.end()) + 1 or len(text) + 1) - 1]
            found.append((line.strip()[:160], fix))
    return found
