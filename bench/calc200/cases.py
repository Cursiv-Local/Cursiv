"""
U102 calculation benchmark: at least 200 cases for Cursiv's deterministic calculators, with expected
values taken from outside the code under test.

Sources for expected values:
  * unit factors: exact definitions in NIST SP 811 (2008), Appendix B (e.g. 1 in = 0.0254 m exactly,
    1 lb = 0.45359237 kg, 1 US gal = 3.785411784 L, 1 knot = 1852/3600 m/s, 1 atm = 101325 Pa)
  * temperature: the defining relations C = K - 273.15 and F = C x 9/5 + 32
  * oxygen solubility: APHA Standard Methods 4500-O, Table 4500-O:I (fresh water, 1 atm), values below
  * specific conductance: APHA 2510 B linear compensation, 0.0191 per degree C (re-implemented here)
  * atomic weights: IUPAC standard values (Na 22.990, Cl 35.45, K 39.098, C 12.011, O 15.999, H 1.008, N 14.007)
  * statistics and percentages: worked by hand below

Each case is (question, expect, tolerance):
  expect a number  -> Cursiv's code must answer with that number (within tolerance)
  expect "REFUSE"  -> Cursiv's code must read it and refuse (physically impossible or out of range)
  expect None      -> Cursiv's code must not answer (missing unit or variable, a question ABOUT a number)
"""

# ── NIST SP 811 exact factors, written out independently of fieldcalc._UNITS ──
M = {"in": 0.0254, "ft": 0.3048, "yd": 0.9144, "mi": 1609.344, "nmi": 1852.0, "cm": 0.01, "mm": 0.001, "km": 1000.0,
     "m": 1.0}
KG = {"lb": 0.45359237, "oz": 0.028349523125, "g": 0.001, "mg": 1e-6, "kg": 1.0}
L = {"gal": 3.785411784, "imperial gallon": 4.54609, "qt": 0.946352946, "ml": 0.001, "l": 1.0}
M2 = {"acre": 4046.8564224, "ha": 10000.0, "ft2": 0.09290304, "km2": 1e6, "m2": 1.0}
MS = {"mph": 0.44704, "km/h": 1000 / 3600, "knots": 1852 / 3600, "m/s": 1.0}
PA = {"psi": 6894.757293168361, "atm": 101325.0, "bar": 1e5, "kpa": 1000.0, "mmhg": 101325 / 760, "pa": 1.0}


def _conv(table, v, a, b):
    return v * table[a] / table[b]


def _rel(x, r=1e-6):
    return max(abs(x) * r, 1e-9)


CASES: list[tuple] = []

# 1. unit conversions (84)
for table, pairs in (
        (M, [("in", "cm"), ("ft", "m"), ("mi", "km"), ("yd", "m"), ("nmi", "km"), ("km", "mi"), ("m", "ft"),
             ("cm", "in"), ("mm", "in")]),
        (KG, [("lb", "kg"), ("oz", "g"), ("kg", "lb"), ("g", "oz"), ("mg", "g")]),
        (L, [("gal", "l"), ("l", "gal"), ("imperial gallon", "l"), ("qt", "l"), ("ml", "l")]),
        (M2, [("acre", "ha"), ("ha", "acre"), ("ft2", "m2"), ("km2", "acre")]),
        (MS, [("mph", "m/s"), ("km/h", "m/s"), ("knots", "m/s"), ("m/s", "mph")]),
        (PA, [("psi", "kpa"), ("atm", "kpa"), ("bar", "psi"), ("mmhg", "kpa")])):
    for a, b in pairs:
        for v in (1, 2.5, 12):
            exp = _conv(table, v, a, b)
            CASES.append((f"Convert {v} {a} to {b}", exp, max(_rel(exp, 1e-4), 0.00005)))
# six-decimal-place requests (exact factors must survive the rounding)
for v, a, b in ((3, "l", "gal"), (10, "knots", "m/s"), (1, "psi", "kpa"), (7, "in", "cm")):
    table = L if a == "l" else MS if a == "knots" else PA if a == "psi" else M
    exp = round(_conv(table, v, a, b), 6)
    CASES.append((f"Convert {v} {a} to {b} to six decimal places", exp, 5e-7))

# 2. temperature (24), including the absolute-zero boundary
for c in (-40, 0, 4, 18.6, 25, 37, 100, -273.15):
    CASES.append((f"Convert {c} C to F", c * 9 / 5 + 32, 0.0001))
    CASES.append((f"Convert {c} C to K", c + 273.15, 0.0001))
for f in (32, 212, -40, 98.6):
    CASES.append((f"Convert {f} F to C", (f - 32) * 5 / 9, 0.0001))
for k in (0, 273.15, 300):
    CASES.append((f"Convert {k} K to C", k - 273.15, 0.0001))
CASES.append(("Convert -300 C to K", "REFUSE", 0))      # below absolute zero
CASES.append(("Convert -10 K to C", "REFUSE", 0))
CASES.append(("Convert -500 F to C", "REFUSE", 0))

# 3. oxygen solubility, APHA Table 4500-O:I, 0-40 °C (41) + out of range (2)
DO_TABLE = [14.621, 14.216, 13.829, 13.460, 13.107, 12.770, 12.447, 12.139, 11.843, 11.559, 11.288, 11.027,
            10.777, 10.537, 10.306, 10.084, 9.870, 9.665, 9.467, 9.276, 9.092, 8.915, 8.743, 8.578, 8.418, 8.263,
            8.113, 7.968, 7.827, 7.691, 7.559, 7.430, 7.305, 7.183, 7.065, 6.950, 6.837, 6.727, 6.620, 6.515, 6.412]
for t, do in enumerate(DO_TABLE):
    CASES.append((f"Measured DO is {do} mg/L at {t} C. What is the percent saturation?", 100.0, 0.1))
CASES.append(("Measured DO is 7 mg/L at 55 C. What is the percent saturation?", "REFUSE", 0))
CASES.append(("Measured DO is -2 mg/L at 15 C. What is the percent saturation?", "REFUSE", 0))

# 4. specific conductance at 25 °C, APHA 2510 B (12) + out of range (1)
for k, t in ((412, 18), (1250, 9.5), (100, 25), (85, 5), (2000, 30), (640, 12), (55, 0.5), (3100, 35),
             (500, 20), (920, 15), (150, 22), (75, 8)):
    CASES.append((f"Conductivity is {k} uS/cm at {t} C. What is the specific conductance at 25 C?",
                  k / (1 + 0.0191 * (t - 25)), max(k / (1 + 0.0191 * (t - 25)) * 0.0005, 0.05)))
CASES.append(("Conductivity is 412 uS/cm at 60 C. What is the specific conductance at 25 C?", "REFUSE", 0))

# 5. discharge (8)
for w, d, v, fl in ((3.2, 0.4, 0.6, True), (1.5, 0.25, 0.8, False), (10, 1.2, 0.3, False), (0.8, 0.1, 0.5, True),
                    (5, 0.6, 1.1, False), (2.2, 0.35, 0.45, True), (12, 2.0, 0.9, False), (0.5, 0.05, 0.2, False)):
    how = "the float moved" if fl else "current meter velocity"
    exp = w * d * v * (0.85 if fl else 1)
    CASES.append((f"The stream is {w} m wide, {d} m deep and {how} {v} m/s. What is the discharge?", exp,
                  max(exp * 0.0005, 0.0005)))

# 6. molar solutions, IUPAC atomic weights (8)
MOLAR = {"NaCl": 22.990 + 35.45, "KCl": 39.098 + 35.45, "NaOH": 22.990 + 15.999 + 1.008,
         "KNO3": 39.098 + 14.007 + 3 * 15.999}
for salt, mm in MOLAR.items():
    for molarity, ml in ((0.1, 500), (0.01, 1000)):
        exp = molarity * ml / 1000 * mm
        CASES.append((f"How many grams of {salt} for {ml} mL of {molarity} M solution?", exp, max(exp * 0.002, 0.001)))

# 7. conductivity units (4)
for q, exp in (("Convert 450 uS/cm to mS/cm", 0.45), ("What is 1.8 mS/cm in µS/cm?", 1800),
               ("Convert 12.5 mS/cm to uS/cm", 12500), ("Convert 3 uS/cm to mS/cm", 0.003)):
    CASES.append((q, exp, max(exp * 1e-6, 1e-9)))

# 8. statistics, worked by hand (10)
CASES += [
    ("Calculate the median of 4, 9, 2, 20, 7.", 7, 0),
    ("Calculate the mean of 18.6, 19.1, 18.9, 18.4, and 19.0.", 18.8, 0.0001),
    ("What is the median of 1, 2, 3, 4?", 2.5, 0),
    ("Calculate the sample standard deviation of 2, 4, 4, 4, 5, 5, 7, 9.", 2.13809, 0.0001),    # sqrt(32/7)
    ("What is the population standard deviation of 2, 4, 4, 4, 5, 5, 7, 9?", 2.0, 0.0001),      # sqrt(32/8)
    ("What is the range of 12.4, 9.8, 15.1, 10.7?", 5.3, 0.0001),
    ("What is the total of 1.5, 2.5, 3.0?", 7.0, 0.0001),
    ("Calculate the mean of 10, 20.", 15, 0),
    ("What is the average of 7.1, 7.3, 7.2?", 7.2, 0.0001),
    ("Calculate the median of 5, 5, 5.", 5, 0),
]

# 9. percentages and arithmetic (8)
CASES += [
    ("What is 15% of 240?", 36, 0), ("What is 2.5% of 80?", 2, 0), ("What is 100% of 7.5?", 7.5, 0),
    ("What is 12 times 7?", 84, 0), ("What is 144 divided by 12?", 12, 0), ("What is 3.5 plus 2.25?", 5.75, 0),
    ("What is 10 minus 12.5?", -2.5, 0), ("What is 0.1 plus 0.2?", 0.3, 1e-12),
]

# 10. dilution (6) + impossible (2)
CASES += [
    ("How much 1000 mg/L stock do I need to make 250 mL of a 20 mg/L standard?", 5, 0.01),
    ("How much 500 mg/L stock do I need to make 100 mL of a 10 mg/L standard?", 2, 0.01),
    ("How much 100 mg/L stock do I need to make 1000 mL of a 5 mg/L standard?", 50, 0.01),
    ("How much 2000 mg/L stock do I need to make 50 mL of a 40 mg/L standard?", 1, 0.01),
    ("How much 1000 mg/L stock do I need to make 500 mL of a 1 mg/L standard?", 0.5, 0.01),
    ("How much 250 mg/L stock do I need to make 200 mL of a 25 mg/L standard?", 20, 0.01),
    ("How much 10 mg/L stock do I need to make 100 mL of a 50 mg/L standard?", "REFUSE", 0),   # can't concentrate
    ("How much 1000 mg/L stock do I need to make -100 mL of a 10 mg/L standard?", "REFUSE", 0),
]

# 11. must not answer: missing unit, missing variable, a question about a number (12)
CASES += [
    ("Convert 5 to feet", None, 0),
    ("Measured DO is 7.8 mg/L. What is the percent saturation?", None, 0),
    ("What is the specific conductance at 25 C?", None, 0),
    ("The stream is 3 m wide. What is the discharge?", None, 0),
    ("How many grams of NaCl do I need?", None, 0),
    ("Is 412 uS/cm conductivity normal for a trout stream?", None, 0),
    ("Why would a float give a higher velocity than a current meter?", None, 0),
    ("What does percent saturation of dissolved oxygen tell me?", None, 0),
    ("My stock bottle says 1000 mg/L, how long does it keep?", None, 0),
    ("Is 14.2 C cold for a creek in October?", None, 0),
    ("Convert 10 kg to liters", None, 0),                     # mass to volume needs a density
    ("Convert 5 m to kg", None, 0),
]
