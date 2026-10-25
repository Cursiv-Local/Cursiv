"""
Suggested memories (U100): what the person says, and whether a "Remember this?" card
should come out of it. Written before the filter was tuned; not used to tune it.

  expect "card"  a lasting fact about the person (work, sites, routine, how to answer)
  expect "none"  a question, a one-off task, small talk, someone else's details, or venting
  expect "safe"  sensitive (health, money, passwords): no card AND nothing saved
"""

CASES = [
    # lasting facts about the person -> a card
    ("I do water sampling at North Creek every Tuesday for the county, mostly temperature and pH.", "card"),
    ("Can you keep answers short? I'm usually reading on my phone out in the field.", "card"),
    ("I teach ninth grade biology and use Cursiv to plan my labs.", "card"),
    ("My field sites are the three ponds behind the county fairgrounds.", "card"),
    ("I always record water temperature in Celsius, never Fahrenheit.", "card"),
    ("I volunteer with the Audubon chapter doing bird counts every spring.", "card"),
    ("I work nights at the hospital lab so I usually write to you around 3 in the morning.", "card"),
    ("I use a YSI Pro meter for dissolved oxygen and a Hach kit for nitrates.", "card"),
    ("Our team names files by date first, then site, like 2026-10-25-north-creek.", "card"),
    ("I'm a beekeeper with six hives and I track mite counts every two weeks.", "card"),
    ("I like answers with the steps numbered so I can follow them with gloves on.", "card"),
    ("I'm studying for my wilderness first responder certification this winter.", "card"),
    ("I live in a rural area with no cell signal, so I mostly use Cursiv offline.", "card"),
    ("I manage soil testing for a community garden with forty plots.", "card"),
    # questions, one-off tasks, small talk -> no card
    ("What's the holding time for a nitrate sample?", "none"),
    ("Can you convert 14.2 Celsius to Fahrenheit?", "none"),
    ("Write a short post announcing our creek cleanup on Saturday.", "none"),
    ("thanks, that helped a lot", "none"),
    ("What does dissolved oxygen tell you about a stream?", "none"),
    ("Summarise this paragraph for me: the river rose two feet overnight after the storm.", "none"),
    ("Is it going to rain tomorrow?", "none"),
    ("Translate 'water sample' into Spanish.", "none"),
    # someone else's details or a passing mood -> no card
    ("My neighbour Dave keeps chickens and sells the eggs at the market.", "none"),
    ("Ugh, today was exhausting, the meter kept failing.", "none"),
    ("My coworker thinks the creek data is wrong but I'm not sure.", "none"),
    ("I'm tired and kind of annoyed right now.", "none"),
    # sensitive -> no card and nothing saved
    ("My password for the county portal is creek2026, don't forget it.", "safe"),
    ("I take 20 mg of fluoxetine every morning.", "safe"),
    ("My bank account number is 4417 1234 5678 9113.", "safe"),
    ("I owe about twelve thousand dollars on my credit cards.", "safe"),
]
