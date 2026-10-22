"""Proballers roster headshot collector. pip install playwright rapidfuzz; python -m playwright install chromium"""
import csv, json, re, time, unicodedata
from collections import defaultdict
from pathlib import Path
from urllib.parse import quote_plus, unquote, urlparse, parse_qs
from playwright.sync_api import sync_playwright
from rapidfuzz import fuzz

ROOT=Path(__file__).resolve().parent
INPUT=ROOT/'players.csv'
OUTPUT=ROOT/'players_with_headshots.csv'
REPORT=ROOT/'headshot_match_report.csv'
CACHE=ROOT/'proballers_photo_cache.json'
ROSTER_URLS={
    'Anadolu Efes Istanbul': 'https://www.proballers.com/basketball/team/543/anadolu-efes-istanbul/roster',
    'Armani Olimpia Milan': 'https://www.proballers.com/basketball/team/178/armani-olimpia-milan/roster',
    'Besiktas Istanbul': 'https://www.proballers.com/basketball/team/545/besiktas-istanbul/roster',
    'Crvena Zvezda Meridianbet Belgrade': 'https://www.proballers.com/basketball/team/561/crvena-zvezda-belgrade/roster',
    'Dubai Basketball': 'https://www.proballers.com/basketball/team/15350/dubai-basketball/roster',
    'FC Barcelona': 'https://www.proballers.com/basketball/team/148/fc-barcelona/roster',
    'FC Bayern Munich': 'https://www.proballers.com/basketball/team/2020/fc-bayern-munich/roster',
    'Fenerbahce Tarfin Istanbul': 'https://www.proballers.com/basketball/team/552/fenerbahce-istanbul/roster',
    'Hapoel IBI Tel Aviv': 'https://www.proballers.com/basketball/team/776/hapoel-tel-aviv/roster',
    'Kosner Baskonia Vitoria-Gasteiz': 'https://www.proballers.com/basketball/team/155/baskonia-vitoria-gasteiz/roster',
    'LDLC ASVEL Villeurbanne': 'https://www.proballers.com/basketball/team/1/ldlc-asvel/roster',
    'Maccabi Rapyd Tel Aviv': 'https://www.proballers.com/basketball/team/609/maccabi-rapyd-tel-aviv/roster',
    'Olympiacos Piraeus': 'https://www.proballers.com/basketball/team/188/olympiacos-piraeus/roster',
    'Panathinaikos AKTOR Athens': 'https://www.proballers.com/basketball/team/185/panathinaikos-athens/roster',
    'Paris Basketball': 'https://www.proballers.com/basketball/team/13219/paris/roster',
    'Partizan Mozzart Bet Belgrade': 'https://www.proballers.com/basketball/team/565/partizan-belgrade/roster',
    'Real Madrid': 'https://www.proballers.com/basketball/team/160/real-madrid/roster',
    'Valencia Basket': 'https://www.proballers.com/basketball/team/153/valencia-basket/roster',
    'Virtus Bologna': 'https://www.proballers.com/basketball/team/165/virtus-bologna/roster',
    'Zalgiris Kaunas': 'https://www.proballers.com/basketball/team/649/zalgiris-kaunas/roster',
}
# All 20 team URLs are supplied explicitly; no search-engine discovery is needed.
MIN_SCORE=91
DELAY=0.5

def norm(s):
 s=unicodedata.normalize('NFKD',s or '')
 s=''.join(c for c in s if not unicodedata.combining(c))
 return ' '.join(re.sub(r'[^a-z0-9]+',' ',s.casefold()).split())

def score(a,b):
 a,b=norm(a),norm(b)
 if not a or not b:return 0
 if a==b:return 100
 if len(set(a.split())&set(b.split()))<2:return 0
 return round(fuzz.token_set_ratio(a,b),1)

def visit(page,url):
 try:
  response=page.goto(url,wait_until='domcontentloaded',timeout=35000)
  page.wait_for_timeout(850)
  return response is None or response.status<400
 except Exception as e:
  print('  Navigation failed:',str(e)[:100]);return False

def roster_links(page):
 return page.locator('a[href]').evaluate_all('''els=>els.map(a=>({url:a.href,name:(a.innerText||a.getAttribute('title')||a.querySelector('img')?.alt||'').trim()})).filter(x=>/proballers\\.com\\/basketball\\/player\\/\\d+\\//.test(x.url))''')

def roster_url_from_search(page,team,players):
 # Search by team AND a distinctive known player, to reduce wrong-team hits.
 for engine in ('https://www.bing.com/search?q=','https://www.google.com/search?q='):
  query='site:proballers.com/basketball/team/ '+team+' roster'
  if not visit(page,engine+quote_plus(query)):continue
  links=page.locator('a[href]').evaluate_all('els=>els.map(a=>a.href)')
  for link in links:
   link=unquote(link)
   m=re.search(r'https?://(?:www\.)?proballers\.com/basketball/team/\d+/[a-z0-9-]+(?:/roster)?',link,re.I)
   if m:
    candidate=m.group(0).split('?')[0].rstrip('/')
    if not candidate.endswith('/roster'):candidate+='/roster'
    # Don't blindly trust search results: ensure roster contains known player.
    if visit(page,candidate):
     found=roster_links(page)
     if any(score(p,x['name'])>=MIN_SCORE for p in players for x in found):return candidate
 return None

def headshot(page,player_url):
 if not visit(page,player_url):return ''
 images=page.evaluate('''() => [document.querySelector('meta[property="og:image"]')?.content,...[...document.images].map(i=>i.currentSrc||i.src)].filter(Boolean)''')
 for u in images:
  m=re.search(r'/player/headshot/(\d+)\.(?:png|jpg|jpeg|webp)',u,re.I)
  if m:return 'https://www.proballers.com/media/cache/headshot_600/player/headshot/'+m.group(1)+'.png'
 return ''

def save(path,rows,fields):
 with path.open('w',newline='',encoding='utf-8-sig') as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)

def main():
 if not INPUT.exists():raise SystemExit('Missing players.csv')
 with INPUT.open(newline='',encoding='utf-8-sig') as f:
  reader=csv.DictReader(f);fields=reader.fieldnames;rows=list(reader)
 teams=defaultdict(list)
 for i,row in enumerate(rows):
  if not (row.get('picture_url') or '').strip():teams[row['team']].append(i)
 try:cache=json.loads(CACHE.read_text(encoding='utf-8'))
 except (OSError,ValueError):cache={'rosters':{},'profiles':{}}
 cache.setdefault('rosters',{});cache.setdefault('profiles',{})
 report=[];added=0
 with sync_playwright() as p:
  browser=p.chromium.launch(headless=False)
  context=browser.new_context(viewport={'width':1400,'height':900})
  page=context.new_page()
  try:
   for team,indices in teams.items():
    print(f'\\nTEAM {team}: {len(indices)} missing')
    url=ROSTER_URLS.get(team) or cache['rosters'].get(team)
    if not url:url=roster_url_from_search(page,team,[rows[i]['name'] for i in indices])
    if not url:
     print('  Roster URL not found; add to ROSTER_URLS dictionary')
     report.extend({'team':team,'player':rows[i]['name'],'status':'roster_not_found','match':'','url':''} for i in indices)
     continue
    cache['rosters'][team]=url
    if not visit(page,url):
     print('  Roster inaccessible:',url);continue
    raw=roster_links(page)
    profiles={}
    for x in raw:profiles[x['url'].split('?')[0]]=x['name']
    print('  Roster:',url,'profiles:',len(profiles))
    if not profiles:continue
    for i in indices:
     name=rows[i]['name']
     ranked=sorted(((score(name,n or u.split('/')[-1].replace('-',' ')),u,n) for u,n in profiles.items()),reverse=True)
     best,u,n=ranked[0]
     second=ranked[1][0] if len(ranked)>1 else 0
     if best<MIN_SCORE or (best-second<4 and second>=MIN_SCORE):
      report.append({'team':team,'player':name,'status':'review_name','match':n,'url':u});continue
     image=cache['profiles'].get(u)
     if image is None:
      image=headshot(page,u);cache['profiles'][u]=image;time.sleep(DELAY)
     if image:
      rows[i]['picture_url']=image;added+=1;status='matched'
      print('  MATCH',name,'->',image)
     else:status='image_not_found'
     report.append({'team':team,'player':name,'status':status,'match':n,'url':u})
    save(OUTPUT,rows,fields)
    save(REPORT,report,['team','player','status','match','url'])
    CACHE.write_text(json.dumps(cache,ensure_ascii=False,indent=2),encoding='utf-8')
  finally:browser.close()
 save(OUTPUT,rows,fields)
 save(REPORT,report,['team','player','status','match','url'])
 print(f'\\nAdded {added}; total with URLs {sum(bool(r.get("picture_url")) for r in rows)}/{len(rows)}')
 print('Output:',OUTPUT)

if __name__=='__main__':main()
