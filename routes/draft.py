"""Draft Mode HTTP endpoints, retaining legacy URL and endpoint names."""
from flask import render_template, jsonify, request, current_app
from flask_login import login_required, current_user
from sqlalchemy import func
from uuid import uuid4
from extensions import db
from models import Team, Player, Legend, DraftRun, UserTitle, UserAchievement
from services.draft_service import (
    DRAFT_POSITIONS, calculate_draft_rating, run_draft_season,
)

_unlock_draft_achievements = None
DRAFT_ACHIEVEMENTS = {}

def configure(dependencies):
    global _unlock_draft_achievements, DRAFT_ACHIEVEMENTS
    _unlock_draft_achievements = dependencies["unlock_draft_achievements"]
    DRAFT_ACHIEVEMENTS = dependencies["DRAFT_ACHIEVEMENTS"]

def draft_mode():
    return render_template('draft.html')


def draft_pool():
    teams = Team.query.order_by(Team.id).all()
    players = Player.query.order_by(Player.id).all()
    legends = Legend.query.order_by(Legend.id).all()

    return jsonify({
        "legends": [
            {
                "id": p.id, "name": p.name, "nationality": p.nationality,
                "position": p.position, "rating": p.rating,
                "offense": p.offense, "defense": p.defense,
                "picture_url": p.picture_url,
                "points_per_game": p.points_per_game,
                "assists_per_game": p.assists_per_game,
                "rebounds_per_game": p.rebounds_per_game,
                "blocks_per_game": p.blocks_per_game,
                "steals_per_game": p.steals_per_game,
                "fg_percentage": p.fg_percentage,
                "team_name": p.legendary_team,
                "peak_season": p.peak_season, "is_legend": True
            } for p in legends
        ],
        'teams': [
            {
                'id': team.id,
                'name': team.name,
                'image_url': team.image_url,
            }
            for team in teams
        ],
        'players': [
            {
                'id': player.id,
                'name': player.name,
                'picture_url': player.picture_url,
                'nationality': player.nationality,
                'position': player.position,
                'rating': player.rating,
                'offense': player.offense,
                'defense': player.defense,
                'points_per_game': player.points_per_game,
                'assists_per_game': player.assists_per_game,
                'rebounds_per_game': player.rebounds_per_game,
                "blocks_per_game": player.blocks_per_game,
                "steals_per_game": player.steals_per_game,
                'team_name': player.team.name if player.team else None,
                'team_id': player.team_id,
            }
            for player in players
        ],
    })


def simulate_draft_api():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "Invalid request."}), 400

    club_id = data.get("club_id")
    lineup_data = data.get("lineup")
    run_token = data.get("run_token")

    if not isinstance(lineup_data, dict):
        return jsonify({"error": "Invalid lineup."}), 400

    if set(lineup_data.keys()) != set(DRAFT_POSITIONS):
        return jsonify({
            "error": "Your lineup must contain PG, SG, SF, PF and C."
        }), 400

    try:
        club_id = int(club_id)
        references = {}
        for pos in DRAFT_POSITIONS:
            item = lineup_data[pos]
            if not isinstance(item, dict) or item.get("type") not in ("player", "legend"):
                raise ValueError("Invalid player reference")
            player_id = int(item["id"])
            if player_id <= 0:
                raise ValueError("Invalid player ID")
            references[pos] = {"type": item["type"], "id": player_id}
    except (ValueError, TypeError, KeyError):
        return jsonify({"error": "Invalid player or club ID."}), 400

    keys = [(p["type"], p["id"]) for p in references.values()]
    if len(set(keys)) != 5:
        return jsonify({"error": "You cannot draft the same player twice."}), 400
    if sum(p["type"] == "legend" for p in references.values()) > 1:
        return jsonify({"error": "Only one legend is allowed per draft."}), 400

    club = db.session.get(Team, club_id)
    if club is None:
        return jsonify({"error": "Club not found."}), 404

    lineup = {}
    for pos, ref in references.items():
        model = Legend if ref["type"] == "legend" else Player
        entry = db.session.get(model, ref["id"])
        if entry is None:
            return jsonify({"error": "One or more players were not found."}), 400
        lineup[pos] = entry

    rating = calculate_draft_rating(lineup)

    # Guests receive a result but don't save anything.
    is_logged_in = current_user.is_authenticated

    # For logged-in users, check whether this draft was saved already.
    if is_logged_in:
        try:
            token = str(uuid4()) if run_token is None else str(
                __import__("uuid").UUID(str(run_token))
            )
        except (ValueError, TypeError, AttributeError):
            return jsonify({"error": "Invalid simulation token."}), 400

        existing = DraftRun.query.filter_by(
            run_token=token
        ).first()

        if existing:
            if existing.user_id != current_user.id:
                return jsonify({"error": "Invalid simulation token."}), 409

            return jsonify({
                "saved": True,
                "already_saved": True,
                "run_id": existing.id,
                "result": {
                    "wins": existing.wins,
                    "losses": existing.losses,
                    "seed": existing.seed,
                    "totalTeams": Team.query.count(),
                    "teamStrength": existing.team_score,
                    "outcome": existing.outcome,
                    "details": "This simulation was already saved."
                },
                "new_achievements": []
            })

    all_teams = Team.query.order_by(Team.id).all()
    all_players = Player.query.all()

    result = run_draft_season(
        club, rating, all_teams, all_players
    )

    if not is_logged_in:
        return jsonify({
            "saved": False,
            "result": result,
            "new_achievements": []
        })

    draft_run = DraftRun(
        user_id=current_user.id,
        club_id=club.id,
        team_score=rating["total_points"],
        base_score=rating["base_score"],
        out_of_position=rating["out_of_position"],
        wins=result["wins"],
        losses=result["losses"],
        seed=result["seed"],
        outcome=result["outcome"],
        lineup=references,
        run_token=token
    )

    try:
        db.session.add(draft_run)

        # Make the new run visible to achievement queries.
        db.session.flush()

        unlocked = _unlock_draft_achievements(
            current_user.id,
            draft_run
        )

        db.session.commit()

    except IntegrityError:
        db.session.rollback()
        return jsonify({
            "error": "This draft was already submitted. Please refresh your draft history."
        }), 409

    except Exception:
        db.session.rollback()
        current_app.logger.exception("Failed to save draft")
        return jsonify({
            "error": "Could not save the simulation."
        }), 500

    return jsonify({
        "saved": True,
        "already_saved": False,
        "run_id": draft_run.id,
        "result": result,
        "new_achievements": unlocked
    })


@login_required
def my_draft_stats():

    user_id = current_user.id

    drafts = DraftRun.query.filter_by(
        user_id=user_id
    )

    total_drafts = drafts.count()

    best_score = db.session.query(
        func.max(DraftRun.team_score)
    ).filter(
        DraftRun.user_id == user_id
    ).scalar()

    average_score = db.session.query(
        func.avg(DraftRun.team_score)
    ).filter(
        DraftRun.user_id == user_id
    ).scalar()

    championships = drafts.filter_by(
        outcome="EUROLEAGUE CHAMPIONS"
    ).count()

    playoff_outcomes = [
        "PLAYOFF ELIMINATION",
        "FINAL FOUR",
        "EUROLEAGUE FINALIST",
        "EUROLEAGUE CHAMPIONS"
    ]

    final_four_outcomes = [
        "FINAL FOUR",
        "EUROLEAGUE FINALIST",
        "EUROLEAGUE CHAMPIONS"
    ]

    playoffs = drafts.filter(
        DraftRun.outcome.in_(playoff_outcomes)
    ).count()

    final_fours = drafts.filter(
        DraftRun.outcome.in_(final_four_outcomes)
    ).count()

    best_draft = drafts.order_by(
        DraftRun.team_score.desc()
    ).first()

    achievements = UserAchievement.query.filter_by(
        user_id=user_id
    ).all()

    equipped = UserTitle.query.filter_by(
        user_id=user_id
    ).first()

    return jsonify({
        "total_drafts": total_drafts,
        "best_score": round(best_score or 0, 1),
        "average_score": round(average_score or 0, 1),
        "championships": championships,
        "playoff_appearances": playoffs,
        "final_four_appearances": final_fours,

        "best_draft": {
            "score": best_draft.team_score,
            "lineup": best_draft.lineup,
            "club_id": best_draft.club_id,
            "outcome": best_draft.outcome
        } if best_draft else None,

        "achievements": [
            {
                "key": a.achievement_key,
                "name": DRAFT_ACHIEVEMENTS.get(
                    a.achievement_key, {}
                ).get("name", a.achievement_key)
            }
            for a in achievements
        ],

        "equipped_title": (
            equipped.title_key if equipped else None
        )
    })

