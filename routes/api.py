"""Extracted routes from the original app.py."""
from flask import request, jsonify
from models import Team, Player, Legend


def get_players():
    query = Player.query.join(Team)

    search = request.args.get("search", "").strip()
    team_name = request.args.get("team", "")
    position = request.args.get("position", "")

    if search:
        query = query.filter(Player.name.ilike(f"%{search}%"))

    if team_name:
        query = query.filter(Team.name == team_name)

    if position:
        query = query.filter(Player.position == position)

    players = query.order_by(Player.name).all()

    return jsonify([
        {
            "id": player.id,
            "name": player.name,
            "nationality": player.nationality,
            "picture_url": player.picture_url,
            "position": player.position,
            "rating": player.rating,
            "defense": player.defense,
            "offense": player.offense,
            "points_per_game": player.points_per_game,
            "assists_per_game": player.assists_per_game,
            "rebounds_per_game": player.rebounds_per_game,
            "blocks_per_game": player.blocks_per_game,
            "steals_per_game": player.steals_per_game,
            "fg_percentage": player.fg_percentage,
            "team": player.team.name,
            "team_image_url": player.team.image_url,
            "games_played": player.games_played,
            "total_points": player.total_points,
            "total_assists": player.total_assists,
            "total_rebounds": player.total_rebounds,
            "total_blocks": player.total_blocks,
            "total_steals": player.total_steals,
            "total_turnovers": player.total_turnovers,
            "total_fgm": player.total_fgm,
            "total_fga": player.total_fga,
        }
        for player in players
    ])


def get_teams():
    teams = Team.query.order_by(Team.name).all()

    return jsonify([
        {
            "id": team.id,
            "name": team.name,
            "country": team.country,
            "record": team.record,
            "image_url": team.image_url,
        }
        for team in teams
    ])



def get_legends():
    position = request.args.get("position", "").upper().strip()

    query = Legend.query

    if position:
        if position not in ("PG", "SG", "SF", "PF", "C"):
            return jsonify({"error": "Invalid position"}), 400

        query = query.filter_by(position=position)

    legends = query.order_by(
        Legend.rating.desc(),
        Legend.name.asc()
    ).all()

    return jsonify([
        {
            "id": legend.id,
            "name": legend.name,
            "nationality": legend.nationality,
            "position": legend.position,
            "rating": legend.rating,
            "offense": legend.offense,
            "defense": legend.defense,
            "points_per_game": legend.points_per_game,
            "assists_per_game": legend.assists_per_game,
            "rebounds_per_game": legend.rebounds_per_game,
            "blocks_per_game": legend.blocks_per_game,
            "steals_per_game": legend.steals_per_game,
            "fg_percentage": legend.fg_percentage,
            "picture_url": legend.picture_url,
            "peak_season": legend.peak_season,
            "legendary_team": legend.legendary_team,
            "stats_type": legend.stats_type,
            "is_legend": True
        }
        for legend in legends
    ])
