"""Higher or Lower game logic, statistics and achievements."""
import random
from flask import session
from flask_login import current_user
from extensions import db
from models import Player, HigherLowerStats, UserAchievement

HL_STATISTICS = {
    "rating": "Overall Rating",
    "points_per_game": "Points Per Game",
    "assists_per_game": "Assists Per Game",
    "rebounds_per_game": "Rebounds Per Game",
    "steals_per_game": "Steals Per Game",
    "blocks_per_game": "Blocks Per Game",
    "fg_percentage": "Field Goal Percentage"
}


HL_SESSION_KEY = "higher_or_lower_game"


HL_ACHIEVEMENTS = {
    "hl_first_game": {
        "name": "First Comparison",
        "description": "Complete your first Higher or Lower game.",
        "title": "First Comparison"
    },
    "hl_streak_5": {
        "name": "Getting Warm",
        "description": "Reach a streak of 5.",
        "title": "Getting Warm"
    },
    "hl_streak_10": {
        "name": "On Fire",
        "description": "Reach a streak of 10.",
        "title": "On Fire"
    },
    "hl_streak_20": {
        "name": "EuroLeague Expert",
        "description": "Reach a streak of 20.",
        "title": "EuroLeague Expert"
    },
    "hl_correct_50": {
        "name": "Sharp Shooter",
        "description": "Make 50 correct guesses.",
        "title": "Sharp Shooter"
    },
    "hl_games_25": {
        "name": "Dedicated Analyst",
        "description": "Complete 25 games.",
        "title": "Dedicated Analyst"
    }
}


def hl_get_stats():
    """Get or create the logged-in user's game statistics."""
    stats = HigherLowerStats.query.filter_by(
        user_id=current_user.id
    ).first()

    if stats is None:
        stats = HigherLowerStats(user_id=current_user.id)
        db.session.add(stats)
        db.session.flush()

    return stats


def hl_unlock_achievements(stats):
    """Add newly earned achievements to the existing user system."""
    eligible = set()

    if stats.total_games >= 1:
        eligible.add("hl_first_game")

    if stats.best_streak >= 5:
        eligible.add("hl_streak_5")

    if stats.best_streak >= 10:
        eligible.add("hl_streak_10")

    if stats.best_streak >= 20:
        eligible.add("hl_streak_20")

    if stats.total_correct >= 50:
        eligible.add("hl_correct_50")

    if stats.total_games >= 25:
        eligible.add("hl_games_25")

    existing = {
        item.achievement_key
        for item in UserAchievement.query.filter_by(
            user_id=current_user.id
        ).all()
    }

    unlocked = []

    for key in sorted(eligible - existing):
        db.session.add(UserAchievement(
            user_id=current_user.id,
            achievement_key=key
        ))

        unlocked.append({
            "key": key,
            "name": HL_ACHIEVEMENTS[key]["name"]
        })

    return unlocked


def hl_valid_players(players, stat_key):
    """
    Return players with valid, positive values
    for the selected statistic.
    """

    valid = []

    for player in players:

        value = getattr(player, stat_key, None)

        if value is None:
            continue

        try:
            value = float(value)
        except (TypeError, ValueError):
            continue

        if value <= 0:
            continue

        valid.append(player)

    return valid


def hl_available_statistics(players):
    """
    Find statistics that have at least two
    different positive values in the database.
    """

    available = []

    for stat_key in HL_STATISTICS:

        valid = hl_valid_players(players, stat_key)

        distinct_values = {
            float(getattr(player, stat_key))
            for player in valid
        }

        if len(distinct_values) >= 2:
            available.append(stat_key)

    return available


def hl_choose_pair(players, stat_key, first_id=None):
    """
    Select two different players whose values
    for the chosen statistic are not equal.

    If possible, use first_id as the first player.
    """

    eligible = hl_valid_players(players, stat_key)

    if len(eligible) < 2:
        raise ValueError(
            "Not enough players with valid statistics."
        )

    first = None

    if first_id is not None:

        first = next(
            (
                player for player in eligible
                if player.id == first_id
            ),
            None
        )

    if first is None:
        first = random.choice(eligible)

    first_value = float(
        getattr(first, stat_key)
    )

    possible_second = [
        player
        for player in eligible
        if (
            player.id != first.id
            and float(getattr(player, stat_key)) != first_value
        )
    ]

    # A carried-over player might have a value
    # that matches every other eligible player.
    if not possible_second:

        possible_first = [
            player
            for player in eligible
            if any(
                other.id != player.id
                and float(getattr(other, stat_key))
                != float(getattr(player, stat_key))
                for other in eligible
            )
        ]

        if not possible_first:
            raise ValueError(
                "No valid player comparisons are available."
            )

        first = random.choice(possible_first)

        first_value = float(
            getattr(first, stat_key)
        )

        possible_second = [
            player
            for player in eligible
            if (
                player.id != first.id
                and float(getattr(player, stat_key))
                != first_value
            )
        ]

    second = random.choice(possible_second)

    return first, second


def hl_format_value(value, stat_key):
    """
    Format a statistic for display.
    """

    if value is None:
        return "—"

    if stat_key == "rating":
        return str(int(value))

    if stat_key == "fg_percentage":
        return f"{float(value):.1f}%"

    return f"{float(value):.1f}"


def hl_player_data(player):
    """
    Return public player information.

    The hidden statistic is NOT included here.
    """

    return {
        "id": player.id,
        "name": player.name,
        "team": (
            player.team.name
            if player.team
            else "EuroLeague"
        ),
        "picture_url": player.picture_url or ""
    }


def hl_make_round(players, mode, streak, first_id=None):
    """
    Generate a new comparison.

    mode can be a specific statistic or 'random'.
    """

    available = hl_available_statistics(players)

    if not available:
        raise ValueError(
            "The database needs at least two players "
            "with different valid statistics."
        )

    if mode == "random":
        stat_key = random.choice(available)
    else:
        stat_key = mode

        if stat_key not in available:
            raise ValueError(
                "Not enough valid player data "
                "for this statistic."
            )

    first, second = hl_choose_pair(
        players,
        stat_key,
        first_id=first_id
    )

    return {
        "mode": mode,
        "stat": stat_key,
        "first_id": first.id,
        "second_id": second.id,
        "streak": streak,
        "active": True
    }


def hl_public_round(state, players_by_id, best):
    """
    Prepare the game data sent to JavaScript.

    Only the first player's statistic is visible.
    """

    first = players_by_id[state["first_id"]]
    second = players_by_id[state["second_id"]]

    stat_key = state["stat"]

    first_data = hl_player_data(first)

    first_data["value_display"] = hl_format_value(
        getattr(first, stat_key),
        stat_key
    )

    second_data = hl_player_data(second)

    return {
        "stat_key": stat_key,
        "stat_label": HL_STATISTICS[stat_key],
        "round": state["streak"] + 1,
        "streak": state["streak"],
        "best": best,
        "player_one": first_data,
        "player_two": second_data
    }

