"""Extracted routes from the original app.py."""
from flask import render_template
from flask_login import login_required
from models import Team, Player


def home():
    return render_template("index.html")


def player_directory():
    return render_template("players.html")


def team_directory():
    teams = Team.query.order_by(Team.name).all()
    return render_template("teams.html", teams=teams)


def team_profile(team_id):
    team = Team.query.get_or_404(team_id)

    players = Player.query.filter_by(
        team_id=team.id
    ).order_by(Player.rating.desc()).all()

    return render_template(
        "team_profile.html",
        team=team,
        players=players
    )


@login_required
def profile():
    return render_template("profile.html")

