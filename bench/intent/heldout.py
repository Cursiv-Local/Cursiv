"""
U99 held-out phrasing set: written after the prompt and checks were final and never
used for tuning. Its score is the one to publish. Same format as phrasings.py.
"""

CASES = [
    # field notebook
    ("Upper Meadow plot 4: soil temp 9.8 C, light frost", "notebook.log", {"details": "9.8"}),
    ("pond B turbidity was 40 NTU after the storm, add that", "notebook.log", {"details": "40"}),
    ("Note in the field log: Cedar Run 13.1 C, fast water", "notebook.log", {"details": "13.1"}),
    ("Fox Hollow spring, pH 6.2, smells of sulfur. Record it.", "notebook.log", {"details": "6.2"}),
    ("enter an observation: Gravel Bar, 21 dragonflies counted", "notebook.log", {"details": "21"}),
    ("put this in the notebook - Black Creek dissolved oxygen 7.4 mg/L", "notebook.log", {"details": "7.4"}),
    ("Mud Flats salinity 12 ppm, low tide", "notebook.log", {"details": "12"}),
    ("record: Ash Grove, canopy cover 65 %", "notebook.log", {"details": "65"}),
    ("what did I log this morning?", "notebook.today", {}),
    ("anything in my notebook about frost?", "notebook.search", {"words": "frost"}),
    ("search my field log for turbidity", "notebook.search", {"words": "turbidity"}),
    ("what's the average soil temp in my Upper Meadow samples?", "notebook.average", {"measure": "soil"}),
    ("highest pH I've got for Fox Hollow?", "notebook.average", {"measure": "ph"}),
    # memory
    ("remember that the lab closes at 4 on Fridays", "memory.save", {"fact": "lab closes"}),
    ("please remember my GPS unit is the older Garmin", "memory.save", {"fact": "garmin"}),
    ("don't forget Priya is allergic to latex", "memory.save", {"fact": "latex"}),
    ("forget what I said about the Garmin", "memory.forget", {"words": "garmin"}),
    ("please delete the memory about the lab hours", "memory.forget", {"words": "lab"}),
    # files
    ("open notes.md", "file.read", {"path": "notes.md"}),
    ("what's inside budget.csv?", "file.read", {"path": "budget.csv"}),
    ("show me my files", "file.list", {}),
    ("make plan.txt with: sample sites 1 to 5", "file.create", {"path": "plan.txt", "text": "sample sites 1 to 5"}),
    ("add 'bring spare batteries' to packing.txt", "file.append", {"path": "packing.txt", "text": "bring spare batteries"}),
    ("put a line in log.txt saying Visited Cedar Run", "file.append", {"path": "log.txt", "text": "visited cedar run"}),
    # workspace and offline
    ("let's use my Thesis folder", "workspace.set", {"folder": "thesis"}),
    ("work in the Grant 2027 folder from now on", "workspace.set", {"folder": "grant 2027"}),
    ("go offline please", "offline.on", {}),
    ("no internet for the rest of the trip", "offline.on", {}),
    ("ok you can go online again", "offline.off", {}),
    ("switch offline mode off", "offline.off", {}),
    # memory recall: answered by memory's own route
    ("what do you remember about Priya?", "native.memory", {}),
    # traps
    ("How do I log in to my university VPN?", "none", {}),
    ("What's a good way to record bird calls?", "none", {}),
    ("Remember the Alamo — who said that?", "none", {}),
    ("Why does pH matter for trout?", "none", {}),
    ("My notes from class are a mess, any tips?", "none", {}),
    ("What happens if I go offline on Zoom?", "none", {}),
    ("Write a short poem about a muddy creek", "none", {}),
    ("Is 7.4 mg/L of dissolved oxygen healthy?", "none", {}),
    ("The pond was 12 C, which seems cold for June, right?", "none", {}),
    ("Explain how a field notebook differs from a lab notebook", "none", {}),
    ("I keep forgetting my waders at home", "none", {}),
    ("Which folder structure works best for photos?", "none", {}),
    ("Tell me about the history of the logging industry", "none", {}),
    ("Can you summarise what a workspace in Excel is?", "none", {}),
    ("If I recorded 3 m of erosion, is that a lot?", "none", {}),
    ("good morning", "none", {}),
    ("Convert 21 C to F", "none", {}),
    ("What file format should I save GPS tracks in?", "none", {}),
    ("Do people still keep paper logbooks?", "none", {}),
]
