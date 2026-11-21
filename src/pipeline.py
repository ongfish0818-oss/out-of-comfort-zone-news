"""Out of Comfort Zone: licensed-feed RSS -> verify -> original carousel -> Meta API.

No login automation, paywall bypass, article scraping, or image reuse.
Live mode refuses publication unless the user expressly enables it and confirms rights.
"""
from __future__ import annotations
import argparse, datetime as dt, html, json, os, re, sys, textwrap, time
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

try:
    import feedparser
except ImportError:
    feedparser = None  # Safe offline demo works without feedparser; live feed needs it.
import requests
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
DOCS = ROOT / 'docs' / 'daily'
TZ = ZoneInfo('Asia/Kuala_Lumpur')
FEED = os.getenv('EDGE_FEED_URL') or 'https://myassets.theedgemalaysia.com/arc/outboundfeeds/rss'
HISTORY = DATA / 'history.json'
ALLOWED = ('theedgemalaysia.com', 'www.theedgemalaysia.com')
KEYS = {'economy':8,'gdp':9,'bursa':10,'klci':9,'bank negara':10,'policy':7,'government':6,'investment':7,'corporate':5,'earnings':7,'profit':6,'semiconductor':6,'data centre':7,'ringgit':8,'trade':6,'budget':6,'inflation':8}
W,H = 1080,1350
BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
REG = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'

def font(size, bold=False):
    p = BOLD if bold else REG
    if not Path(p).exists():
        p = '/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf' if bold else '/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf'
    return ImageFont.truetype(p, size)

def now_my(): return dt.datetime.now(TZ)

def clean(s):
    s = re.sub(r'<[^>]*>', ' ', str(s or ''))
    return re.sub(r'\s+', ' ', html.unescape(s)).strip()

def is_original_article(url):
    p=urlparse(url)
    return p.scheme=='https' and (p.hostname or '').lower() in ALLOWED and bool(re.search(r'/node/\d+|/article/', p.path))

def feed_items(max_age_hours=40, session=None, now=None):
    """Use official publisher feed metadata only, NOT article text extraction."""
    if feedparser is None: raise RuntimeError('Install feedparser for live RSS mode')
    session = session or requests.Session()
    resp=session.get(FEED, timeout=25, headers={'User-Agent':'OutOfComfortZoneNewsBrief/1.0 (respectful RSS reader)', 'Accept':'application/rss+xml, application/atom+xml, application/xml;q=0.9, text/xml;q=0.8'})
    # Report the actual response without printing full copyrighted article text or credentials.
    print(f'Feed diagnostic: HTTP {resp.status_code}; final URL={resp.url}; content type={resp.headers.get("Content-Type","unknown")}; bytes={len(resp.content)}', flush=True)
    resp.raise_for_status()
    payload = resp.content.lstrip(b'\xef\xbb\xbf \t\r\n')
    if not (payload.startswith(b'<?xml') or payload.startswith(b'<rss') or payload.startswith(b'<feed') or payload.startswith(b'<rdf:RDF')):
        label = 'HTML website/login/challenge' if b'<html' in payload[:500].lower() or b'<!doctype html' in payload[:500].lower() else 'non-XML content'
        raise RuntimeError(f'RSS endpoint returned {label}, not a feed. Check EDGE_FEED_URL; current URL: {resp.url}. No articles were created.')
    parsed=feedparser.parse(resp.content)
    if parsed.bozo and not parsed.entries:
        reason = str(getattr(parsed, 'bozo_exception', 'unknown parser error'))
        raise RuntimeError(f'Feed XML parse failed ({reason}); URL: {resp.url}')
    if not parsed.entries:
        raise RuntimeError(f'Feed contains zero usable entries; verify that {resp.url} is an active publisher-approved RSS endpoint')
    now=now or now_my()
    items=[]
    for e in parsed.entries:
        link=e.get('link','').split('?')[0]
        if not is_original_article(link): continue
        pub=e.get('published_parsed') or e.get('updated_parsed')
        if not pub: continue
        pub_time=dt.datetime(*pub[:6],tzinfo=dt.timezone.utc).astimezone(TZ)
        age=(now-pub_time).total_seconds()/3600
        if age < -2 or age > max_age_hours: continue
        title=clean(e.get('title',''))
        summary=clean(e.get('summary') or e.get('description') or '')
        # Do not fabricate a summary from a title, or publish too little evidence.
        if len(title)<18 or len(summary)<70: continue
        summary=summary[:400].rsplit(' ',1)[0] if len(summary)>400 else summary
        items.append({'title':title, 'summary':summary, 'url':link, 'published':pub_time.isoformat(),
                      'source':'The Edge Malaysia', 'score':sum(v for k,v in KEYS.items() if k in (title+' '+summary).lower())})
    seen=set();out=[]
    for item in sorted(items,key=lambda z:(z['score'],z['published']),reverse=True):
        if item['url'] in seen: continue
        seen.add(item['url']);out.append(item)
    return out

def validate_source_pages(items, session=None):
    """Confirm articles exist at the publisher; do not scrape their copyrighted full text."""
    session=session or requests.Session()
    valid=[]
    for item in items:
        try:
            r=session.get(item['url'],timeout=18,headers={'User-Agent':'OutOfComfortZoneNewsBrief/1.0'},stream=True,allow_redirects=True)
            if r.status_code==200 and (r.url.startswith('https://theedgemalaysia.com/') or r.url.startswith('https://www.theedgemalaysia.com/')):
                valid.append(item)
