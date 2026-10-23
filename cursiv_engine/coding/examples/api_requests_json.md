---
title: Call a web API and use the JSON (with keys kept out of the code)
triggers: \bapi\b|requests|json|fetch data|weather|http get|rest|api key|\.env
---
## Question
How do I get data from an API in Python, like the weather?

## Answer
**Where:** your project folder, venv active (see "Start a new Python project").

### Setup (once, inside the venv)
```bash
pip install requests python-dotenv
```

### Keep the key out of your code
Create a file named `.env` in the project folder:
```
WEATHER_API_KEY=paste-your-key-here
```
Add `.env` to `.gitignore` so it's never uploaded.

### The program
**weather.py** (uses Open-Meteo, which needs no key; shows where a key would go)
```python
import os
import sys

import requests
from dotenv import load_dotenv

load_dotenv()                                   # reads .env into os.environ
API_KEY = os.getenv("WEATHER_API_KEY")          # unused by Open-Meteo, shown for keyed APIs


def forecast(lat: float, lon: float) -> dict:
    r = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={"latitude": lat, "longitude": lon, "current": "temperature_2m,wind_speed_10m",
                "temperature_unit": "fahrenheit"},
        timeout=15,
    )
    r.raise_for_status()                        # turns 4xx/5xx into a clear error
    return r.json()


if __name__ == "__main__":
    lat, lon = (float(sys.argv[1]), float(sys.argv[2])) if len(sys.argv) == 3 else (39.96, -82.99)
    try:
        data = forecast(lat, lon)
    except requests.RequestException as e:
        sys.exit(f"Couldn't reach the weather service: {e}")
    cur = data["current"]
    print(f"Now: {cur['temperature_2m']}°F, wind {cur['wind_speed_10m']} mph")
```

### Run it
```bash
python weather.py
```
or with your coordinates: `python weather.py 40.71 -74.01`.
**Success:** `Now: 61.3°F, wind 7.2 mph`.

### If something goes wrong
- `No module named 'requests'` → venv not active, or install step skipped.
- `401 Unauthorized` (keyed APIs) → key missing/wrong in `.env`; check `print(API_KEY is not None)`.
- `429 Too Many Requests` → you hit the rate limit; wait or slow down.
- `KeyError` on the JSON → print `data` once to see the real structure; APIs differ.
