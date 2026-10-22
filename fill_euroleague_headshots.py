"""Fill picture_url from EuroLeague's season people feed; never guess photo URLs.
Usage: pip install requests; python fill_euroleague_headshots.py
Place alongside players_2026_27_rebuilt.csv. Review the match report before importing.
"""
import csv
import re
import unicodedata
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import urlparse
import requests

HERE = Path(__file__).resolve().parent
INPUT = HERE / 'players.csv'
OUTPUT = HERE / 'players_with_headshots.csv'
REPORT = HERE / 'headshot_match_report.csv'
SEASONS = ['E2026', 'E2025', 'E2024', 'E2023']
URL = 'https://api-live.euroleague.net/v2/competitions/E/seasons/{season}/people'

def norm(value):
    value = unicodedata.normalize('NFKD', str(value or ''))
    value = ''.join(c for c in value if not unicodedata.combining(c))
    return ' '.join(re.findall(r'[a-z0-9]+', value.lower()))

def unpack(row):
    person = row.get('person') if isinstance(row.get('person'), dict) else row
    if not isinstance(person, dict):
        return None
    name = (person.get('name') or person.get('fullName') or person.get('displayName')
            or row.get('player_name') or row.get('playerName'))
    if isinstance(name, dict):
        name = name.get('fullName') or name.get('displayName') or name.get('name')
    if not name:
        first = person.get('firstName') or ''
        last = person.get('lastName') or ''
        name = f'{first} {last}'.strip()
    photo = (row.get('player_image_url') or row.get('imageUrl') or row.get('image')
             or person.get('imageUrl') or person.get('image') or person.get('photoUrl'))
    if isinstance(photo, dict):
        photo = photo.get('url')
    if not isinstance(photo, str) or not photo.startswith('https://'):
        return None
    if not name:
        return None
    return {'name': name, 'photo': photo}

def fetch_season(season):
    entries = []
    for offset in range(0, 3000, 200):
        response = requests.get(URL.format(season=season), params={'limit': 200, 'offset': offset}, timeout=30)
        response.raise_for_status()
        payload = response.json()
        data = payload.get('data', []) if isinstance(payload, dict) else payload
        if not isinstance(data, list):
            raise ValueError(f'Unexpected {season} response: expected a list under data')
        for raw in data:
            if isinstance(raw, dict):
                item = unpack(raw)
                if item:
                    item['season'] = season
                    entries.append(item)
        if len(data) < 200:
            break
    print(f'{season}: {len(entries)} records with photos')
    return entries

def main():
    with INPUT.open(encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        columns = reader.fieldnames
        players = list(reader)
    if not columns or 'picture_url' not in columns:
        raise ValueError('CSV must contain picture_url column')
    records = []
    for season in SEASONS:
        try:
            records.extend(fetch_season(season))
        except (requests.RequestException, ValueError) as e:
            print(f'Could not load {season}: {e}')
    if not records:
        raise RuntimeError('No EuroLeague image records retrieved. Original CSV unchanged.')
    by_name = defaultdict(list)
    for record in records:
        by_name[norm(record['name'])].append(record)
    report = []
    used = 0
    for player in players:
        if player.get('picture_url', '').strip():
            report.append([player['name'], 'existing', '', player['picture_url'], ''])
            continue
        key = norm(player['name'])
        matches = by_name.get(key, [])
        match = matches[0] if matches else None
        status = 'exact' if match else 'unmatched'
        suggestion = ''
        if not match:
            # Suggestions are NEVER automatically assigned to avoid wrong-player photos.
            choices = sorted(((SequenceMatcher(None, key, n).ratio(), n) for n in by_name), reverse=True)
            if choices and choices[0][0] >= .70:
                suggestion = by_name[choices[0][1]][0]['name']
        if match:
            player['picture_url'] = match['photo']
            used += 1
        report.append([player['name'], status, match['name'] if match else '',
                       match['photo'] if match else '', suggestion])
    with OUTPUT.open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(players)
    with REPORT.open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['csv_player', 'status', 'matched_euroleague_name', 'image_url', 'possible_name_to_review'])
        writer.writerows(report)
    print(f'Filled {used} exact-name headshots; {sum(not p.get("picture_url", "").strip() for p in players)} still missing')
    print('Output:', OUTPUT)
    print('Review:', REPORT)

if __name__ == '__main__':
    main()
