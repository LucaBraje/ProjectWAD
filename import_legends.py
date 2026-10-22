"""Import or update EuroLeague legends from legends.csv.

Place beside app.py and legends.csv. Requires Legend model in app.py.
Run: python import_legends.py
"""
import csv
from pathlib import Path
from app import app, db, Legend

CSV_PATH = Path(__file__).resolve().parent / 'legends.csv'
POSITIONS = {'PG', 'SG', 'SF', 'PF', 'C'}
REQUIRED = {'name','nationality','position','rating','defense','offense',
            'points_per_game','assists_per_game','rebounds_per_game',
            'blocks_per_game','steals_per_game','fg_percentage',
            'picture_url','peak_season','legendary_team'}
INT_FIELDS = ('rating', 'defense', 'offense')
FLOAT_FIELDS = ('points_per_game', 'assists_per_game', 'rebounds_per_game',
                'blocks_per_game', 'steals_per_game', 'fg_percentage')
TEXT_FIELDS = ('nationality', 'position', 'peak_season', 'legendary_team', 'stats_type')


def load_rows():
    if not CSV_PATH.is_file():
        raise FileNotFoundError(f'Could not find {CSV_PATH}')
    with CSV_PATH.open(encoding='utf-8-sig', newline='') as handle:
        reader = csv.DictReader(handle)
        missing = REQUIRED - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f'Missing CSV columns: {sorted(missing)}')
        result, names = [], set()
        for line_number, row in enumerate(reader, start=2):
            name = (row.get('name') or '').strip()
            if not name:
                raise ValueError(f'Line {line_number}: name is blank')
            key = name.casefold()
            if key in names:
                raise ValueError(f'Line {line_number}: duplicate name {name}')
            names.add(key)
            values = {'name': name}
            for field in TEXT_FIELDS:
                if field == 'stats_type' and field not in row:
                    values[field] = 'estimated_peak_game_stats'
                else:
                    values[field] = (row.get(field) or '').strip()
            values['picture_url'] = (row.get('picture_url') or '').strip() or None
            if values['position'] not in POSITIONS:
                raise ValueError(f'Line {line_number}: invalid position for {name}')
            if not values['nationality'] or not values['legendary_team']:
                raise ValueError(f'Line {line_number}: nationality or club missing for {name}')
            try:
                for field in INT_FIELDS:
                    values[field] = int(row[field])
                    if not 0 <= values[field] <= 99:
                        raise ValueError(f'{field} must be 0-99')
                for field in FLOAT_FIELDS:
                    values[field] = float(row[field])
                    if values[field] < 0 or (field == 'fg_percentage' and values[field] > 100):
                        raise ValueError(f'{field} is out of range')
            except (TypeError, ValueError) as error:
                raise ValueError(f'Line {line_number} ({name}): {error}') from error
            result.append(values)
    return result


def import_legends():
    rows = load_rows()  # Validate everything before touching the database
    with app.app_context():
        existing = {legend.name.casefold(): legend for legend in Legend.query.all()}
        created = updated = 0
        try:
            for values in rows:
                key = values['name'].casefold()
                legend = existing.get(key)
                if legend is None:
                    legend = Legend(name=values['name'])
                    db.session.add(legend)
                    existing[key] = legend
                    created += 1
                else:
                    updated += 1
                for field, value in values.items():
                    # An empty photo field never removes an existing photo.
                    if field == 'picture_url' and not value:
                        continue
                    setattr(legend, field, value)
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
        print(f'Legends added: {created}')
        print(f'Legends updated: {updated}')
        print(f'Legends in database: {Legend.query.count()}')
        print('No active players, teams, or saved drafts were changed.')


if __name__ == '__main__':
    import_legends()
