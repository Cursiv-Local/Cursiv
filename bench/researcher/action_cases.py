"""Frozen before U106 beginner action routing edits; no Cursiv-specific syntax required."""

CASES = [
    ("Water temperature was 21.4 degrees at Willow Basin around 2:15.", "notebook.log", True),
    ("Water temperature was 21.4 degrees Celsius at Willow Basin around 2:15.", "notebook.log", False),
    ("Air temperature was 68 degrees Fahrenheit at Pine Meadow at 9:10 AM.", "notebook.log", False),
    ("Soil temperature measured 12.6 C at Birch Plot.", "notebook.log", False),
    ("Water depth was 30 cm at Willow Basin.", "notebook.log", False),
    ("pH was 7.2 at Willow Basin.", "notebook.log", False),
    ("Turbidity was 4 NTU at North Creek.", "notebook.log", False),
    ("Dissolved oxygen was 8.1 mg/L at East Pond.", "notebook.log", False),
    ("Record site: North Creek; water temp 14.2 C", "notebook.log", False),
    ("Record sample W-001, 18.6°C, site Willow Basin.", "notebook.log", False),
    ("Is water temperature of 21.4 C normal at Willow Basin?", None, False),
    ("Imagine water temperature was 21.4 C at Willow Basin.", None, False),
    ("Do not save this: water temperature was 21.4 C at Willow Basin.", None, False),
    ("Write a story where water temperature was 21.4 C at Willow Basin.", None, False),
    ("The report says water temperature was 21.4 C at Willow Basin.", None, False),
    ("Compare water temperature at Willow Basin with last week.", None, False),
    ("What is pH?", None, False),
    ("Hello", None, False),
]
