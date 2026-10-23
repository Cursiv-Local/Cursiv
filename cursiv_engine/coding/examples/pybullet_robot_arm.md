---
title: Simulate a robot arm with PyBullet (WSL or Windows)
triggers: pybullet|robot(ic)? arm|urdf|kuka|physics sim|simulat
---
## Question
How do I install pybullet and get a robot arm simulation running?

## Answer
**Where:** the Ubuntu (WSL) terminal — the one whose prompt looks like `you@PC:~$`. (Windows PowerShell steps are at the end.)

### One-time setup
1. Install Python's tools and a compiler (asks for your WSL password; typing shows nothing):
```bash
sudo apt update && sudo apt install -y python3-full python3-venv build-essential
```
2. Create a virtual environment named `robot`:
```bash
python3 -m venv ~/robot
```
3. Turn it on (your prompt now starts with `(robot)`):
```bash
source ~/robot/bin/activate
```
4. Install pybullet inside it (no `sudo`; may take a few minutes to build):
```bash
pip install pybullet
```
5. Check it:
```bash
python -c "import pybullet; print('pybullet works')"
```

### Every new terminal
```bash
source ~/robot/bin/activate
```
Without this you'll get `No module named 'pybullet'`.

### The program
Make a project folder and the file:
```bash
mkdir -p ~/arm && cd ~/arm && nano arm.py
```
**arm.py**
```python
import math
import time
import pybullet as p
import pybullet_data

p.connect(p.GUI)                       # use p.DIRECT for no window
p.setAdditionalSearchPath(pybullet_data.getDataPath())
p.setGravity(0, 0, -9.81)
p.loadURDF("plane.urdf")
arm = p.loadURDF("kuka_iiwa/model.urdf", useFixedBase=True)
joints = p.getNumJoints(arm)
print(f"Loaded arm with {joints} joints")

t = 0.0
try:
    while True:
        # swing every joint back and forth
        for j in range(joints):
            target = 0.8 * math.sin(t + j)
            p.setJointMotorControl2(arm, j, p.POSITION_CONTROL, targetPosition=target, force=200)
        p.stepSimulation()
        time.sleep(1 / 240)
        t += 1 / 240
except KeyboardInterrupt:
    p.disconnect()
```
Save in nano: Ctrl+O, Enter, Ctrl+X.

### Run it
```bash
python arm.py
```
**Success looks like:** `Loaded arm with 7 joints` and a 3D window with an orange arm swinging. Stop with Ctrl+C.

### If something goes wrong
- `error: externally-managed-environment` → you ran pip outside the venv. Do step 3, then step 4 again.
- `No module named 'pybullet'` → new terminal, venv not active: `source ~/robot/bin/activate`.
- No window / `cannot connect to X server` → in PowerShell: `wsl --update`, then `wsl --shutdown`, reopen Ubuntu. Or change `p.GUI` to `p.DIRECT`.
- `error: command 'gcc' failed` → step 1 didn't finish; run it again.

### Windows PowerShell instead of WSL
```powershell
py -m venv $HOME\robot
```
```powershell
& $HOME\robot\Scripts\Activate.ps1
```
```powershell
pip install pybullet
```
If activation says "running scripts is disabled": `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, then activate again. If the pip build fails asking for "Microsoft Visual C++ 14.0", install Microsoft C++ Build Tools (Desktop development with C++) or use WSL.
