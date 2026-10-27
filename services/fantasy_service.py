"""Fantasy rules, validation, lineup locking and round scoring.

Functions retain their original behavior and do not initialize Flask.
"""
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from flask import current_app
from sqlalchemy import func
from extensions import db
from models import (Player, FantasySquad, FantasySquadPlayer, FantasyRoundLineup,
                    FantasyRoundScore, SimulationSeason, SimulationWeek, SimulationGame,
                    SimulationPlayerStats)

FANTASY_BUDGET = 10000  # 100.00M
FANTASY_POSITIONS = ("PG", "SG", "SF", "PF", "C")

def fantasy_calculate_round_scores(season, week, games):
    """
    Calculate and save Fantasy scores for every complete squad.

    Called when the administrator finalizes a simulated round.

    Scoring:
        Starter = 100%
        Bench = 50%
        Captain = 200% (instead of the normal starter 100%)

    FantasyRoundScore.total_points stores hundredths of a point.

    IMPORTANT:
    This function does NOT commit.
    The admin finalization route commits everything together.
    """

    from decimal import Decimal, ROUND_HALF_UP

    # --------------------------------------------------------
    # 1. COLLECT ALL SIMULATED PLAYER PERFORMANCES
    # --------------------------------------------------------

    player_points = {}

    for game in games:

        stats = SimulationPlayerStats.query.filter_by(
            game_id=game.id
        ).all()

        for stat in stats:

            if stat.player_id in player_points:
                raise ValueError(
                    f"Player {stat.player_id} has multiple "
                    f"performances in Round {week.week_number}."
                )

            if stat.fantasy_points is None:
                raise ValueError(
                    f"Player {stat.player_id} has no Fantasy points."
                )

            player_points[stat.player_id] = Decimal(
                str(stat.fantasy_points)
            )

    # --------------------------------------------------------
    # 2. FIND ALL COMPLETE FANTASY SQUADS
    # --------------------------------------------------------

    squads = FantasySquad.query.filter_by(
        season_id=season.id
    ).all()

    scored_squads = 0

    for squad in squads:

        # Incomplete squads cannot participate.
        if len(squad.players) != 10:
            continue

        # ----------------------------------------------------
        # 3. LOAD THE LOCKED LINEUP
        # ----------------------------------------------------

        lineup = FantasyRoundLineup.query.filter_by(
            squad_id=squad.id,
            week_id=week.id
        ).all()

        if len(lineup) != 10:
            raise ValueError(
                f"Fantasy squad {squad.id} does not have "
                f"a complete locked lineup for "
                f"Round {week.week_number}."
            )

        starter_ids = [
            entry.player_id
            for entry in lineup
            if entry.is_starter
        ]

        captain_ids = [
            entry.player_id
            for entry in lineup
            if entry.is_captain
        ]

        if len(captain_ids) != 1:
            raise ValueError(
                f"Fantasy squad {squad.id} has "
                f"an invalid captain."
            )

        captain_id = captain_ids[0]

        # Reuse the validation function from Phase 8.3.
        fantasy_validate_lineup(
            squad,
            starter_ids,
            captain_id
        )

        # Ensure the lineup contains exactly the squad's players.
        squad_player_ids = {
            entry.player_id
            for entry in squad.players
        }

        lineup_player_ids = {
            entry.player_id
            for entry in lineup
        }

        if (
            len(lineup_player_ids) != 10
            or lineup_player_ids != squad_player_ids
        ):
            raise ValueError(
                f"Fantasy squad {squad.id} has "
                f"invalid lineup players."
            )

        # ----------------------------------------------------
        # 4. CALCULATE TOTAL FANTASY POINTS
        # ----------------------------------------------------

        total = Decimal("0")

        for entry in lineup:

            # A player who did not play contributes zero.
            base_points = player_points.get(
                entry.player_id,
                Decimal("0")
            )

            if entry.is_captain:
                multiplier = Decimal("2")

            elif entry.is_starter:
                multiplier = Decimal("1")

            else:
                multiplier = Decimal("0.5")

            contribution = base_points * multiplier

            total += contribution

        # Convert to hundredths.
        # Example: 143.75 points -> 14375.
        total_in_hundredths = int(
            (total * Decimal("100")).quantize(
                Decimal("1"),
                rounding=ROUND_HALF_UP
            )
        )

        # ----------------------------------------------------
        # 5. SAVE OR UPDATE THE ROUND SCORE
        # ----------------------------------------------------

        round_score = FantasyRoundScore.query.filter_by(
            squad_id=squad.id,
            week_id=week.id
        ).first()

        if round_score is None:

            round_score = FantasyRoundScore(
                squad_id=squad.id,
                week_id=week.id,
                total_points=total_in_hundredths
            )

            db.session.add(round_score)

        else:

            round_score.total_points = total_in_hundredths
            round_score.calculated_at = datetime.now(
                timezone.utc
            )

        scored_squads += 1

    return scored_squads


def fantasy_delete_round_data(week_ids):
    """Delete saved Fantasy results and lineup snapshots for given rounds.

    The caller owns the transaction and must commit or roll back.
    """
    if not week_ids:
        return

    FantasyRoundScore.query.filter(
        FantasyRoundScore.week_id.in_(week_ids)
    ).delete(synchronize_session=False)

    FantasyRoundLineup.query.filter(
        FantasyRoundLineup.week_id.in_(week_ids)
    ).delete(synchronize_session=False)


def fantasy_player_price(player):
    """
    Return price in hundredths of a million.
    1250 = 12.50M.

    Prices are deterministic and based on player ratings.
    """
    rating = max(0, min(100, player.rating or 70))

    # 70 rating -> 4.00M
    # 80 rating -> 8.00M
    # 90 rating -> 12.00M
    # 100 rating -> 16.00M
    price = 400 + (rating - 70) * 40

    return max(100, min(1800, price))


def fantasy_current_season():
    return (
        SimulationSeason.query
        .filter_by(status="active")
        .order_by(SimulationSeason.id.desc())
        .first()
    )


def fantasy_squad_editable(season):
    """
    Squad composition is editable only before Round 1 locks.
    """
    if season is None or season.current_week != 1:
        return False

    first_week = SimulationWeek.query.filter_by(
        season_id=season.id,
        week_number=1
    ).first()

    return (
        first_week is not None
        and first_week.status == "scheduled"
    )


def fantasy_validate_squad(player_ids):
    """
    Validate the entire squad on the server.
    Never trust prices or restrictions sent by JavaScript.
    """

    if not isinstance(player_ids, list):
        raise ValueError("Invalid squad data.")

    if len(player_ids) != 10:
        raise ValueError("Your squad must contain exactly 10 players.")

    if any(type(player_id) is not int for player_id in player_ids):
        raise ValueError("Player IDs must be integers.")

    if len(set(player_ids)) != 10:
        raise ValueError("You cannot select the same player twice.")

    players = Player.query.filter(
        Player.id.in_(player_ids)
    ).all()

    if len(players) != 10:
        raise ValueError("One or more selected players do not exist.")

    position_counts = {
        position: 0
        for position in FANTASY_POSITIONS
    }

    team_counts = {}
    total_price = 0

    for player in players:

        if player.position not in position_counts:
            raise ValueError(
                f"{player.name} has an unsupported position."
            )

        position_counts[player.position] += 1

        team_counts[player.team_id] = (
            team_counts.get(player.team_id, 0) + 1
        )

        if team_counts[player.team_id] > 4:
            raise ValueError(
                "You cannot select more than 4 players "
                "from the same club."
            )

        total_price += fantasy_player_price(player)

    for position, count in position_counts.items():
        if count != 2:
            raise ValueError(
                f"You must select exactly 2 {position} players."
            )

    if total_price > FANTASY_BUDGET:
        raise ValueError(
            "Your squad exceeds the 100M budget."
        )

    return players, total_price


def fantasy_get_lineup(squad, week):
    """Return the saved lineup for a particular round."""
    return (
        FantasyRoundLineup.query
        .filter_by(squad_id=squad.id, week_id=week.id)
        .all()
    )


def fantasy_lineup_editable(season, week):
    """Lineups can only be edited before the current round locks."""
    return (
        season.status == "active"
        and week.week_number == season.current_week
        and week.status == "scheduled"
    )


def fantasy_lock_round_lineups(season, week):
    """
    Ensure every complete Fantasy squad has a saved lineup
    before the administrator locks the round.

    Existing valid lineups are preserved.
    Missing lineups are created automatically.

    Changes are committed by the calling admin route.
    """

    squads = FantasySquad.query.filter_by(
        season_id=season.id
    ).all()

    for squad in squads:

        # Only complete squads can participate.
        if len(squad.players) != 10:
            continue

        existing = fantasy_get_lineup(squad, week)

        if existing:
            # Do not silently overwrite incomplete or invalid
            # lineups. Abort the entire lock operation instead.
            if len(existing) != 10:
                raise ValueError(
                    f"Squad {squad.id} has an incomplete lineup."
                )

            starter_ids = [
                entry.player_id
                for entry in existing
                if entry.is_starter
            ]

            captain_ids = [
                entry.player_id
                for entry in existing
                if entry.is_captain
            ]

            if len(captain_ids) != 1:
                raise ValueError(
                    f"Squad {squad.id} has an invalid captain."
                )

            fantasy_validate_lineup(
                squad,
                starter_ids,
                captain_ids[0]
            )

            existing_ids = {
                entry.player_id for entry in existing
            }

            squad_ids = {
                entry.player_id for entry in squad.players
            }

            if existing_ids != squad_ids:
                raise ValueError(
                    f"Squad {squad.id} contains invalid lineup players."
                )

            continue

        # No lineup saved: generate a default.
        starter_ids, captain_id = fantasy_default_lineup(
            squad,
            week
        )

        fantasy_validate_lineup(
            squad,
            list(starter_ids),
            captain_id
        )

        for entry in squad.players:

            db.session.add(
                FantasyRoundLineup(
                    squad_id=squad.id,
                    week_id=week.id,
                    player_id=entry.player_id,
                    is_starter=entry.player_id in starter_ids,
                    is_captain=entry.player_id == captain_id
                )
            )


def fantasy_default_lineup(squad, week):
    """
    For a new round, use the previous round's lineup.
    For Round 1, choose the first player at each position.
    """
    squad_players = [entry.player for entry in squad.players]
    squad_ids = {player.id for player in squad_players}

    previous_week = None

    if week.week_number > 1:
        previous_week = SimulationWeek.query.filter_by(
            season_id=week.season_id,
            week_number=week.week_number - 1
        ).first()

    if previous_week:
        previous_lineup = fantasy_get_lineup(squad, previous_week)

        if len(previous_lineup) == 10:
            previous_ids = {
                entry.player_id for entry in previous_lineup
            }

            starters = {
                entry.player_id
                for entry in previous_lineup
                if entry.is_starter
            }

            captains = [
                entry.player_id
                for entry in previous_lineup
                if entry.is_captain
            ]

            if (
                previous_ids == squad_ids
                and len(starters) == 5
                and len(captains) == 1
                and captains[0] in starters
            ):
                return starters, captains[0]

    starters = set()

    for position in ("PG", "SG", "SF", "PF", "C"):
        candidates = [
            player for player in squad_players
            if player.position == position
        ]

        if not candidates:
            raise ValueError(
                f"Your squad has no {position} player."
            )

        best_player = max(
            candidates,
            key=lambda player: player.rating or 0
        )

        starters.add(best_player.id)

    captain_id = max(
        (player for player in squad_players if player.id in starters),
        key=lambda player: player.rating or 0
    ).id

    return starters, captain_id


def fantasy_validate_lineup(squad, starter_ids, captain_id):
    """Validate the lineup entirely on the server."""

    if len(starter_ids) != 5 or len(set(starter_ids)) != 5:
        raise ValueError("Select exactly five different starters.")

    squad_players = [entry.player for entry in squad.players]

    if len(squad_players) != 10:
        raise ValueError("Complete your 10-player squad first.")

    players_by_id = {
        player.id: player for player in squad_players
    }

    if not set(starter_ids).issubset(players_by_id):
        raise ValueError("A starter does not belong to your squad.")

    positions = [
        players_by_id[player_id].position
        for player_id in starter_ids
    ]

    if set(positions) != {"PG", "SG", "SF", "PF", "C"}:
        raise ValueError(
            "Your starting five must contain one player per position."
        )

    if captain_id not in starter_ids:
        raise ValueError("Your captain must be a starter.")
