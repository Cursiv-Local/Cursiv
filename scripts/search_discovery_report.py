"""Summarize owner-exported aggregate search data without changing site analytics.

  python scripts/search_discovery_report.py --gsc-csv Queries.csv --output reports/search-period.json
  python scripts/search_discovery_report.py --referrals-csv Referrals.csv --output reports/referrals.json

Use a Search Console Queries export for one date range (not a date-comparison export).
Missing exports are unavailable, never zero. Referrers cannot reveal hidden search queries.
No visitor IDs, IPs, cookies, raw search queries or individual events are emitted.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re
from urllib.parse import urlsplit

BRAND = re.compile(r'\bcursiv(?:ai)?\b', re.I)


def number(value):
    result = float(str(value or '0').replace(',', '').strip())
    if not math.isfinite(result):
        raise ValueError('Numbers must be finite')
    return result


def search_summary(rows):
    groups = {name: dict(query_rows=0, clicks=0, impressions=0, _position_sum=0,
                         _position_impressions=0) for name in ('branded', 'non_branded', 'unknown')}
    for row in rows:
        row = {key.strip().lower(): value for key, value in row.items() if key is not None}
        if not {'clicks', 'impressions'} <= row.keys() or not {'top queries', 'query', 'queries'} & row.keys():
            raise ValueError('Expected single-range Queries CSV with Clicks and Impressions columns')
        query = row.get('top queries', row.get('query', row.get('queries', ''))).strip()
        group = groups['branded' if BRAND.search(query) else 'non_branded' if query else 'unknown']
        clicks, impressions = number(row['clicks']), number(row['impressions'])
        if clicks < 0 or impressions < 0:
            raise ValueError('Counts must be nonnegative')
        group['query_rows'] += 1
        group['clicks'] += clicks
        group['impressions'] += impressions
        if row.get('position') and impressions:
            group['_position_sum'] += number(row['position']) * impressions
            group['_position_impressions'] += impressions
    for group in groups.values():
        group['ctr'] = group['clicks'] / group['impressions'] if group['impressions'] else None
        numerator, denominator = group.pop('_position_sum'), group.pop('_position_impressions')
        group['average_position'] = numerator / denominator if denominator else None
    return dict(status='measured export', brand_rule='Case-insensitive Cursiv/CursivAI word token, including cursiv.us and Cursiv-Local',
                groups=groups, limits='Exported query rows only; Google may omit anonymized/low-volume queries. Unknown rows are separate. Counts do not establish AI recommendations.')


def referral_channel(value):
    value = value.strip().lower()
    host = urlsplit(value if '://' in value else 'https://' + value).hostname or ''
    if any(host == domain or host.endswith('.' + domain) for domain in (
            'chatgpt.com', 'chat.openai.com', 'perplexity.ai', 'claude.ai', 'gemini.google.com', 'copilot.microsoft.com')):
        return 'ai_assistant'
    if (re.fullmatch(r'(?:[a-z0-9-]+\.)?google\.(?:com|[a-z]{2}|co\.[a-z]{2}|com\.[a-z]{2})', host)
            or any(host == domain or host.endswith('.' + domain) for domain in ('bing.com', 'duckduckgo.com', 'search.yahoo.com', 'search.brave.com'))):
        return 'search_engine'
    return 'other_or_unknown'


def referrals_summary(rows):
    groups = dict(ai_assistant=0, search_engine=0, other_or_unknown=0)
    for row in rows:
        row = {key.strip().lower(): value for key, value in row.items() if key is not None}
        source = row.get('referrer', row.get('source', ''))
        value = row.get('visitors', row.get('count'))
        if value is None or not {'referrer', 'source'} & row.keys():
            raise ValueError('Expected Referrer or Source plus Visitors or Count columns')
        count = number(value)
        if count < 0:
            raise ValueError('Counts must be nonnegative')
        groups[referral_channel(source)] += count
    return dict(status='measured export', channels=groups,
                limits='Referral channels do not reveal branded/non-branded search intent. Some apps strip referrers; unknown is not direct traffic proof.')


def read_rows(path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gsc-csv', type=Path)
    parser.add_argument('--referrals-csv', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    report = dict(checked_utc=datetime.now(timezone.utc).isoformat(),
                  search_console=search_summary(read_rows(args.gsc_csv)) if args.gsc_csv else {'status': 'unavailable; no export supplied'},
                  referrals=referrals_summary(read_rows(args.referrals_csv)) if args.referrals_csv else {'status': 'unavailable; no export supplied'})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
