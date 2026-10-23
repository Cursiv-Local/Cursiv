---
title: Reading pasted terminal errors and fixing them step by step
triggers: externally.managed|command not found|missing destination|no module named|not recognized|permission denied|error:|traceback|sudo
---
## Question
(pasted)
```
joshu@Josh:/mnt/c/Users/joshu$ install pybullet
install: missing destination file operand after 'pybullet'
joshu@Josh:/mnt/c/Users/joshu$ sudo pip3 install virtualenv
error: externally-managed-environment
joshu@Josh:/mnt/c/Users/joshu$ -m sudo pip3 install virtualenv
-m: command not found
```

## Answer
### What went wrong
1. `install pybullet` → `install` is a Linux command for **copying files**, not for installing software. That's why it asks for a "destination".
2. `sudo pip3 install virtualenv` → Ubuntu **blocks pip outside a virtual environment** to protect its own Python ("externally-managed-environment"). You also don't need `virtualenv` — Python has `venv` built in. And never use `sudo` with pip.
3. `-m sudo pip3 ...` → `-m` only works *after* `python3` (like `python3 -m venv`). On its own, bash thinks `-m` is a program.

### Do this instead (in this same Ubuntu terminal)
1. Install Python's venv tools (only step that uses sudo):
```bash
sudo apt update && sudo apt install -y python3-full python3-venv build-essential
```
2. Create your environment (one time):
```bash
python3 -m venv ~/robot
```
3. Turn it on — **every new terminal**:
```bash
source ~/robot/bin/activate
```
Your prompt should now start with `(robot)`.
4. Install the package — no sudo:
```bash
pip install pybullet
```
5. Check:
```bash
python -c "import pybullet; print('pybullet works')"
```

### If something goes wrong
- Still "externally-managed-environment" → the prompt doesn't show `(robot)`; run step 3.
- `python3 -m venv` says "ensurepip is not available" → step 1 didn't finish; run it again.
- The password prompt shows nothing while typing → normal; type it and press Enter.
