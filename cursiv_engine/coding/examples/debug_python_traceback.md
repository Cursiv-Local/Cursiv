---
title: Read a Python traceback and fix the bug
triggers: traceback|exception|error|bug|crash|doesn.?t work|not working|TypeError|KeyError|IndexError|AttributeError|NameError|ValueError
---
## Question
(pasted)
```
Traceback (most recent call last):
  File "C:\Users\me\projects\shop\cart.py", line 14, in <module>
    print(total(items))
  File "C:\Users\me\projects\shop\cart.py", line 9, in total
    return sum(i["price"] * i["qty"] for i in items)
TypeError: can't multiply sequence by non-int of type 'float'
```

## Answer
### What went wrong
Read a traceback **from the bottom up**:
- Last line = the error: `TypeError: can't multiply sequence by non-int of type 'float'` — Python tried to multiply a **string** by a number. One of `price`/`qty` is text like `"2"` instead of the number `2` (common when data comes from a CSV, form, or `input()`).
- Line above = where: `cart.py`, line 9, inside `total`.
- Higher lines = how it got there (line 14 called `total`).

### Fix
Convert to numbers where the data comes in — or inside `total`:
```python
def total(items: list[dict]) -> float:
    return sum(float(i["price"]) * int(i["qty"]) for i in items)
```

### How to find this kind of bug yourself
1. Print the types right before the failing line:
```python
for i in items:
    print(repr(i["price"]), type(i["price"]), repr(i["qty"]), type(i["qty"]))
```
`repr` shows quotes around strings, so `'2'` vs `2` is obvious.
2. Run again:
```bash
python cart.py
```

### Common errors, quick meanings
- `NameError: name 'x' is not defined` → typo, or used before it was assigned/imported.
- `KeyError: 'price'` → that dict has no such key; print the dict to see real keys.
- `IndexError: list index out of range` → list shorter than you think; print `len(...)`.
- `AttributeError: 'NoneType' object has no attribute ...` → a function returned `None` (often forgot `return`).
- `ModuleNotFoundError` → package not installed in the Python you're running (activate the venv).
- `IndentationError` → mixed tabs/spaces or a missing indent after `:`.
