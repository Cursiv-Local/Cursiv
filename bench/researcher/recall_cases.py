"""Frozen beginner notebook-recall probes, written before U106 recall edits.

Expected values name synthetic sample IDs, never real research observations.
"""

CASES = [
    ("record_yesterday", "What did I record yesterday?", ["WB-001", "WB-002", "EM-001"]),
    ("write_down_yesterday", "What did I write down yesterday?", ["WB-001", "WB-002", "EM-001"]),
    ("jot_today", "Show what I jotted down today.", ["WB-003"]),
    ("last_tuesday", "What did I record last Tuesday?", ["WB-004"]),
    ("notebook_yesterday", "Show my field notebook from yesterday.", ["WB-001", "WB-002", "EM-001"]),
    ("willow_water_yesterday", "What was the water temperature at Willow Basin yesterday?", ["WB-001"]),
    ("east_water_yesterday", "What was the water temperature at East Meadow yesterday?", ["EM-001"]),
    ("site_yesterday", "Show observations at Willow Basin yesterday.", ["WB-001", "WB-002"]),
    ("sample_today", "Show measurements for sample WB-003 today.", ["WB-003"]),
    ("sample_other_day", "Show measurements for sample WB-003 yesterday.", []),
    ("words_yesterday", "Find observations mentioning cloudy yesterday.", ["WB-001"]),
    ("empty_site", "What was the water temperature at Empty Reach yesterday?", []),
    ("general_temperature", "What is water temperature?", None),
    ("measurement_howto", "How do I measure water temperature at Willow Basin?", None),
    ("creative", "Write a story about observations yesterday.", None),
    ("workspace_file", "Find notes.txt about water temperature.", None),
    ("saved_notes", "Show my saved notes.", None),
    ("memory_write", "Remember that water temperature was 21 degrees.", None),
    ("negated", "Do not show my field notebook.", None),
    ("future", "What might water temperature at Willow Basin be tomorrow?", None),
]
