---
title: Pull information from a web page (requests + BeautifulSoup)
triggers: scrap(e|ing)|beautifulsoup|bs4|web page data|extract from (a )?(website|page)|parse html|crawl
---
## Question
How do I grab all the headlines from a news page?

## Answer
First check: does the site offer an API or RSS feed? Use that if it does — it's more reliable and allowed. Respect the site's terms and `robots.txt`, and don't hammer it with requests.

### Setup (venv active)
```bash
pip install requests beautifulsoup4
```

### The program
**headlines.py**
```python
import sys

import requests
from bs4 import BeautifulSoup

URL = sys.argv[1] if len(sys.argv) > 1 else "https://news.ycombinator.com/"
HEADERS = {"User-Agent": "Mozilla/5.0 (personal script)"}

r = requests.get(URL, headers=HEADERS, timeout=20)
r.raise_for_status()
soup = BeautifulSoup(r.text, "html.parser")

# Find the right selector: right-click a headline in the browser -> Inspect,
# and note its tag/class. For Hacker News it's <span class="titleline"><a>.
links = soup.select("span.titleline > a") or soup.select("h2 a, h3 a")
for n, a in enumerate(links[:30], 1):
    print(f"{n:2}. {a.get_text(strip=True)}\n    {a.get('href')}")
if not links:
    print("No headlines found — the selector doesn't match this site. Inspect the page and update it.")
```

### Run it
```bash
python headlines.py
```
**Success:** a numbered list of titles with links.

### If something goes wrong
- Empty list → the page is built by JavaScript after loading (requests only sees the raw HTML). Look for the site's API in the browser's Network tab (F12), or use Playwright (`pip install playwright`, then `playwright install chromium`).
- `403 Forbidden` → the site blocks scripts; use its API/RSS instead.
- Garbled characters → `r.encoding = r.apparent_encoding` before parsing.
