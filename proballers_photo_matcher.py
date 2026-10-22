"""Match Proballers team-roster players to a local CSV and collect headshot URLs.

Install: pip install playwright rapidfuzz
         python -m playwright install chromium
Run:     python proballers_photo_matcher.py

This uses the normal browser UI. It does not bypass login, paywalls or bot protection.
"""
import csv
import json
import re
import time
import unicodedata
from collections import defaultdict
from pathlib import Path
from urllib.parse import quote_plus, urljoin, urlparse

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from rapidfuzz import fuzz

ROOT = Path(__file__).resolve().parent
INPUT = ROOT / 'players.csv'
OUTPUT = ROOT / 'players_with_headshots.csv'
REPORT = ROOT / 'headshot_match_report.csv'
CACHE = ROOT / 'proballers_photo_cache.json'

# Starting point supplied by the user. Add other team-roster URLs here to
# bypass web-search discovery when you have them.
TEAM_ROSTER_URLS = {
    'Real Madrid': 'https://www.proballers.com/basketball/team/160/real-madrid/roster',
}

# Only accept strong automatic matches. We also require distinctive name parts.
MIN_SCORE = 94
MAX_PROFILES_PER_TEAM = 65
DELAY_SECONDS = 1.0
HEADLESS = False  # visible browser; switch to True after confirming it works
OVERWRITE_EXISTING_PHOTOS = False


def norm(s):
    s = unicodedata.normalize('NFKD', s or '')
    s = ''.join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r'[^a-z0-9]+', ' ', s.casefold())
    return ' '.join(s.split())


def name_score(a, b):
    a, b = norm(a), norm(b)
    if not a or not b:
        return 0
    if a == b:
        return 100
    a_parts, b_parts = a.split(), b.split()
    # Initials and suffixes are often represented differently. The first and
    # last names must still have a plausible correspondence.
    common = set(a_parts) & set(b_parts)
    if len(common) < 2:
        return 0
    return round(max(fuzz.token_set_ratio(a, b), fuzz.ratio(a, b)), 1)


def load_cache():
    try:
        return json.loads(CACHE.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return {'rosters': {}, 'profiles': {}}


def save_cache(cache):
    CACHE.write_text(json.dumps(cache, indent=2, ensure_ascii=False), encoding='utf-8')


def goto(page, url):
    try:
        page.goto(url, wait_until='domcontentloaded', timeout=30000)
        page.wait_for_timeout(1100)
        return True
    except PlaywrightTimeout:
        print('  Page timed out:', url)
        return False
    except Exception as e:
        print('  Page error:', str(e)[:160])
        return False


def discover_roster(page, team):
    if team in TEAM_ROSTER_URLS:
        return TEAM_ROSTER_URLS[team]
    # Search engine results are only used to find a team URL; player identities
    # and images are taken from the Proballers pages themselves.
    query = f'site:proballers.com/basketball/team/ {team} roster proballers'
    if not goto(page, 'https://www.google.com/search?q=' + quote_plus(query)):
        return None
    links = page.locator('a[href]').evaluate_all(
        "els => els.map(a => ({url:a.href, text:a.innerText})).filter(x => x.url.includes('proballers.com/basketball/team/'))"
    )
    for item in links:
        url = item['url'].split('?')[0]
        if re.search(r'/basketball/team/\d+/[^/]+', url):
            return url.rstrip('/') + '/roster' if not url.endswith('/roster') else url
    return None


def roster_profiles(page, url):
    if not goto(page, url):
        return []
    if 'proballers.com' not in page.url:
        return []
    links = page.locator('a[href]').evaluate_all("""els => els.map(a => ({
        href:a.href, name:(a.innerText || a.getAttribute('title') ||
        a.querySelector('img')?.alt || '').trim()
    }))""")
    found = {}
    for item in links:
        href = item['href'].split('?')[0]
        if re.search(r'proballers\.com/basketball/player/\d+/', href):
            found[href] = item['name']
    return [{'url': u, 'roster_name': n} for u, n in found.items()][:MAX_PROFILES_PER_TEAM]


def profile_info(page, url):
    if not goto(page, url):
        return {'name': '', 'image': ''}
    data = page.evaluate("""() => {
      const metas = [...document.querySelectorAll('meta')];
      const meta = key => metas.find(x => x.getAttribute('property')===key || x.getAttribute('name')===key)?.content || '';
      const imgs = [...document.images].map(i=>({src:i.currentSrc||i.src, alt:i.alt||''}));
      const title = document.querySelector('h1')?.innerText || '';
      return {title, ogTitle:meta('og:title'), ogImage:meta('og:image'), imgs};
    }""")
    name = (data['title'] or data['ogTitle']).split(' - ')[0].strip()
    candidates = [data['ogImage']] + [x['src'] for x in data['imgs']]
    # Prioritize genuine player headshot URLs, not team logos or page banners.
    image = next((x for x in candidates if re.search(
        r'proballers\.com/media/cache/[^/]+/player/headshot/\d+\.(?:png|jpe?g|webp)', x or '', re.I
    )), '')
    if not image:
        image = next((x for x in candidates if re.search(
            r'/player/headshot/\d+\.(?:png|jpe?g|webp)', x or '', re.I
        )), '')
    return {'name': name, 'image': image}


def write_csv(path, rows, fields):
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main():
    if not INPUT.exists():
        print(f'Missing {INPUT}. Rename your latest CSV to players.csv and try again.')
        return
    with INPUT.open(encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []
        rows = list(reader)
    if not {'name', 'team', 'picture_url'}.issubset(fields):
        print('CSV must contain name, team and picture_url columns.')
        return

    cache = load_cache()
    teams = defaultdict(list)
    for idx, row in enumerate(rows):
        if not row['picture_url'].strip() or OVERWRITE_EXISTING_PHOTOS:
            teams[row['team']].append(idx)

    report = []
    updated = 0
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=HEADLESS)
        context = browser.new_context(viewport={'width': 1365, 'height': 900})
        page = context.new_page()
        try:
            for team, indices in teams.items():
                print(f'\nTEAM: {team} ({len(indices)} missing)')
                roster_url = cache['rosters'].get(team) or discover_roster(page, team)
                if not roster_url:
                    print('  No roster found. Add its URL to TEAM_ROSTER_URLS.')
                    for i in indices:
                        report.append({'team': team, 'player': rows[i]['name'], 'status': 'roster_not_found', 'matched_name': '', 'score': '', 'url': ''})
                    continue
                cache['rosters'][team] = roster_url
                profiles = roster_profiles(page, roster_url)
                print(f'  Roster: {roster_url}; profiles found: {len(profiles)}')
                if not profiles:
                    for i in indices:
                        report.append({'team': team, 'player': rows[i]['name'], 'status': 'roster_empty_or_blocked', 'matched_name': '', 'score': '', 'url': ''})
                    save_cache(cache)
                    continue

                # First compare names visible on the roster. Only fetch player
                # pages that have a plausible chance of matching CSV entries.
                for i in indices:
                    target = rows[i]['name']
                    choices = sorted(
                        ((name_score(target, p['roster_name'] or p['url'].split('/')[-1].replace('-', ' ')), p) for p in profiles),
                        key=lambda x: x[0], reverse=True
                    )
                    score, candidate = choices[0]
                    second = choices[1][0] if len(choices) > 1 else 0
                    if score < MIN_SCORE or (score - second < 4 and second >= MIN_SCORE):
                        report.append({'team': team, 'player': target, 'status': 'review_name', 'matched_name': candidate['roster_name'], 'score': score, 'url': candidate['url']})
                        continue
                    url = candidate['url']
                    info = cache['profiles'].get(url)
                    if info is None:
                        info = profile_info(page, url)
                        cache['profiles'][url] = info
                        time.sleep(DELAY_SECONDS)
                    verified_score = name_score(target, info['name'] or candidate['roster_name'])
                    if verified_score >= MIN_SCORE and info['image']:
                        rows[i]['picture_url'] = info['image']
                        updated += 1
                        status = 'matched'
                        print(f'  MATCH {target} -> {info["image"]}')
                    else:
                        status = 'review_profile_or_image'
                    report.append({'team': team, 'player': target, 'status': status, 'matched_name': info['name'], 'score': verified_score, 'url': url})
                save_cache(cache)
                # Save intermediate output after each team so interruptions
                # don't lose previous matches.
                write_csv(OUTPUT, rows, fields)
                write_csv(REPORT, report, ['team', 'player', 'status', 'matched_name', 'score', 'url'])
        finally:
            browser.close()
    write_csv(OUTPUT, rows, fields)
    write_csv(REPORT, report, ['team', 'player', 'status', 'matched_name', 'score', 'url'])
    print(f'\nDone. Added {updated} URLs. Total populated: {sum(bool(r["picture_url"].strip()) for r in rows)}/{len(rows)}')
    print('Updated CSV:', OUTPUT)
    print('Review report:', REPORT)


if __name__ == '__main__':
    main()
