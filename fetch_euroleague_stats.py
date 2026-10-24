
"""
Fetch official EuroLeague 2026-27 season player statistics.

Usage:
    pip install requests

    # Preview matches without modifying the database:
    python fetch_euroleague_stats.py

    # Import validated statistics:
    python fetch_euroleague_stats.py --apply

Features:
    - Uses the official EuroLeague statistics API.
    - Matches existing players by name (no EuroLeague ID required).
    - Supports "LASTNAME, FIRSTNAME" naming format.
    - Handles accents, punctuation and capitalization.
    - Skips unmatched, ambiguous and incomplete records.
    - Preserves existing players, teams, ratings and achievements.
    - Recalculates per-game averages after importing totals.
"""

import argparse
from collections import defaultdict
import re
import sys
import unicodedata

import requests


# ============================================================
# EUROLEAGUE API CONFIGURATION
# ============================================================

URL = (
    "https://api-live.euroleague.net/v3/"
    "competitions/E/statistics/players/traditional"
)

SEASON = "E2026"
PAGE_SIZE = 100


# ============================================================
# PLAYER NAME NORMALIZATION
# ============================================================

def normalized(name):
    """
    Normalize a name for matching.

    Examples:
        "Kendrick Nunn" -> "kendrick nunn"
        "KENDRICK NUNN" -> "kendrick nunn"
        "Nikola Mirotić" -> "nikola mirotic"
    """

    name = unicodedata.normalize(
        "NFKD",
        str(name or "")
    )

    name = "".join(
        character
        for character in name
        if not unicodedata.combining(character)
    )

    name = name.casefold()

    name = (
        name.replace("ı", "i")
            .replace("ø", "o")
            .replace("ł", "l")
            .replace("đ", "d")
            .replace("ß", "ss")
    )

    return " ".join(
        re.findall(r"[a-z0-9]+", name)
    )


def official_name_key(name):
    """
    Convert EuroLeague names to normal order.

    Examples:
        "NUNN, KENDRICK" -> "kendrick nunn"
        "MOTLEY, JOHNATHAN" -> "johnathan motley"
        "DECK, GABRIEL" -> "gabriel deck"
    """

    name = str(name or "").strip()

    if "," in name:
        surname, given = name.split(",", 1)

        if surname.strip() and given.strip():
            name = f"{given.strip()} {surname.strip()}"

    return normalized(name)


# ============================================================
# API DATA HELPERS
# ============================================================

def keys_flat(obj, prefix="", depth=0):
    """
    Flatten nested dictionaries from the API.
    """

    if not isinstance(obj, dict) or depth > 3:
        return {}

    output = {}

    for key, val in obj.items():

        clean_key = re.sub(
            r"[^a-z0-9]",
            "",
            str(key).casefold()
        )

        if isinstance(val, dict):

            nested = keys_flat(
                val,
                prefix + clean_key,
                depth + 1
            )

            for nested_key, nested_value in nested.items():
                output.setdefault(
                    nested_key,
                    nested_value
                )

        else:

            output.setdefault(clean_key, val)

            if prefix:
                output.setdefault(
                    prefix + clean_key,
                    val
                )

    return output


def value(row, *names):
    """
    Find a field using possible API field names.
    """

    for name in names:

        key = re.sub(
            r"[^a-z0-9]",
            "",
            name.casefold()
        )

        if key in row and row[key] is not None:
            return row[key]

    return None


def integer(row, *names):
    """
    Convert an API statistic into a nonnegative integer.
    """

    raw = value(row, *names)

    if raw is None or isinstance(raw, bool):
        return None

    try:

        number = float(
            str(raw).replace(",", "").strip()
        )

        if number < 0 or not number.is_integer():
            return None

        return int(number)

    except (ValueError, TypeError):
        return None


# ============================================================
# PARSE OFFICIAL PLAYER STATISTICS
# ============================================================

def parse_player(item):
    """
    Extract player name, team and season totals.
    """

    flat = keys_flat(item)

    name = value(
        flat,
        "playerName",
        "playerFullName",
        "fullName",
        "name"
    )

    if not isinstance(name, str) or not name.strip():
        return None

    games = integer(
        flat,
        "gamesPlayed"
    )

    stats = {
        "games_played": games,

        "total_points": integer(
            flat,
            "pointsScored",
            "points",
            "pts"
        ),

        "total_assists": integer(
            flat,
            "assists",
            "ast"
        ),

        "total_rebounds": integer(
            flat,
            "totalRebounds",
            "rebounds",
            "reb"
        ),

        "total_blocks": integer(
            flat,
            "blocks",
            "blocksMade",
            "blk"
        ),

        "total_steals": integer(
            flat,
            "steals",
            "stl"
        ),

        "total_turnovers": integer(
            flat,
            "turnovers",
            "tov"
        ),
    }

    # Two-point field goals
    two_made = integer(
        flat,
        "twoPointersMade",
        "twoPointMade"
    )

    two_attempted = integer(
        flat,
        "twoPointersAttempted",
        "twoPointAttempted"
    )

    # Three-point field goals
    three_made = integer(
        flat,
        "threePointersMade",
        "threePointMade"
    )

    three_attempted = integer(
        flat,
        "threePointersAttempted",
        "threePointAttempted"
    )

    # Total field goals made
    if two_made is not None and three_made is not None:
        stats["total_fgm"] = two_made + three_made
    else:
        stats["total_fgm"] = integer(
            flat,
            "fieldGoalsMade",
            "fgm"
        )

    # Total field goals attempted
    if two_attempted is not None and three_attempted is not None:
        stats["total_fga"] = (
            two_attempted + three_attempted
        )
    else:
        stats["total_fga"] = integer(
            flat,
            "fieldGoalsAttempted",
            "fga"
        )

    team = value(
        flat,
        "playerTeamName",
        "teamName",
        "clubName"
    )

    return {
        "name": name.strip(),
        "team": team if isinstance(team, str) else "",
        "stats": stats
    }


# ============================================================
# UNWRAP API RESPONSE
# ============================================================

def unwrap(payload):
    """
    Find the player list in the API response.
    """

    if isinstance(payload, list):
        return payload, len(payload)

    if not isinstance(payload, dict):
        raise ValueError(
            "Unexpected API response format."
        )

    for key in (
        "data",
        "items",
        "players",
        "results"
    ):

        val = payload.get(key)

        if isinstance(val, list):
            return val, payload.get(
                "total",
                payload.get("totalCount")
            )

        if isinstance(val, dict):
            try:
                return unwrap(val)
            except ValueError:
                pass

    raise ValueError(
        "Could not find player list. API keys: "
        + ", ".join(payload.keys())
    )


# ============================================================
# FETCH ALL EUROLEAGUE PLAYERS
# ============================================================

def fetch_all():
    """
    Fetch all official player statistics using pagination.
    """

    session = requests.Session()

    results = []
    offset = 0

    for _ in range(30):

        response = session.get(
            URL,
            params={
                "SeasonMode": "Single",
                "SeasonCode": SEASON,
                "statisticMode": "Accumulated",
                "limit": PAGE_SIZE,
                "offset": offset
            },
            timeout=25,
            headers={
                "Accept": "application/json",
                "User-Agent": "DraftEuroleagueStats/1.0"
            }
        )

        response.raise_for_status()

        page, total = unwrap(response.json())

        if not page:
            break

        results.extend(page)

        print(
            f"Fetched {len(results)} official rows...",
            flush=True
        )

        if (
            len(page) < PAGE_SIZE
            or (
                isinstance(total, int)
                and len(results) >= total
            )
        ):
            break

        offset += PAGE_SIZE

    else:
        raise RuntimeError(
            "Pagination limit reached. Import stopped."
        )

    if not results:
        raise RuntimeError(
            "API returned zero players."
        )

    return results


# ============================================================
# MAIN IMPORT FUNCTION
# ============================================================

def main():

    parser = argparse.ArgumentParser(
        description="EuroLeague E2026 statistics importer"
    )

    parser.add_argument(
        "--apply",
        action="store_true",
        help="Save validated statistics to the database"
    )

    args = parser.parse_args()

    # --------------------------------------------------------
    # STEP 1: FETCH OFFICIAL STATISTICS
    # --------------------------------------------------------

    print(
        f"Fetching EuroLeague statistics for {SEASON}..."
    )

    try:
        rows = fetch_all()

    except (
        requests.RequestException,
        ValueError,
        RuntimeError
    ) as error:

        sys.exit(
            f"API error: {error}\n"
            "No database changes were made."
        )

    # --------------------------------------------------------
    # STEP 2: PARSE PLAYER STATISTICS
    # --------------------------------------------------------

    parsed = [
        player
        for player in (
            parse_player(row)
            for row in rows
        )
        if player is not None
    ]
    print("\nSTATISTICS CHECK:")
    for player in parsed:
        if "NUNN" in player["name"].upper() or "MOTLEY" in player["name"].upper():
            print(player["name"], player["stats"])
    if not parsed:

        sample = rows[0]

        sys.exit(
            "API fields not recognized. "
            "No changes made. First row keys: "
            + str(
                list(sample.keys())
                if isinstance(sample, dict)
                else type(sample)
            )
        )

    # --------------------------------------------------------
    # STEP 3: CONNECT TO EXISTING FLASK DATABASE
    # --------------------------------------------------------

    from app import app, db, Player

    with app.app_context():

        players = Player.query.all()

        # Local players indexed by normalized name
        local_index = defaultdict(list)

        for player in players:
            key = normalized(player.name)
            local_index[key].append(player)

        # Official players indexed by normalized name
        official_index = defaultdict(list)

        for entry in parsed:
            key = official_name_key(entry["name"])
            official_index[key].append(entry)

        # ----------------------------------------------------
        # STEP 4: MATCH PLAYERS
        # ----------------------------------------------------

        ready = []
        unmatched = []
        ambiguous = []
        incomplete = []

        for name_key, entries in official_index.items():

            matches = local_index.get(name_key, [])

            if not matches:

                unmatched.extend(
                    entry["name"]
                    for entry in entries
                )

                continue

            # Never update ambiguous names
            if len(matches) != 1 or len(entries) != 1:

                ambiguous.append((
                    entries[0]["name"],
                    len(matches),
                    len(entries)
                ))

                continue

            entry = entries[0]
            stats = entry["stats"]

            missing_fields = [
                field
                for field, amount in stats.items()
                if amount is None
            ]

            if missing_fields:

                incomplete.append((
                    entry["name"],
                    missing_fields
                ))

                continue

            if (
                stats["games_played"] <= 0
                or stats["total_fgm"] > stats["total_fga"]
            ):

                incomplete.append((
                    entry["name"],
                    ["invalid games or shooting totals"]
                ))

                continue

            ready.append((
                matches[0],
                entry
            ))

        # ----------------------------------------------------
        # STEP 5: DISPLAY PREVIEW
        # ----------------------------------------------------

        print()
        print("=" * 65)
        print("EUROLEAGUE STATISTICS IMPORT PREVIEW")
        print("=" * 65)

        print(f"Season: {SEASON}")
        print(f"Official rows: {len(rows)}")
        print(f"Local players: {len(players)}")

        print("-" * 65)

        print(f"Ready to update: {len(ready)}")
        print(f"Unmatched: {len(unmatched)}")
        print(f"Ambiguous: {len(ambiguous)}")
        print(f"Incomplete: {len(incomplete)}")

        print("=" * 65)

        print("\nMATCHED PLAYERS (first 20):")

        if ready:
            for player, entry in ready[:20]:

                print(
                    f"  {player.name}"
                    f" <- {entry['name']}"
                    f" ({entry['stats']['games_played']} games)"
                )
        else:
            print("  None")

        print("\nUNMATCHED PLAYERS (first 35):")

        if unmatched:
            for name in unmatched[:35]:
                print(f"  {name}")
        else:
            print("  None")

        print("\nAMBIGUOUS MATCHES (first 20):")

        if ambiguous:
            for item in ambiguous[:20]:
                print(f"  {item}")
        else:
            print("  None")

        print("\nINCOMPLETE STATISTICS (first 15):")

        if incomplete:
            for item in incomplete[:15]:
                print(f"  {item}")
        else:
            print("  None")

        # ----------------------------------------------------
        # STEP 6: PREVIEW MODE
        # ----------------------------------------------------

        if not ready:

            print(
                "\nNo safe matches to update. "
                "No changes made."
            )

            return

        if not args.apply:

            print(
                "\nPREVIEW ONLY. "
                "No database changes were made."
            )

            print(
                "Run with --apply to import statistics."
            )

            return

        # ----------------------------------------------------
        # STEP 7: IMPORT STATISTICS
        # ----------------------------------------------------

        try:

            for player, entry in ready:

                for field, amount in entry["stats"].items():

                    setattr(
                        player,
                        field,
                        amount
                    )

            # Recalculate averages from official totals.
            from update_player_stats import update_all_player_stats

            update_all_player_stats(
                db,
                Player
            )

            print()
            print("=" * 65)

            print(
                f"Successfully imported statistics "
                f"for {len(ready)} existing players."
            )

            print("=" * 65)

        except Exception:

            db.session.rollback()

            print(
                "Import failed. Database transaction rolled back."
            )

            raise


# ============================================================
# SCRIPT ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()
