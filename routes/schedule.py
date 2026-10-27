"""Public fictional EuroLeague schedule endpoints."""
from flask import render_template, jsonify
from models import SimulationSeason, SimulationWeek, SimulationGame

def schedule():
    return render_template("schedule.html")


def api_schedule(week_number):

    season = SimulationSeason.query.filter_by(
        status="active"
    ).first()

    if not season:
        return jsonify({
            "error": "No active season found."
        }), 404

    week = SimulationWeek.query.filter_by(
        season_id=season.id,
        week_number=week_number
    ).first()

    if not week:
        return jsonify({
            "error": "Week not found."
        }), 404

    games = (
        SimulationGame.query
        .filter_by(week_id=week.id)
        .order_by(SimulationGame.id)
        .all()
    )

    games_data = []

    for game in games:

        games_data.append({
            "id": game.id,
            "status": game.status,

            "home_team": {
                "id": game.home_team.id,
                "name": game.home_team.name,
                "image_url": game.home_team.image_url
            },

            "away_team": {
                "id": game.away_team.id,
                "name": game.away_team.name,
                "image_url": game.away_team.image_url
            },

            "home_score": game.home_score,
            "away_score": game.away_score
        })

    return jsonify({
        "season": {
            "id": season.id,
            "name": season.name,
            "current_week": season.current_week
        },
        "week": week.week_number,
        "total_weeks": 38,
        "status": week.status,
        "games": games_data
    })

