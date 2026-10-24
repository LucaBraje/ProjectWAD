
"""
Add missing EuroLeague players and update existing players with different names.

Commands:
    python add_missing_players.py
    python add_missing_players.py --apply
    python add_missing_players.py --apply --new-only

Features:
    - Fetches official EuroLeague E2026 statistics.
    - Adds approved genuinely missing players.
    - Updates existing players with known nickname/name differences.
    - Matches official EuroLeague team names to local database teams.
    - Adds custom ratings, positions, nationalities, and pictures.
    - Skips unresolved or ambiguous players.
    - Creates a SQLite backup before changing data.
    - Preserves existing player ratings and other project data.
"""

import argparse
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path

from sqlalchemy import inspect

from fetch_euroleague_stats import (
    fetch_all,
    parse_player,
    normalized,
    official_name_key,
)

from app import app, db, Player, Team


# ============================================================
# 1. EXISTING PLAYER NAME ALIASES
# ============================================================

# Official EuroLeague name -> existing database name
# These players already exist. We only update their statistics.

PLAYER_ALIASES = {
    "Gabriel Deck": "Gaby Deck",
    "William Rayman": "Will Rayman",
    "Giampaolo Ricci": "Pippo Ricci",
    "Armando Bacot Jr.": "Armando Bacot",
    "Daron Russell": "Fatts Russell",
    "Tornike Shengelia": "Toko Shengelia",
    "Nikolaos Rogkavopoulos": "Nikos Rogkavopoulos",
    "Nathan Sestina": "Nate Sestina",
    "Tyty Washington Jr": "TyTy Washington",
    "Mouhamet Diouf": "Momo Diouf",
    "Bo Klintman": "Bobi Klintman",
    "Nathan Reuvers": "Nate Reuvers",
    "A.J. Lawson": "AJ Lawson",
    "Mckinley Wright Iv": "McKinley Wright",
    "Kameron Taylor": "Kam Taylor",
    "Jimmy Clark Iii": "Jimmy Clark",
    "O'Shae J Brissett": "Oshae Brissett",
    "Wendell Moore": "Wendell Moore Jr.",
    "Wade Baldwin Iv": "Wade Baldwin",
}


# ============================================================
# 2. NEW PLAYER INFORMATION
# ============================================================

# Custom Draft EuroLeague ratings.
# These are manually assigned game ratings, not official API ratings.
#
# Every new player has:
#   rating       = Overall rating
#   offense      = Offensive rating
#   defense      = Defensive rating
#   position     = Basketball position
#   nationality  = Player nationality
#   picture_url  = Proballers headshot supplied by user

NEW_PLAYER_DATA = {

    "Lorenz Sanz": {
        "rating": 65,
        "offense": 64,
        "defense": 63,
        "position": "PG",
        "nationality": "France",
        "picture_url": "https://www.proballers.com/media/cache/headshot_600/player/headshot/253348.png",
    },

    "Bryant Dunston": {
        "rating": 78,
        "offense": 69,
        "defense": 86,
        "position": "C",
        "nationality": "USA",
        "picture_url": "https://www.proballers.com/media/cache/headshot_600/player/headshot/33551.png",
    },

    "Bandja Sy": {
        "rating": 73,
        "offense": 67,
        "defense": 79,
        "position": "PF",
        "nationality": "France",
        "picture_url": "https://www.proballers.com/media/cache/headshot_600/player/headshot/45446.png",
    },

    "Joel Ayayi": {
        "rating": 74,
        "offense": 72,
        "defense": 76,
        "position": "SG",
        "nationality": "France",
        "picture_url": "https://www.proballers.com/media/cache/headshot_600/player/headshot/68705.png",
    },

    "Leopold Cavaliere": {
        "rating": 72,
        "offense": 71,
        "defense": 73,
        "position": "PF",
        "nationality": "France",
        "picture_url": "https://www.proballers.com/media/cache/headshot_600/player/headshot/57147.png",
    },

    "Jasiel Rivero": {
        "rating": 79,
        "offense": 79,
        "defense": 78,
        "position": "PF",
        "nationality": "Cuba",
        "picture_url": "https://www.proballers.com/media/cache/headshot_600/player/headshot/71197.png",
    },

    "Cameron Payne": {
        "rating": 83,
        "offense": 86,
        "defense": 73,
        "position": "PG",
        "nationality": "USA",
        "picture_url": "https://www.proballers.com/media/cache/headshot_600/player/headshot/66186.png",
    },

    "Mouhamed Faye": {
        "rating": 76,
        "offense": 68,
        "defense": 83,
        "position": "C",
        "nationality": "Senegal",
        "picture_url": "https://www.proballers.com/media/cache/headshot_600/player/headshot/264377.png",
    },

    "Mathias Lessort": {
        "rating": 90,
        "offense": 85,
        "defense": 94,
        "position": "C",
        "nationality": "France",
        "picture_url": "https://www.proballers.com/media/cache/headshot_600/player/headshot/13260.png",
    },
}


# Normalize names for matching against the API.
APPROVED_NEW_PLAYERS = {
    normalized(name): data
    for name, data in NEW_PLAYER_DATA.items()
}


# ============================================================
# 3. TEAM NAME ALIASES
# ============================================================

# Official API team name -> local database team name

TEAM_ALIASES = {
    "Anadolu Efes Istanbul": "Anadolu Efes",
    "Armani Olimpia Milan": "Armani Milan",
    "Baskonia Vitoria-Gasteiz": "Baskonia Vitoria-Gasteiz",
    "Dubai Basketball": "Dubai Basketball",
    "Fenerbahce Istanbul": "Fenerbahçe Tarfin",
    "LDLC ASVEL Villeurbanne": "LDLC ASVEL Villeurbanne",
    "Maccabi Rapyd Tel Aviv": "Maccabi Tel Aviv",
    "Olympiacos Piraeus": "Olympiacos",
    "Panathinaikos AKTOR Athens": "Panathinaikos",
    "Paris Basketball": "Paris Basketball",
    "Partizan Mozzart Bet Belgrade": "Partizan Belgrade",
    "Real Madrid": "Real Madrid",
    "Valencia Basket": "Valencia",
    "Virtus Bologna": "Virtus Bologna",
}


# ============================================================
# 4. PLAYERS TO SKIP
# ============================================================

# Marcio Santos appears under two teams in the API.
# We will review him separately.

SKIP_PLAYERS = {
    normalized("Marcio Santos"),
}


# ============================================================
# 5. HELPER FUNCTIONS
# ============================================================

def display_name(api_name):
    """
    Convert:
        'LESSORT, MATHIAS'
    Into:
        'Mathias Lessort'
    """

    if "," not in api_name:
        return api_name.strip().title()

    surname, given = api_name.split(",", 1)

    return f"{given.strip().title()} {surname.strip().title()}"


def similarity(a, b):
    """
    Compare two player names.
    """

    return SequenceMatcher(
        None,
        normalized(a),
        normalized(b),
    ).ratio()


def calculate_averages(stats):
    """
    Calculate per-game averages from official season totals.
    """

    games = stats["games_played"]

    if not games or games <= 0:
        raise ValueError("Invalid games played")

    attempts = stats["total_fga"]

    return {
        "points_per_game": round(
            stats["total_points"] / games, 2
        ),
        "assists_per_game": round(
            stats["total_assists"] / games, 2
        ),
        "rebounds_per_game": round(
            stats["total_rebounds"] / games, 2
        ),
        "blocks_per_game": round(
            stats["total_blocks"] / games, 2
        ),
        "steals_per_game": round(
            stats["total_steals"] / games, 2
        ),
        "fg_percentage": round(
            stats["total_fgm"] / attempts * 100, 2
        ) if attempts else 0.0,
    }


def valid_statistics(stats):
    """
    Ensure all required statistics exist and are valid.
    """

    required = [
        "games_played",
        "total_points",
        "total_assists",
        "total_rebounds",
        "total_blocks",
        "total_steals",
        "total_turnovers",
        "total_fgm",
        "total_fga",
    ]

    if any(stats.get(field) is None for field in required):
        return False

    if stats["games_played"] <= 0:
        return False

    if stats["total_fgm"] > stats["total_fga"]:
        return False

    return True


def resolve_team(api_team, local_teams):
    """
    Match an official EuroLeague team name to an existing
    Team record in the local SQLite database.
    """

    if not api_team or ";" in api_team:
        return None

    key = normalized(api_team)

    # First try an exact normalized match.
    if key in local_teams:
        return local_teams[key]

    # Otherwise use the alias dictionary.
    alias = TEAM_ALIASES.get(api_team)

    if alias:
        return local_teams.get(normalized(alias))

    return None


def backup_database():
    """
    Create a consistent backup of the existing SQLite database.
    """

    database_path = Path(
        db.engine.url.database
    ).resolve()

    if not database_path.is_file():
        raise FileNotFoundError(
            f"Database not found: {database_path}"
        )

    backup_path = database_path.with_name(
        database_path.stem
        + "_backup_"
        + datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        + database_path.suffix
    )

    with sqlite3.connect(database_path) as source:
        with sqlite3.connect(backup_path) as destination:
            source.backup(destination)

    print(f"\nDatabase backup created: {backup_path}")


def apply_statistics(player, stats):
    """
    Update a player's official season totals and averages.

    Does NOT change:
        - Overall rating
        - Offensive rating
        - Defensive rating
        - Position
        - Nationality
        - Picture
        - Team
    """

    for field, amount in stats.items():
        setattr(player, field, amount)

    averages = calculate_averages(stats)

    for field, amount in averages.items():
        setattr(player, field, amount)


# ============================================================
# 6. MAIN FUNCTION
# ============================================================

def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write approved changes to the database",
    )

    parser.add_argument(
        "--new-only",
        action="store_true",
        help="Add new players without updating existing aliases",
    )

    args = parser.parse_args()

    if args.new_only and not args.apply:
        parser.error("--new-only requires --apply")

    print("Fetching official EuroLeague players...")
    rows = fetch_all()

    with app.app_context():

        # ----------------------------------------------------
        # LOAD EXISTING DATABASE DATA
        # ----------------------------------------------------

        players = Player.query.all()
        teams = Team.query.all()

        local_players = defaultdict(list)

        for player in players:
            local_players[normalized(player.name)].append(player)

        local_teams = {
            normalized(team.name): team
            for team in teams
        }

        alias_lookup = {
            normalized(api_name): normalized(local_name)
            for api_name, local_name in PLAYER_ALIASES.items()
        }

        # ----------------------------------------------------
        # PARSE OFFICIAL API RECORDS
        # ----------------------------------------------------

        official_entries = defaultdict(list)

        for raw in rows:

            entry = parse_player(raw)

            if entry is None:
                continue

            key = official_name_key(entry["name"])

            official_entries[key].append((entry, raw))

        new_players = []
        alias_updates = []
        skipped = []

        # ----------------------------------------------------
        # CLASSIFY PLAYERS
        # ----------------------------------------------------

        for key, entries in official_entries.items():

            if len(entries) != 1:
                skipped.append(
                    (key, "duplicate official API records")
                )
                continue

            entry, raw = entries[0]

            name = display_name(entry["name"])
            stats = entry["stats"]

            # Player already exists with the same name.
            # The original importer handles these players.
            if key in local_players:
                continue

            # Players requiring manual review.
            if key in SKIP_PLAYERS:
                skipped.append(
                    (name, "requires manual review")
                )
                continue

            # Do not import incomplete official statistics.
            if not valid_statistics(stats):
                skipped.append(
                    (name, "invalid or incomplete statistics")
                )
                continue

            # ------------------------------------------------
            # EXISTING PLAYER WITH A DIFFERENT NAME
            # ------------------------------------------------

            if key in alias_lookup:

                existing_key = alias_lookup[key]
                matches = local_players.get(existing_key, [])

                if len(matches) != 1:
                    skipped.append(
                        (name, "alias not uniquely resolved")
                    )
                    continue

                alias_updates.append(
                    (matches[0], entry)
                )

                continue

            # ------------------------------------------------
            # NEW APPROVED PLAYER
            # ------------------------------------------------

            if key not in APPROVED_NEW_PLAYERS:
                skipped.append(
                    (name, "not approved for insertion")
                )
                continue

            # Match API team to local database team.
            team = resolve_team(
                entry["team"],
                local_teams,
            )

            if team is None:
                skipped.append(
                    (name, f"unresolved team: {entry['team']}")
                )
                continue

            # Check for strong name similarity to existing
            # players to avoid accidental duplicates.
            suggestions = sorted(
                (
                    (similarity(name, player.name), player.name)
                    for player in players
                ),
                reverse=True,
            )[:3]

            strong_duplicates = [
                existing_name
                for score, existing_name in suggestions
                if score >= 0.85
            ]

            if strong_duplicates:
                skipped.append(
                    (
                        name,
                        "possible duplicate: "
                        + ", ".join(strong_duplicates),
                    )
                )
                continue

            # Get our custom information for this player.
            player_info = APPROVED_NEW_PLAYERS[key]

            new_players.append({
                "name": name,
                "team": team,
                "stats": stats,
                "player_info": player_info,
            })

        # ----------------------------------------------------
        # PREVIEW
        # ----------------------------------------------------

        print()
        print("=" * 65)
        print("EUROLEAGUE PLAYER DATABASE UPDATE")
        print("=" * 65)

        print(f"Current players: {len(players)}")
        print(f"New players to add: {len(new_players)}")
        print(f"Existing aliases to update: {len(alias_updates)}")
        print(f"Skipped: {len(skipped)}")

        print("\nNEW PLAYERS:")

        for entry in new_players:

            info = entry["player_info"]

            print(
                f"  + {entry['name']} "
                f"({entry['team'].name}) "
                f"| OVR: {info['rating']} "
                f"| OFF: {info['offense']} "
                f"| DEF: {info['defense']} "
                f"| POS: {info['position']}"
            )

        print("\nEXISTING PLAYERS TO UPDATE:")

        for player, entry in alias_updates:
            print(
                f"  ~ {player.name} "
                f"<- {entry['name']}"
            )

        print("\nSKIPPED:")

        for name, reason in skipped:
            print(f"  - {name}: {reason}")

        if not args.apply:
            print(
                "\nPREVIEW ONLY. No database changes made."
            )
            return

        # ----------------------------------------------------
        # VERIFY DATABASE SCHEMA
        # ----------------------------------------------------

        existing_columns = {
            column["name"]
            for column in inspect(db.engine).get_columns("player")
        }

        required_columns = {
            "games_played",
            "total_points",
            "total_assists",
            "total_rebounds",
            "total_blocks",
            "total_steals",
            "total_turnovers",
            "total_fgm",
            "total_fga",
        }

        if not required_columns.issubset(existing_columns):
            sys.exit(
                "Database migration is missing required columns."
            )

        # ----------------------------------------------------
        # BACKUP DATABASE
        # ----------------------------------------------------

        backup_database()

        # ----------------------------------------------------
        # APPLY DATABASE CHANGES
        # ----------------------------------------------------

        try:

            # Add the nine missing players.
            for entry in new_players:

                info = entry["player_info"]

                player = Player(
                    name=entry["name"],
                    team_id=entry["team"].id,

                    rating=info["rating"],
                    offense=info["offense"],
                    defense=info["defense"],

                    position=info["position"],
                    nationality=info["nationality"],

                    picture_url=info["picture_url"],
                )

                # Add official totals and calculate averages.
                apply_statistics(
                    player,
                    entry["stats"],
                )

                db.session.add(player)

            # Update existing players with known aliases.
            if not args.new_only:

                for player, entry in alias_updates:
                    apply_statistics(
                        player,
                        entry["stats"],
                    )

            # Commit everything as one transaction.
            db.session.commit()

        except Exception:
            db.session.rollback()
            raise

        # ----------------------------------------------------
        # SUCCESS MESSAGE
        # ----------------------------------------------------

        print()
        print("=" * 65)
        print("DATABASE UPDATE COMPLETED")
        print("=" * 65)

        print(
            f"New players added: {len(new_players)}"
        )

        print(
            "Existing players updated: "
            + str(
                0 if args.new_only
                else len(alias_updates)
            )
        )

        print(
            f"Total players: {Player.query.count()}"
        )


if __name__ == "__main__":
    main()
