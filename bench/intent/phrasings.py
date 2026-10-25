"""
U99 phrasing set: how people actually ask for Cursiv's actions, and traps that
must trigger nothing. "native.memory" cases are recall questions memory's own route
(memory/intents.py) answers before this step runs; the intent step must stay out. Each case: (message, expected action or "none", {slot: text
that must appear in it}). Used by scripts/intent_bench.py against the real local
model; the score is published with the release, not tuned against.
"""

LOG = [
    ("Add a note that North Creek was 14.2 C and cloudy today", "notebook.log", {"details": "14.2"}),
    ("jot down: South Pond pH 6.4, algae at the edges", "notebook.log", {"details": "6.4"}),
    ("record water temp 13.8 C at East Fork, slightly turbid", "notebook.log", {"details": "13.8"}),
    ("North Creek reading: 15.1 C, clear, light flow", "notebook.log", {"details": "15.1"}),
    ("log that the well at Plot 3 was 9.5 C this morning", "notebook.log", {"details": "9.5"}),
    ("put in my notebook: Ridge transect, soil temp 11 C, frost on the grass", "notebook.log", {"details": "11"}),
    ("can you save an observation: Lake Marsh pH 7.8", "notebook.log", {"details": "7.8"}),
    ("note down conductivity 420 uS at South Pond", "notebook.log", {"details": "420"}),
    ("just measured the creek at 12.9 C, write it down", "notebook.log", {"details": "12.9"}),
    ("save this reading - Station 4, dissolved oxygen 8.2 mg/L", "notebook.log", {"details": "8.2"}),
    ("East Fork today: 16.4 C and the water was murky, log it", "notebook.log", {"details": "16.4"}),
    ("record that sample NC-07 at North Creek had pH 7.1", "notebook.log", {"details": "7.1"}),
    ("add an entry: Willow Spring 10.2 C, cattle tracks nearby", "notebook.log", {"details": "10.2"}),
    ("log: river bank erosion worse at the bend, 3 m of bank lost", "notebook.log", {"details": "3"}),
    ("keep track of this - pond turbidity 25 NTU", "notebook.log", {"details": "25"}),
    ("write down that the stream was 14 C at noon", "notebook.log", {"details": "14"}),
    ("I want to log a field observation: South Pond, 17.3 C", "notebook.log", {"details": "17.3"}),
    ("note that Plot 2 soil moisture was 31 %", "notebook.log", {"details": "31"}),
    ("record 6.9 pH at the upper creek", "notebook.log", {"details": "6.9"}),
    ("log the marsh reading, 18.0 C, lots of frogs", "notebook.log", {"details": "18.0"}),
]

NOTEBOOK_READ = [
    ("what did I record today?", "notebook.today", {}),
    ("show me what I logged today", "notebook.today", {}),
    ("what did I log about cloudy water?", "notebook.search", {"words": "cloudy"}),
    ("find my notes about algae", "notebook.search", {"words": "algae"}),
    ("look up the North Creek entries in my notebook", "notebook.search", {"words": "north creek"}),
    ("did I log anything about cattle?", "notebook.search", {"words": "cattle"}),
    ("what was the average water temp in my TEST samples?", "notebook.average", {"measure": "water"}),
    ("average pH across my NC samples", "notebook.average", {"measure": "ph"}),
    ("what's the highest water temp I recorded at East Fork?", "notebook.average", {"measure": "water"}),
    ("lowest temperature in my South Pond samples?", "notebook.average", {"measure": "temp"}),
]

MEMORY = [
    ("remember that my truck's spare key is in the blue box", "memory.save", {"fact": "blue box"}),
    ("don't forget I'm allergic to bee stings", "memory.save", {"fact": "bee stings"}),
    ("keep in mind that Sam handles the water samples on Fridays", "memory.save", {"fact": "sam"}),
    ("please remember my survey season ends in November", "memory.save", {"fact": "november"}),
    ("save this for later: the gate code at the reservoir is changed monthly", "memory.save", {"fact": "gate code"}),
    ("remember I prefer metric units", "memory.save", {"fact": "metric"}),
    ("forget what I told you about the truck key", "memory.forget", {"words": "truck"}),
    ("you can forget the bee sting thing", "memory.forget", {"words": "bee"}),
    ("delete the memory about the gate code", "memory.forget", {"words": "gate code"}),
    ("what do you remember about Sam?", "native.memory", {}),
    ("do you remember where the spare key is?", "native.memory", {}),
    ("what did I tell you about my allergies?", "native.memory", {}),
]

FILES = [
    ("read notes.txt", "file.read", {"path": "notes.txt"}),
    ("open my field-plan.md", "file.read", {"path": "field-plan.md"}),
    ("show me what's in sites.csv", "file.read", {"path": "sites.csv"}),
    ("what files are in my workspace?", "file.list", {}),
    ("list my files", "file.list", {}),
    ("make a file called todo.txt with: buy pH strips", "file.create", {"path": "todo.txt", "text": "buy ph strips"}),
    ("create summary.md saying Survey went well", "file.create", {"path": "summary.md", "text": "survey went well"}),
    ("add Site C, 12.1 C to notes.txt", "file.append", {"path": "notes.txt", "text": "12.1"}),
    ("put a line in notes.txt: Site D, 9.8 C", "file.append", {"path": "notes.txt", "text": "9.8"}),
    ("append 'check fence' to todo.txt", "file.append", {"path": "todo.txt", "text": "check fence"}),
]

WORKSPACE = [
    ("work in my Field Data folder", "workspace.set", {"folder": "field data"}),
    ("use the Survey 2026 folder", "workspace.set", {"folder": "survey 2026"}),
    ("switch the workspace to C:\\Users\\me\\Documents\\Creek", "workspace.set", {"folder": "creek"}),
    ("let's work out of my Reports folder", "workspace.set", {"folder": "reports"}),
]

OFFLINE = [
    ("go offline for the rest of the day", "offline.on", {}),
    ("turn on offline mode", "offline.on", {}),
    ("keep everything on this computer from now on", "offline.on", {}),
    ("I'm in the field, stay offline", "offline.on", {}),
    ("turn offline mode off", "offline.off", {}),
    ("go back online", "offline.off", {}),
    ("you can use the internet again", "offline.off", {}),
]

TRAPS = [
    ("What is a riffle in a stream?", "none", {}),
    ("Why do field scientists keep logs?", "none", {}),
    ("I wrote a log yesterday about logging trucks", "none", {}),
    ("Tell me a joke about data logging", "none", {}),
    ("How do I remember to take my readings every day?", "none", {}),
    ("What should I write in a field notebook?", "none", {}),
    ("Explain what a workspace is in VS Code", "none", {}),
    ("Write a poem about a field notebook left in the rain", "none", {}),
    ("Is 14.2 C cold for a trout stream?", "none", {}),
    ("Convert 12.4 C to F", "none", {}),
    ("my grandfather kept a logbook on his boat", "none", {}),
    ("the creek was beautiful today", "none", {}),
    ("What's the best way to organise a folder of photos?", "none", {}),
    ("Should I go offline while traveling abroad?", "none", {}),
    ("I forget things a lot lately", "none", {}),
    ("Remember when we talked about rivers? That was fun", "none", {}),
    ("Can you explain how pH meters work?", "none", {}),
    ("Imagine you logged 100 samples; what would the average be?", "none", {}),
    ("hi", "none", {}),
    ("thanks, that's all for now", "none", {}),
    ("what's 3 miles in kilometres?", "none", {}),
    ("Logging companies cut trees near the river", "none", {}),
    ("Does Cursiv save my files to the cloud?", "none", {}),
    ("How long to fill 20 L at 2 L/min?", "none", {}),
    ("Let me think about where to save this later", "none", {}),
]

CASES = LOG + NOTEBOOK_READ + MEMORY + FILES + WORKSPACE + OFFLINE + TRAPS
