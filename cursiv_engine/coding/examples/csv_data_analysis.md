---
title: Analyze a CSV / Excel file with pandas and make a chart
triggers: csv|excel|xlsx|spreadsheet|pandas|data analysis|chart|graph|plot|matplotlib|budget|totals
---
## Question
I have a CSV of expenses. How do I total them by category and make a chart?

## Answer
**Where:** project folder, venv active.

### Setup (once)
```bash
pip install pandas matplotlib openpyxl
```
(`openpyxl` is only needed for .xlsx files.)

### Example data — `expenses.csv`
```
date,category,amount
2026-09-01,Groceries,84.20
2026-09-03,Gas,41.00
2026-09-07,Groceries,63.75
2026-09-10,Kids,25.00
```

### The program
**report.py**
```python
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")              # save to a file; works without a display (WSL too)
import matplotlib.pyplot as plt
import pandas as pd

path = Path(sys.argv[1] if len(sys.argv) > 1 else "expenses.csv")
df = pd.read_excel(path) if path.suffix.lower() in (".xlsx", ".xls") else pd.read_csv(path)

df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
bad = df["amount"].isna().sum()
if bad:
    print(f"Skipping {bad} row(s) with a non-number amount")
df = df.dropna(subset=["amount"])

totals = df.groupby("category")["amount"].sum().sort_values(ascending=False)
print(totals.to_string(float_format=lambda v: f"${v:,.2f}"))
print(f"\nTotal: ${totals.sum():,.2f}")

ax = totals.plot(kind="bar", title="Spending by category")
ax.set_ylabel("Dollars")
plt.tight_layout()
plt.savefig("spending.png", dpi=150)
print("Chart saved to spending.png")
```

### Run it
```bash
python report.py expenses.csv
```
**Success:** a table of totals per category, the grand total, and `spending.png` in the folder (open it: `start spending.png` in PowerShell, `explorer.exe spending.png` in WSL).

### If something goes wrong
- `KeyError: 'amount'` → your column names differ; `print(df.columns)` and change the names in the script.
- `UnicodeDecodeError` → add `encoding="latin-1"` to `read_csv`.
- Amounts with `$` signs → before `to_numeric`: `df["amount"] = df["amount"].astype(str).str.replace(r"[$,]", "", regex=True)`.
