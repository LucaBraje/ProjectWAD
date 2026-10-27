"""Profile account, favorite team, titles, and basketball grid endpoints."""
from flask import request, jsonify, current_app
from flask_login import login_required, current_user
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from extensions import db
from models import User, Team, UserAchievement, UserTitle
from services.achievement_service import GRID_ACHIEVEMENTS, PROFILE_TITLES, sync_grid_achievements

_BasketballGridGame = None

def configure(dependencies):
    global _BasketballGridGame
    _BasketballGridGame = dependencies["BasketballGridGame"]

@login_required
def update_profile_account():
    """Update the authenticated user's account details."""
    # Browser-side protection against cross-site requests.
    origin = request.headers.get("Origin")
    if origin and origin.rstrip("/") != request.host_url.rstrip("/"):
        return jsonify({"error": "Invalid request origin."}), 403

    # Only accept JSON objects, not forms or arbitrary content.
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Expected JSON account details."}), 400

    username = data.get("username")
    email = data.get("email")

    if not isinstance(username, str) or not isinstance(email, str):
        return jsonify({"error": "Username and email must be text."}), 400

    username = username.strip()
    email = email.strip().lower()

    # Match the database column limits (User.username=50, User.email=120).
    if not 3 <= len(username) <= 50:
        return jsonify({"error": "Username must be 3 to 50 characters."}), 400

    if not 3 <= len(email) <= 120 or email.count("@") != 1:
        return jsonify({"error": "Enter a valid email address."}), 400

    local, domain = email.rsplit("@", 1)
    if (not local or not domain or "." not in domain or
            any(char.isspace() for char in email)):
        return jsonify({"error": "Enter a valid email address."}), 400

    # Do not treat the current user's own values as duplicates.
    existing_username = User.query.filter(
        func.lower(User.username) == username.lower(),
        User.id != current_user.id
    ).first()
    if existing_username:
        return jsonify({"error": "This username is already taken."}), 409

    existing_email = User.query.filter(
        func.lower(User.email) == email,
        User.id != current_user.id
    ).first()
    if existing_email:
        return jsonify({"error": "An account with this email already exists."}), 409

    try:
        current_user.username = username
        current_user.email = email
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "Username or email is already in use."}), 409
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Failed to update profile account")
        return jsonify({"error": "Could not save account details."}), 500

    return jsonify({
        "success": True,
        "username": current_user.username,
        "email": current_user.email
    })


@login_required
def profile_favorite_team():
    if request.method == "GET":
        teams = Team.query.order_by(Team.name).all()

        return jsonify({
            "favorite_team_id": current_user.favorite_team_id,
            "teams": [
                {
                    "id": team.id,
                    "name": team.name,
                    "image_url": team.image_url
                }
                for team in teams
            ]
        })

    data = request.get_json(silent=True) or {}
    team_id = data.get("team_id")

    # Allow users to clear their favorite team.
    if team_id is None:
        current_user.favorite_team_id = None
        db.session.commit()

        return jsonify({
            "success": True,
            "favorite_team_id": None
        })

    try:
        team_id = int(team_id)
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid team ID."}), 400

    team = db.session.get(Team, team_id)

    if team is None:
        return jsonify({"error": "Team not found."}), 404

    current_user.favorite_team_id = team.id
    db.session.commit()

    return jsonify({
        "success": True,
        "favorite_team_id": team.id,
        "team_name": team.name,
        "image_url": team.image_url
    })


@login_required
def basketball_grid_profile():
    grid_record = _BasketballGridGame.query.filter_by(user_id=current_user.id).first()
    sync_grid_achievements(current_user.id, grid_record)
    games = grid_record.games if grid_record else 0
    wins = grid_record.wins if grid_record else 0
    stats = {
        "games": games,
        "wins": wins,
        "losses": grid_record.losses if grid_record else 0,
        "best_correct": grid_record.best_correct if grid_record else 0,
        "win_rate": round(wins * 100 / games, 1) if games else 0,
    }
    unlocked = {item.achievement_key for item in UserAchievement.query.filter_by(user_id=current_user.id).all()}
    return jsonify({
        "stats": stats,
        "achievements": [dict(key=key, **definition, unlocked=(key in unlocked)) for key, definition in GRID_ACHIEVEMENTS.items()]
    })


@login_required
def profile_titles():
    sync_grid_achievements(current_user.id, _BasketballGridGame.query.filter_by(user_id=current_user.id).first())
    achievements = UserAchievement.query.filter_by(
        user_id=current_user.id
    ).all()

    unlocked_keys = {
        achievement.achievement_key
        for achievement in achievements
    }

    equipped = UserTitle.query.filter_by(
        user_id=current_user.id
    ).first()

    equipped_key = equipped.title_key if equipped else None

    return jsonify({
        "equipped_title": equipped_key,
        "titles": [
            {
                "key": key,
                "name": name,
                "unlocked": key in unlocked_keys,
                "equipped": key == equipped_key
            }
            for key, name in PROFILE_TITLES.items()
        ]
    })


@login_required
def equip_profile_title():
    sync_grid_achievements(current_user.id, _BasketballGridGame.query.filter_by(user_id=current_user.id).first())
    data = request.get_json(silent=True) or {}
    title_key = data.get("title_key")

    # None means unequip the current title.
    if title_key is not None:
        if not isinstance(title_key, str):
            return jsonify({"error": "Invalid title."}), 400

        if title_key not in PROFILE_TITLES:
            return jsonify({"error": "Unknown title."}), 400

        achievement = UserAchievement.query.filter_by(
            user_id=current_user.id,
            achievement_key=title_key
        ).first()

        if achievement is None:
            return jsonify({
                "error": "You haven't unlocked this title yet."
            }), 403

    equipped = UserTitle.query.filter_by(
        user_id=current_user.id
    ).first()

    if equipped is None and title_key is not None:
        equipped = UserTitle(
            user_id=current_user.id,
            title_key=title_key
        )
        db.session.add(equipped)

    elif equipped is not None:
        if title_key is None:
            db.session.delete(equipped)
        else:
            equipped.title_key = title_key

    db.session.commit()

    return jsonify({
        "success": True,
        "equipped_title": title_key,
        "title_name": (
            PROFILE_TITLES[title_key]
            if title_key is not None
            else None
        )
    })


