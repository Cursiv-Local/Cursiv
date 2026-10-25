"""
Field calculations a small model gets wrong (U101). Written before the code that answers them.

(question, expected number, tolerance) -- expected None means Cursiv's code must NOT answer it
(a question about the number, not a calculation). Expected values from the standard formulas:
  dilution C1V1 = C2V2; conductivity to 25 °C with APHA 2510 B's 0.0191 per °C; discharge = width
  x depth x velocity, x 0.85 for a surface float (USGS float coefficient); percent DO saturation
  against the Benson & Krause solubility; molar solutions from molar mass x molarity x volume.
"""

CASES = [
    # dilution
    ("Dilute 50 mL of a 1000 mg/L stock to make 10 mg/L. What final volume?", 5000, 1),
    ("How much 1000 mg/L stock do I need to make 250 mL of a 20 mg/L standard?", 5, 0.01),
    # conductivity to 25 °C
    ("Conductivity is 412 uS/cm at 18 C. What is the specific conductance at 25 C?", 475.6, 0.6),
    ("My meter read 1250 µS/cm at a water temperature of 9.5 °C. Correct it to 25 °C.", 1775.7, 0.6),
    # discharge
    ("The stream is 3.2 m wide, 0.4 m deep and the float moved 0.6 m/s. What is the discharge?", 0.653, 0.001),
    ("Channel 1.5 m wide, average depth 0.25 m, current meter velocity 0.8 m/s. Discharge?", 0.3, 0.001),
    # percent saturation
    ("Measured DO is 7.8 mg/L at 18.6 C. What is the percent saturation?", 83.4, 0.3),
    ("Dissolved oxygen 10.2 mg/L in 12 °C water: what percent saturation is that?", 94.6, 0.3),
    # unit swaps
    ("Convert 450 uS/cm to mS/cm", 0.45, 0.0005),
    ("What is 1.8 mS/cm in µS/cm?", 1800, 0.5),
    # molar solutions
    ("How many grams of NaCl for 500 mL of 0.1 M solution?", 2.922, 0.003),
    ("How much KCl do I weigh out for 1 L of 0.01 M?", 0.7455, 0.001),
    # volume from a flow
    ("A 2 hour sample at 3 L per minute filtered how many liters?", 360, 0.5),
    ("The pump ran 45 minutes at 0.5 L/min. How much water went through the filter?", 22.5, 0.05),
    # traps: about a number, not a calculation -- code must not answer
    ("Is 412 uS/cm conductivity normal for a trout stream?", None, 0),
    ("Why would a float give a higher velocity than a current meter?", None, 0),
    ("What does percent saturation of dissolved oxygen tell me?", None, 0),
    ("My stock bottle says 1000 mg/L, how long does it keep?", None, 0),
]
