
import csv
import re
import shutil
import unicodedata
from datetime import datetime
from pathlib import Path

from app import app, db, Player, Team


# ==========================================
# CONFIGURATION
# ==========================================

BASE_DIR = Path(__file__).resolve().parent

CSV_FILE = BASE_DIR / "players.csv"

# Safety settings
DRY_RUN = False
UPDATE_EXISTING = True
ADD_NEW_PLAYERS = True

# Never automatically delete players.
DELETE_MISSING_PLAYERS = False


# ==========================================
# NAME NORMALIZATION
# ==========================================

def normalize_name(name):
    """
    Normalize names for comparison.

    Examples:
    'Nikola Mirotić' -> 'nikola mirotic'
    'NIKOLA MIROTIC' -> 'nikola mirotic'
    """

    name = unicodedata.normalize("NFKD", name or "")

    name = "".join(
        char for char in name
        if not unicodedata.combining(char)
    )

    name = name.lower()
    name = re.sub(r"[^a-z0-9]+", " ", name)

    return " ".join(name.split())


# Add verified aliases here when the CSV and
# existing database use different player names.
#
# Format:
# "name in CSV": "name in existing database"
#
# Do not add aliases for different people.

PLAYER_ALIASES = {
    "michael perry james": "mike james",
    "deshane davis larkin": "shane larkin",
    "nikola mirotic stajovic": "nikola mirotic",
    "timothy neocartes shorts vtori": "tj shorts",
    "facundo campazzo": "facundo campazzo",
}


def canonical_name(name):
    normalized = normalize_name(name)
    return normalize_name(
        PLAYER_ALIASES.get(normalized, normalized)
    )


# ==========================================
# VALUE CONVERSION
# ==========================================

def to_int(value, default=None):
    if value is None or str(value).strip() == "":
        return default

    return int(float(value))


def to_float(value, default=None):
    if value is None or str(value).strip() == "":
        return default

    return float(value)


def optional_text(value):
    if value is None:
        return None

    value = str(value).strip()
    return value or None


# ==========================================
# UPDATE PLAYER
# ==========================================

def update_player(player, row, team):
    """
    Update an existing player without
    changing their database ID.

    Blank CSV fields do not overwrite
    existing values.
    """

    player.name = row["name"].strip()
    player.team_id = team.id

    nationality = optional_text(row.get("nationality"))
    position = optional_text(row.get("position"))
    picture_url = optional_text(row.get("picture_url"))

    if nationality is not None:
        player.nationality = nationality

    if position is not None:
        player.position = position

    if picture_url is not None:
        player.picture_url = picture_url

    integer_fields = [
        "rating",
        "offense",
        "defense",
    ]

    float_fields = [
        "points_per_game",
        "assists_per_game",
        "rebounds_per_game",
        "blocks_per_game",
        "steals_per_game",
        "fg_percentage",
    ]

    for field in integer_fields:
        value = to_int(row.get(field))

        if value is not None:
            setattr(player, field, value)

    for field in float_fields:
        value = to_float(row.get(field))

        if value is not None:
            setattr(player, field, value)


# ==========================================
# CREATE NEW PLAYER
# ==========================================

def create_player(row, team):
    return Player(
        name=row["name"].strip(),
        nationality=optional_text(row.get("nationality")),
        position=optional_text(row.get("position")) or "SF",
        rating=to_int(row.get("rating"), 70),
        offense=to_int(row.get("offense"), 70),
        defense=to_int(row.get("defense"), 70),
        points_per_game=to_float(row.get("points_per_game"), 0.0),
        assists_per_game=to_float(row.get("assists_per_game"), 0.0),
        rebounds_per_game=to_float(row.get("rebounds_per_game"), 0.0),
        blocks_per_game=to_float(row.get("blocks_per_game"), 0.0),
        steals_per_game=to_float(row.get("steals_per_game"), 0.0),
        fg_percentage=to_float(row.get("fg_percentage"), 0.0),
        picture_url=optional_text(row.get("picture_url")),
        team_id=team.id,
    )


# ==========================================
# MAIN IMPORT
# ==========================================

def import_players():

    if not CSV_FILE.exists():
        print(f"ERROR: CSV not found: {CSV_FILE}")
        return

    added = 0
    updated = 0
    unchanged = 0
    skipped = 0

    missing_teams = set()
    ambiguous_players = []
    missing_players = []
    duplicate_csv_names = []

    with app.app_context():

        teams = Team.query.all()
        players = Player.query.all()

        team_lookup = {
            normalize_name(team.name): team
            for team in teams
        }

        # Existing players grouped by normalized name
        player_lookup = {}

        for player in players:
            key = canonical_name(player.name)

            player_lookup.setdefault(key, []).append(player)

        csv_player_names = set()
        seen_csv_names = set()

        with open(
            CSV_FILE,
            "r",
            encoding="utf-8-sig",
            newline=""
        ) as file:

            reader = csv.DictReader(file)

            for row_number, row in enumerate(reader, start=2):

                try:
                    name = (row.get("name") or "").strip()
                    team_name = (row.get("team") or "").strip()

                    if not name or not team_name:
                        skipped += 1
                        print(
                            f"Row {row_number}: Missing name/team."
                        )
                        continue

                    key = canonical_name(name)

                    if key in seen_csv_names:
                        duplicate_csv_names.append(name)
                        skipped += 1
                        continue

                    seen_csv_names.add(key)

                    team = team_lookup.get(
                        normalize_name(team_name)
                    )

                    if team is None:
                        missing_teams.add(team_name)
                        skipped += 1
                        continue

                    csv_player_names.add(key)

                    matches = player_lookup.get(key, [])

                    if len(matches) > 1:
                        ambiguous_players.append(name)
                        skipped += 1
                        continue

                    if len(matches) == 1:

                        player = matches[0]

                        old_team = player.team.name

                        if UPDATE_EXISTING:
                            update_player(player, row, team)
                            updated += 1

                            if old_team != team.name:
                                print(
                                    f"TRANSFER: {name}: "
                                    f"{old_team} -> {team.name}"
                                )
                        else:
                            unchanged += 1

                    else:

                        if ADD_NEW_PLAYERS:
                            player = create_player(row, team)
                            db.session.add(player)

                            # Prevent a duplicate if this
                            # name occurs later in processing.
                            player_lookup[key] = [player]

                            added += 1
                        else:
                            skipped += 1

                except (ValueError, TypeError, KeyError) as error:
                    print(
                        f"Row {row_number}: {error}"
                    )
                    skipped += 1

        # Find existing players absent from the new CSV.
        # They are reported, not deleted.
        for player in players:
            if canonical_name(player.name) not in csv_player_names:
                missing_players.append(
                    f"{player.name} ({player.team.name})"
                )

        # ======================================
        # SUMMARY
        # ======================================

        print("\n" + "=" * 55)
        print("PLAYER IMPORT SUMMARY")
        print("=" * 55)

        print(f"CSV file: {CSV_FILE.name}")
        print(f"Mode: {'DRY RUN' if DRY_RUN else 'LIVE'}")

        print(f"New players: {added}")
        print(f"Existing players updated: {updated}")
        print(f"Existing players unchanged: {unchanged}")
        print(f"Rows skipped: {skipped}")

        print(f"Missing teams: {len(missing_teams)}")
        print(f"Ambiguous players: {len(ambiguous_players)}")
        print(f"Duplicate CSV names: {len(duplicate_csv_names)}")
        print(f"Old players absent from CSV: {len(missing_players)}")

        if missing_teams:
            print("\nMISSING TEAMS:")
            for team_name in sorted(missing_teams):
                print(f" - {team_name}")

        if ambiguous_players:
            print("\nAMBIGUOUS PLAYER MATCHES:")
            for name in ambiguous_players:
                print(f" - {name}")

        if duplicate_csv_names:
            print("\nDUPLICATE CSV PLAYERS:")
            for name in duplicate_csv_names:
                print(f" - {name}")

        if missing_players:
            print("\nEXISTING PLAYERS NOT IN NEW CSV:")
            for name in missing_players:
                print(f" - {name}")

        # ======================================
        # SAVE OR ROLLBACK
        # ======================================

        if DRY_RUN:
            db.session.rollback()
            print("\nDRY RUN COMPLETE.")
            print("No database changes were saved.")

        else:
            if missing_teams or ambiguous_players or duplicate_csv_names:
                db.session.rollback()
                print("\nIMPORT CANCELLED.")
                print("Resolve the issues above before saving.")
                return

            db.session.commit()

            print("\nIMPORT COMPLETED SUCCESSFULLY.")
            print("Database changes saved.")


if __name__ == "__main__":
    import_players()
