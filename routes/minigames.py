"""Other Games and Higher or Lower HTTP endpoints."""
from flask import render_template, request, jsonify, session
from flask_login import login_required, current_user
from extensions import db
from models import Player, HigherLowerStats, UserAchievement
from services.minigame_service import (
    HL_STATISTICS, HL_SESSION_KEY, HL_ACHIEVEMENTS,
    hl_get_stats, hl_unlock_achievements, hl_valid_players,
    hl_available_statistics, hl_choose_pair, hl_format_value,
    hl_player_data, hl_make_round, hl_public_round,
)

def other_games():
    return render_template("other_games.html")


def higher_or_lower():
    return render_template("higher_or_lower.html")



# =====================================================
# HIGHER OR LOWER — START
# =====================================================

@login_required
def hl_start():
    data = request.get_json(silent=True) or {}
    mode = data.get("stat", "random")

    if mode != "random" and mode not in HL_STATISTICS:
        return jsonify({"error": "Invalid statistic."}), 400

    players = Player.query.all()

    try:
        state = hl_make_round(players, mode, streak=0)
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    stats = hl_get_stats()

    # Starting a new run abandons any previous unfinished run.
    stats.current_streak = 0
    db.session.commit()

    session[HL_SESSION_KEY] = state

    players_by_id = {p.id: p for p in players}

    return jsonify(
        hl_public_round(
            state,
            players_by_id,
            stats.best_streak or 0
        )
    )



@login_required
def hl_guess():
    data = request.get_json(silent=True) or {}
    guess = data.get("guess")

    if guess not in ("higher", "lower"):
        return jsonify({"error": "Invalid guess."}), 400

    state = session.get(HL_SESSION_KEY)

    if not state or not state.get("active"):
        return jsonify({
            "error": "No active game. Start a new game."
        }), 400

    players = Player.query.all()
    players_by_id = {p.id: p for p in players}

    first = players_by_id.get(state["first_id"])
    second = players_by_id.get(state["second_id"])

    if first is None or second is None:
        session.pop(HL_SESSION_KEY, None)
        return jsonify({
            "error": "Player data changed. Restart the game."
        }), 409

    stat_key = state["stat"]

    first_value = float(getattr(first, stat_key))
    second_value = float(getattr(second, stat_key))

    correct_answer = (
        "higher" if second_value > first_value else "lower"
    )

    correct = guess == correct_answer

    revealed_value = hl_format_value(
        second_value,
        stat_key
    )

    stats = hl_get_stats()

    # Every submitted guess counts.
    stats.total_guesses = (stats.total_guesses or 0) + 1

    if correct:
        new_streak = state["streak"] + 1

        # Prepare the next round before saving the answer.
        try:
            next_state = hl_make_round(
                players,
                state["mode"],
                streak=new_streak,
                first_id=second.id
            )
        except ValueError:
            db.session.rollback()
            return jsonify({
                "error": "Cannot generate the next comparison."
            }), 409

        stats.total_correct = (stats.total_correct or 0) + 1
        stats.current_streak = new_streak
        stats.best_streak = max(
            stats.best_streak or 0,
            new_streak
        )

        unlocked = hl_unlock_achievements(stats)
        best = stats.best_streak

        db.session.commit()
        session[HL_SESSION_KEY] = next_state

        return jsonify({
            "correct": True,
            "revealed_value": revealed_value,
            "streak": new_streak,
            "best": best,
            "new_achievements": unlocked,
            "next_round": hl_public_round(
                next_state,
                players_by_id,
                best
            )
        })

    # One incorrect guess ends the run.
    final_streak = state["streak"]

    stats.total_games = (stats.total_games or 0) + 1
    stats.current_streak = 0
    stats.best_streak = max(
        stats.best_streak or 0,
        final_streak
    )

    unlocked = hl_unlock_achievements(stats)
    best = stats.best_streak

    db.session.commit()

    state["active"] = False
    session[HL_SESSION_KEY] = state

    return jsonify({
        "correct": False,
        "game_over": True,
        "revealed_value": revealed_value,
        "correct_answer": correct_answer,
        "streak": final_streak,
        "best": best,
        "new_achievements": unlocked
    })


@login_required
def hl_my_stats():
    stats = HigherLowerStats.query.filter_by(
        user_id=current_user.id
    ).first()

    achievements = UserAchievement.query.filter_by(
        user_id=current_user.id
    ).all()

    unlocked = {
        achievement.achievement_key
        for achievement in achievements
    }

    if stats is None:
        best = games = correct = guesses = 0
    else:
        best = stats.best_streak or 0
        games = stats.total_games or 0
        correct = stats.total_correct or 0
        guesses = stats.total_guesses or 0

    accuracy = round(
        correct / guesses * 100, 1
    ) if guesses else 0

    return jsonify({
        "best_streak": best,
        "total_games": games,
        "total_correct": correct,
        "total_guesses": guesses,
        "accuracy": accuracy,
        "achievements": [
            {
                "key": key,
                "name": definition["name"],
                "description": definition["description"],
                "unlocked": key in unlocked
            }
            for key, definition in HL_ACHIEVEMENTS.items()
        ]
    })

