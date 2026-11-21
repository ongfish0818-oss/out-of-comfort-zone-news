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
            r.close()
        except requests.RequestException: pass
        if len(valid)==5: break
    return valid

def load_history():
    try: return json.loads(HISTORY.read_text())
    except (FileNotFoundError,ValueError): return {'posted_urls':[], 'post_dates':[]}

def eligible(items):
    prior=set(load_history()['posted_urls'])
    return [x for x in items if x['url'] not in prior]

def wrap(draw,text,ft,maxwidth):
    words=text.split();lines=[];line=''
    for word in words:
        nxt=(line+' '+word).strip()
        if draw.textbbox((0,0),nxt,font=ft)[2] <= maxwidth: line=nxt
        else:
            if line: lines.append(line)
            line=word
    if line:lines.append(line)
    return lines

def textlines(draw,text,xy,size,maxwidth,fill,bold=False,spacing=13,maxlines=None):
    ft=font(size,bold);lines=wrap(draw,text,ft,maxwidth)
    if maxlines and len(lines)>maxlines:
        lines=lines[:maxlines];lines[-1]=lines[-1].rstrip(' .')+'…'
    x,y=xy
    for line in lines:
        draw.text((x,y),line,font=ft,fill=fill,stroke_width=0)
        y+=size+spacing
    return y

def base():
    img=Image.new('RGB',(W,H));pixels=img.load()
    for y in range(H):
        t=y/(H-1); color=(int(12+16*t),int(31+17*t),int(57+16*t))
        ImageDraw.Draw(img).line([(0,y),(W,y)],fill=color)
    d=ImageDraw.Draw(img)
    d.polygon([(810,0),(1080,0),(1080,420)],fill=(34,57,76))
    d.rectangle((0,0,18,H), fill=(225,53,67))
    return img,d

def decorative(d,number):
    # Original vector motif: no reused copyrighted article photos.
    d.rounded_rectangle((90,810,990,1160),radius=38,fill=(30,67,93),outline=(70,112,135),width=4)
    bars=[100,160,210,260,330]
    for k,h in enumerate(bars):
        d.rounded_rectangle((230+k*120,1100-h,295+k*120,1100),radius=12, fill=(65+22*k,152+12*k,167+5*k))
    d.line([(250,1060),(385,990),(510,1010),(660,860),(795,835)],fill=(239,94,97),width=18,joint='curve')
    d.polygon([(795,835),(746,850),(772,892)], fill=(239,94,97))
    d.text((110,1210),'ORIGINAL EDITORIAL GRAPHIC  •  NOT ARTICLE PHOTOGRAPHY',font=font(19),fill=(174,201,214))

def render(items,out_dir,day):
    out_dir.mkdir(parents=True,exist_ok=True)
    files=[]
    for i in range(6):
        im,d=base()
        d.text((85,75),'OUT OF COMFORT ZONE',font=font(38,True),fill='white')
        d.rectangle((85,142,340,154),fill=(237,66,76))
        if i==0:
            y=textlines(d,'MALAYSIA TOP 5', (85,260),76,900,'white',True,19)
            y=textlines(d,'BUSINESS NEWS', (85,y+8),78,900,(255,110,112),True,19)
            d.text((88,y+75),day.strftime('%d %B %Y').upper(),font=font(35),fill=(210,226,237))
            d.text((88,y+160),'Five verified business headlines',font=font(31),fill='white')
            d.text((88,1220),'SWIPE TO READ  →',font=font(37,True),fill='white')
            d.text((88,1280),'Independent summaries • Source: The Edge Malaysia',font=font(20),fill=(192,213,226))
            decorative_cover(d)
        else:
            article=items[i-1]
            d.rounded_rectangle((83,195,420,260),radius=20,fill=(222,53,68))
            d.text((102,206),f'STORY {i} OF 5',font=font(32,True),fill='white')
            y=textlines(d,article['title'],(84,310),52,920,'white',True,15,maxlines=5)
            summary=article['summary']
            y=textlines(d,summary,(86,y+27),28,905,(224,236,239),False,12,maxlines=5)
            d.text((85,740),f"Published: {dt.datetime.fromisoformat(article['published']).strftime('%d %b %Y')}",font=font(27),fill=(210,230,237))
            decorative(d,i)
        fname=f'{i+1:02d}_'+('cover' if i==0 else 'story')+'.jpg'
        im.save(out_dir/fname,quality=88,subsampling=0)
        files.append(fname)
    return files

def decorative_cover(d):
    for n in range(10):
        x=100+n*100; yy=1080-(n*28) + (n%3)*30
        d.rounded_rectangle((x,yy,x+55,1220),radius=10,fill=(49+n*10,110+n*7,130+n*4))
    d.line([(110,1120),(270,1060),(450,1080),(625,935),(860,880)],fill=(250,97,101),width=20)

def caption(items,day):
    lines=[f"🇲🇾 MALAYSIA TOP 5 BUSINESS NEWS | {day.strftime('%d %b %Y')}",'',
           'Independent daily briefing by Out of Comfort Zone.']
    for i,x in enumerate(items,1):
        lines.extend(['',f"{i}. {x['title']}",x['summary'][:200],f"Source: {x['url']}"])
    lines += ['', 'Independent feed-based summaries from The Edge Malaysia. Article links are plain text and may not be clickable in Instagram captions.',
              '#MalaysiaBusiness #BursaMalaysia #MalaysiaEconomy #BusinessNews #OutOfComfortZone']
    result='\n'.join(lines)
    if len(result)>2200:
        # Preserve links and headlines: shorten story summary by design.
        for x in items:x['summary']=x['summary'][:110].rsplit(' ',1)[0]+'…'
        result='\n'.join(lines[:3]+[part for i,x in enumerate(items,1) for part in ['',f"{i}. {x['title']}",x['summary'],x['url']]]+lines[-2:])
    if len(result)>2200: raise RuntimeError('Caption exceeds Instagram 2200-character limit')
    return result

def prepare(demo=False, date=None):
    day=dt.date.fromisoformat(date) if date else now_my().date()
    if demo:
        source=json.loads((ROOT/'tests'/'fixtures.json').read_text())
    else:
        source=feed_items()
        source=eligible(source)
        source=validate_source_pages(source)
        if len(source)<5: raise RuntimeError(f'Safety stop: only {len(source)} recent, distinct, source-confirmed items (need five)')
    selected=source[:5]
    if len(selected)!=5: raise RuntimeError('Exactly five source-confirmed stories required')
    out=DOCS/day.isoformat();out.mkdir(parents=True,exist_ok=True)
    files=render(selected,out,day)
    cap=caption(selected,day)
    (out/'caption.txt').write_text(cap,encoding='utf8')
    (out/'manifest.json').write_text(json.dumps({'date':day.isoformat(),'demo':demo,'account':'outofcomfortzone.daily','images':files,'articles':selected},indent=2,ensure_ascii=False),encoding='utf8')
    print(f"Prepared {out} (DEMO={demo}; NO publication)")

def graph(method,path,token,params=None):
    version=os.getenv('META_API_VERSION','v24.0')
    url=f'https://graph.instagram.com/{version}/{path.lstrip("/")}'
    payload={'access_token':token,**(params or {})}
    r=requests.request(method,url,params=payload if method=='GET' else None,data=payload if method!='GET' else None,timeout=30)
    try: data=r.json()
    except ValueError:raise RuntimeError(f'Meta invalid response HTTP {r.status_code}')
    if r.status_code>=400 or 'error' in data:raise RuntimeError(f'Meta HTTP {r.status_code}: {json.dumps(data.get("error",data))[:500]}')
    return data

def wait_ready(id,token,timeout=180):
    until=time.monotonic()+timeout
    while time.monotonic()<until:
        status=graph('GET',id,token,{'fields':'status_code'}).get('status_code')
        if status=='FINISHED':return
        if status in ('ERROR','EXPIRED'):raise RuntimeError(f'Meta container {id} {status}')
        time.sleep(12)
    raise RuntimeError(f'Meta container {id} did not become ready')

def publish(date):
    # Strict explicit opt-ins. This mode is deliberately not invoked in dry-run.
    if os.getenv('ENABLE_PUBLISH')!='true' or os.getenv('RIGHTS_CONFIRMED')!='true':
        raise RuntimeError('Publishing locked: ENABLE_PUBLISH and RIGHTS_CONFIRMED must both equal true')
    token=os.environ['IG_ACCESS_TOKEN']; igid=os.environ['IG_USER_ID']
    host=os.environ['PAGES_BASE_URL'].rstrip('/')
    folder=DOCS/date
    manifest=json.loads((folder/'manifest.json').read_text())
    if manifest.get('demo') or manifest.get('date')!=date:raise RuntimeError('Refuse demo or wrong-date post')
    history=load_history()
    if date in history['post_dates']:raise RuntimeError('Already published on this date; refuse duplicate')
    # Check account timeline too: protects against Meta succeeding but history commit failing.
    recent=graph('GET',f'{igid}/media',token,{'fields':'id,caption,timestamp','limit':'25'}).get('data',[])
    if any(f'OOCZ-{date}' in (post.get('caption') or '') for post in recent):
        raise RuntimeError('This date is already visible on Instagram; refuse duplicate')
    files=manifest['images'];articles=manifest['articles']
    if len(files)!=6 or len(articles)!=5:raise RuntimeError('Refuse incomplete carousel')
    caption_text=(folder/'caption.txt').read_text(encoding='utf8')
    caption_text += f'\n\nEdition: OOCZ-{date}'
    if len(caption_text)>2200: raise RuntimeError('Caption exceeds limit with edition marker')
    children=[]
    for name in files:
        img_url=f'{host}/daily/{date}/{name}'
        r=requests.get(img_url,timeout=20)
        if r.status_code!=200 or not r.headers.get('Content-Type','').startswith('image/'):
            raise RuntimeError(f'Image not publicly ready: {img_url} ({r.status_code})')
        child=graph('POST',f'{igid}/media',token,{'image_url':img_url,'is_carousel_item':'true'})['id']
        wait_ready(child,token);children.append(child)
    parent=graph('POST',f'{igid}/media',token,{'media_type':'CAROUSEL','children':','.join(children),'caption':caption_text})['id']
    wait_ready(parent,token)
    posted=graph('POST',f'{igid}/media_publish',token,{'creation_id':parent})['id']
    # Only commit history AFTER Meta confirms successful publication.
    history['posted_urls']=(history['posted_urls']+[x['url'] for x in articles])[-500:]
    history['post_dates']=(history['post_dates']+[date])[-180:]
    HISTORY.write_text(json.dumps(history,indent=2)+'\n')
    print(f'Published carousel id={posted} date={date}')

def main():
    p=argparse.ArgumentParser();p.add_argument('command',choices=['prepare','publish']);p.add_argument('--demo',action='store_true');p.add_argument('--date');a=p.parse_args()
    if a.command=='prepare':prepare(a.demo,a.date)
    else:publish(a.date or now_my().date().isoformat())
if __name__=='__main__':
    try:main()
    except Exception as e:
        print(f'ERROR: {e}',file=sys.stderr);sys.exit(1)
