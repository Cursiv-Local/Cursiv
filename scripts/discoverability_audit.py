"""Read-only public-page audit; never queries private APIs or a visitor database.

  python scripts/discoverability_audit.py --output reports/discovery-before.json --live
  python scripts/discoverability_audit.py --output reports/discovery-after.json --live

User-agent probes cannot establish a request is verified Googlebot or reveal dashboard WAF rules.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
from io import BytesIO
import json
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ('/', '/start', '/local-ai', '/compare', '/documentation', '/local-ai-reference',
          '/notebook-reference', '/portable-ai-reference', '/open-source-offline-ai',
          '/local-ai-hardware-requirements', '/portable-workspace', '/field-research',
          '/offline-research', '/team-drives', '/field-station', '/ai-reliability-testing',
          '/vision', '/story', '/testers', '/privacy/')
EXCLUDED = ('/api/space/ask', '/api/space/join', '/api/space/messages?since=',
            '/api/space/create', '/api/space/image/', '/api/space/pair-code')
ICONS = ('/favicon.ico', '/favicon-96x96.png', '/apple-touch-icon.png', '/assets/cursiv-logo-256.png')
AGENTS = {
    'browser': 'Mozilla/5.0 CursivPublicAudit/1.0',
    'googlebot': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
    'googlebot-image': 'Googlebot-Image/1.0',
}


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title = ''
        self.headings = []
        self.canonical = []
        self.meta = {}
        self.icons = []
        self.schemas = []
        self._capture = None
        self._text = ''

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ('title', 'h1') or (tag == 'script' and a.get('type') == 'application/ld+json'):
            self._capture, self._text = tag, ''
        if tag == 'meta':
            self.meta[a.get('name', a.get('property', ''))] = a.get('content', '')
        if tag == 'link':
            rel = a.get('rel', '').split()
            if 'canonical' in rel:
                self.canonical.append(a.get('href'))
            if any('icon' in item for item in rel):
                self.icons.append(a)

    def handle_data(self, data):
        if self._capture:
            self._text += data

    def handle_endtag(self, tag):
        if self._capture != tag:
            return
        if tag == 'title':
            self.title = self._text.strip()
        elif tag == 'h1':
            self.headings.append(self._text.strip())
        elif tag == 'script':
            try:
                self.schemas.append(json.loads(self._text))
            except ValueError as exc:
                self.schemas.append({'parse_error': str(exc)})
        self._capture = None


def page_summary(body):
    page = Page()
    page.feed(body.decode('utf-8', errors='replace'))
    return dict(title=page.title, h1=page.headings, canonical=page.canonical,
                description=page.meta.get('description'), robots=page.meta.get('robots'),
                icons=page.icons, structured_data=page.schemas)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def fetch(url, agent='browser'):
    result = dict(requested_url=url, user_agent=agent, hops=[])
    opener = urllib.request.build_opener(NoRedirect)
    try:
        for _ in range(5):
            parsed = urllib.parse.urlsplit(url)
            if parsed.hostname not in ('cursiv.us', 'www.cursiv.us', 'cursiv.winklers-llc.com'):
                raise ValueError('Refusing non-product redirect: ' + url)
            if parsed.path.startswith(('/api/', '/remote/', '/admin/')):
                raise ValueError('Private endpoints are evaluated locally, never fetched')
            req = urllib.request.Request(url, headers={'User-Agent': AGENTS[agent], 'Cache-Control': 'no-cache'})
            try:
                response = opener.open(req, timeout=20)
            except urllib.error.HTTPError as exc:
                response = exc
            with response:
                headers = dict((k.lower(), v) for k, v in response.headers.items())
                result['hops'].append(dict(url=url, status=response.code, location=headers.get('location')))
                if response.code in (301, 302, 303, 307, 308) and headers.get('location'):
                    url = urllib.parse.urljoin(url, headers['location'])
                    continue
                body = response.read(2_000_000)
                result.update(final_url=url, status=response.code, content_type=headers.get('content-type'),
                              x_robots_tag=headers.get('x-robots-tag'),
                              challenge=headers.get('cf-mitigated'), sha256=hashlib.sha256(body).hexdigest())
                if 'text/html' in headers.get('content-type', ''):
                    result.update(page_summary(body))
                if urllib.parse.urlsplit(url).path in ('/robots.txt', '/llms.txt'):
                    result['text'] = body.decode('utf-8', errors='replace')
                if urllib.parse.urlsplit(url).path == '/sitemap.xml':
                    tree = ET.fromstring(body)
                    result['sitemap'] = [dict((node.tag.rsplit('}', 1)[-1], node.text) for node in row) for row in tree]
                if headers.get('content-type', '').startswith('image/'):
                    from PIL import Image
                    image = Image.open(BytesIO(body))
                    result['image'] = dict(format=image.format, size=image.size,
                                           ico_sizes=sorted(image.info.get('sizes', [])))
                break
        else:
            raise ValueError('Too many redirects')
    except Exception as exc:
        result['error'] = f'{type(exc).__name__}: {exc}'
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--live', action='store_true')
    args = parser.parse_args()
    local = {}
    for path in sorted((ROOT / 'website').glob('*.html')):
        local[path.relative_to(ROOT).as_posix()] = page_summary(path.read_bytes())
    for rel in ('notebook/index.html', 'privacy/index.html'):
        path = ROOT / 'website' / rel
        local[path.relative_to(ROOT).as_posix()] = page_summary(path.read_bytes())
    report = dict(checked_utc=datetime.now(timezone.utc).isoformat(), local_pages=local,
                  limits='Public HTTP access probes, not authenticated Search Console or verified crawler traffic.')
    if args.live:
        paths = (*PUBLIC, *ICONS, '/robots.txt', '/sitemap.xml', '/llms.txt',
                 '/notebook/', '/app', '/letters', '/?x=2', '/index.html', '/start.html')
        requests = [('https://cursiv.us' + path, 'browser') for path in paths]
        requests += [(url, 'browser') for url in ('http://cursiv.us/', 'https://www.cursiv.us/',
                                                  'http://www.cursiv.us/', 'https://cursiv.winklers-llc.com/')]
        requests += [('https://cursiv.us' + path, agent) for agent in ('googlebot', 'googlebot-image')
                     for path in ('/', *ICONS, '/robots.txt')]
        with ThreadPoolExecutor(max_workers=4) as pool:
            report['live'] = list(pool.map(lambda item: fetch(*item), requests))
        robots = next((row.get('text') for row in report['live']
                       if row['requested_url'] == 'https://cursiv.us/robots.txt' and row.get('text')), None)
        if robots is not None:
            rules = urllib.robotparser.RobotFileParser()
            rules.parse(robots.splitlines())
            report['robots_policy'] = {agent: {path: rules.can_fetch(AGENTS[agent], 'https://cursiv.us' + path)
                                              for path in (*PUBLIC, *ICONS, *EXCLUDED)}
                                       for agent in AGENTS}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    live = report.get('live', [])
    print(json.dumps(dict(output=str(args.output), local_pages=len(local), live_requests=len(live),
                          responses_200=sum(row.get('status') == 200 for row in live),
                          errors=sum('error' in row for row in live)), indent=2))


if __name__ == '__main__':
    main()
