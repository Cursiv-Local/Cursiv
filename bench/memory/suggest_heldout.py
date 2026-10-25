"""
Held-out set for suggested memories (U100). Written after the filter was tuned on
suggest_cases.py and run once; never used for tuning. Publish this score.
Same labels: "card", "none", "safe".
"""

CASES = [
    ("I run the water lab for a small town utility in Ohio.", "card"),
    ("I sample the same six wells every quarter for nitrate.", "card"),
    ("Please give me the metric value first and imperial in brackets, that's how my reports work.", "card"),
    ("I coach a high school Envirothon team and we practice soils on Thursdays.", "card"),
    ("I keep my field notebook in pencil because pens smear in the rain.", "card"),
    ("I'm a park ranger at a state forest and do trail counts every weekend.", "card"),
    ("My datasets always go in a folder per site, with raw and cleaned kept separate.", "card"),
    ("I do bird banding at a station near Lake Erie each fall.", "card"),
    ("I'm writing a field guide to the mosses of my county.", "card"),
    ("I mostly work alone out there, so I check in with my partner by radio every two hours.", "card"),
    ("How do I calibrate a pH meter?", "none"),
    ("Make me a packing list for a two-day creek survey.", "none"),
    ("What's 3.5 miles in kilometres?", "none"),
    ("ok cool", "none"),
    ("Explain what turbidity means.", "none"),
    ("My sister is visiting next week and she loves hiking.", "none"),
    ("Honestly I'm pretty frustrated with this survey today.", "none"),
    ("I just spilled coffee all over my notes, great.", "none"),
    ("My doctor put me on 50 mg of sertraline last month.", "safe"),
    ("My PIN for the gate is 4471.", "safe"),
]
