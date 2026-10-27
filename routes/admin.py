from flask import render_template, jsonify, request, redirect, url_for, flash, abort, session, current_app
from flask_login import current_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timezone
from functools import wraps
import secrets, hmac, random, math
from extensions import db
from models import *
from routes.security import admin_required
from services.basketball_simulator import simulate_game

PLAYER_TOTAL_FIELDS = (
    "games_played", "total_points", "total_assists", "total_rebounds",
    "total_blocks", "total_steals", "total_turnovers", "total_fgm", "total_fga",
)

@admin_required
def admin_dashboard():
    return render_template("admin.html")


@admin_required
def admin_players():
    players = Player.query.order_by(Player.name).all()

    return render_template(
        "admin_players.html",
        players=players
    )


def read_player_statistics(form):
    """
    Validate the submitted season totals.
    Return a dictionary containing totals and calculated averages.
    """

    stats = {}

    for field in PLAYER_TOTAL_FIELDS:
        raw_value = form.get(field, "").strip()

        if not raw_value:
            raise ValueError(f"{field} is required.")

        try:
            value = int(raw_value)
        except ValueError:
            raise ValueError(f"{field} must be a whole number.")

        if value < 0:
            raise ValueError(f"{field} cannot be negative.")

        stats[field] = value

    games = stats["games_played"]
    fgm = stats["total_fgm"]
    fga = stats["total_fga"]

    if fgm > fga:
        raise ValueError(
            "Field goals made cannot exceed field goals attempted."
        )

    if games == 0 and any(
        stats[field] > 0
        for field in PLAYER_TOTAL_FIELDS
        if field != "games_played"
    ):
        raise ValueError(
            "Games played must be greater than zero "
            "when season totals are entered."
        )

    def average(total):
        return round(total / games, 2) if games > 0 else 0.0

    stats["points_per_game"] = average(stats["total_points"])
    stats["assists_per_game"] = average(stats["total_assists"])
    stats["rebounds_per_game"] = average(stats["total_rebounds"])
    stats["blocks_per_game"] = average(stats["total_blocks"])
    stats["steals_per_game"] = average(stats["total_steals"])

    stats["fg_percentage"] = (
        round(fgm / fga * 100, 2)
        if fga > 0
        else 0.0
    )

    return stats


def apply_player_statistics(player, stats):
    """Assign validated statistics to a Player model."""

    for field, value in stats.items():
        setattr(player, field, value)


@admin_required
def admin_add_player():

    teams = Team.query.order_by(Team.name).all()

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        nationality = request.form.get("nationality", "").strip()
        position = request.form.get("position", "").strip()
        picture_url = request.form.get("picture_url", "").strip()

        try:
            team_id = int(request.form.get("team_id", ""))

            rating = int(request.form.get("rating", "70"))
            offense = int(request.form.get("offense", "70"))
            defense = int(request.form.get("defense", "70"))

            if not name:
                raise ValueError("Player name is required.")

            if len(name) > 100 or len(nationality) > 50:
                raise ValueError("Name or nationality is too long.")

            if position not in ("PG", "SG", "SF", "PF", "C"):
                raise ValueError("Invalid player position.")

            if len(picture_url) > 200:
                raise ValueError(
                    "Picture URL must be 200 characters or fewer."
                )

            if not all(
                0 <= value <= 100
                for value in (rating, offense, defense)
            ):
                raise ValueError(
                    "Ratings must be between 0 and 100."
                )

            team = db.session.get(Team, team_id)

            if team is None:
                raise ValueError("Please select a valid team.")

            # Read totals and calculate averages.
            statistics = read_player_statistics(request.form)

        except (ValueError, TypeError) as error:
            flash(f"Invalid player information: {error}", "danger")
            return redirect(url_for("admin_add_player"))

        player = Player(
            name=name,
            nationality=nationality,
            position=position,
            picture_url=picture_url,
            rating=rating,
            offense=offense,
            defense=defense,
            team_id=team_id
        )

        apply_player_statistics(player, statistics)

        db.session.add(player)
        db.session.commit()

        flash("Player added successfully!", "success")
        return redirect(url_for("admin_players"))

    return render_template(
        "admin_player_form.html",
        player=None,
        teams=teams
    )


@admin_required
def admin_edit_player(player_id):

    player = db.get_or_404(Player, player_id)
    teams = Team.query.order_by(Team.name).all()

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        nationality = request.form.get("nationality", "").strip()
        position = request.form.get("position", "").strip()
        picture_url = request.form.get("picture_url", "").strip()

        try:
            team_id = int(request.form.get("team_id", ""))

            rating = int(request.form.get("rating", "70"))
            offense = int(request.form.get("offense", "70"))
            defense = int(request.form.get("defense", "70"))

            if not name:
                raise ValueError("Player name is required.")

            if len(name) > 100 or len(nationality) > 50:
                raise ValueError("Name or nationality is too long.")

            if position not in ("PG", "SG", "SF", "PF", "C"):
                raise ValueError("Invalid player position.")

            if len(picture_url) > 200:
                raise ValueError(
                    "Picture URL must be 200 characters or fewer."
                )

            if not all(
                0 <= value <= 100
                for value in (rating, offense, defense)
            ):
                raise ValueError(
                    "Ratings must be between 0 and 100."
                )

            team = db.session.get(Team, team_id)

            if team is None:
                raise ValueError("Please select a valid team.")

            # Read totals and calculate averages.
            statistics = read_player_statistics(request.form)

        except (ValueError, TypeError) as error:
            flash(f"Invalid player information: {error}", "danger")

            return redirect(
                url_for("admin_edit_player", player_id=player.id)
            )

        # Update player information.
        player.name = name
        player.nationality = nationality
        player.position = position
        player.picture_url = picture_url

        # Update ratings.
        player.rating = rating
        player.offense = offense
        player.defense = defense

        # Update team.
        player.team_id = team_id

        # Update totals and calculated averages.
        apply_player_statistics(player, statistics)

        db.session.commit()

        flash("Player updated successfully!", "success")
        return redirect(url_for("admin_players"))

    return render_template(
        "admin_player_form.html",
        player=player,
        teams=teams
    )


@admin_required
def admin_delete_player(player_id):
    player = db.get_or_404(Player, player_id)

    player_name = player.name

    db.session.delete(player)
    db.session.commit()

    flash(f"{player_name} was deleted.", "success")
    return redirect(url_for("admin_players"))


@admin_required
def admin_teams():
    teams = Team.query.order_by(Team.name).all()

    return render_template(
        "admin_teams.html",
        teams=teams
    )


@admin_required
def admin_add_team():

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        country = request.form.get("country", "").strip()
        record = request.form.get("record", "").strip()
        image_url = request.form.get("image_url", "").strip()
        biography = request.form.get("biography", "").strip()

        if not name:
            flash("Team name is required.", "danger")
            return redirect(url_for("admin_add_team"))

        if len(name) > 100 or len(country) > 100:
            flash("Team name or country is too long.", "danger")
            return redirect(url_for("admin_add_team"))

        if len(record) > 20 or len(image_url) > 500:
            flash("Record or logo path is too long.", "danger")
            return redirect(url_for("admin_add_team"))

        existing_team = Team.query.filter_by(name=name).first()

        if existing_team:
            flash("A team with this name already exists.", "danger")
            return redirect(url_for("admin_add_team"))

        team = Team(
            name=name,
            country=country,
            record=record,
            image_url=image_url,
            biography=biography
        )

        db.session.add(team)
        db.session.commit()

        flash("Team added successfully!", "success")
        return redirect(url_for("admin_teams"))

    return render_template("admin_team_form.html", team=None)


@admin_required
def admin_edit_team(team_id):

    team = db.get_or_404(Team, team_id)

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        country = request.form.get("country", "").strip()
        record = request.form.get("record", "").strip()
        image_url = request.form.get("image_url", "").strip()
        biography = request.form.get("biography", "").strip()

        if not name:
            flash("Team name is required.", "danger")
            return redirect(url_for("admin_edit_team", team_id=team.id))

        if len(name) > 100 or len(country) > 100:
            flash("Team name or country is too long.", "danger")
            return redirect(url_for("admin_edit_team", team_id=team.id))

        if len(record) > 20 or len(image_url) > 500:
            flash("Record or logo path is too long.", "danger")
            return redirect(url_for("admin_edit_team", team_id=team.id))

        existing_team = Team.query.filter(
            Team.name == name,
            Team.id != team.id
        ).first()

        if existing_team:
            flash("Another team already uses that name.", "danger")
            return redirect(url_for("admin_edit_team", team_id=team.id))

        team.name = name
        team.country = country
        team.record = record
        team.image_url = image_url
        team.biography = biography

        db.session.commit()

        flash("Team updated successfully!", "success")
        return redirect(url_for("admin_teams"))

    return render_template("admin_team_form.html", team=team)


@admin_required
def admin_delete_team(team_id):

    team = db.get_or_404(Team, team_id)

    if team.players:
        flash(
            "You cannot delete a team that still has players. "
            "Transfer or delete its players first.",
            "danger"
        )
        return redirect(url_for("admin_teams"))

    team_name = team.name

    # Remove associated team pictures first
    for picture in team.pictures:
        db.session.delete(picture)

    db.session.delete(team)
    db.session.commit()

    flash(f"{team_name} was deleted.", "success")
    return redirect(url_for("admin_teams"))


@admin_required
def admin_legends():
    legends = Legend.query.order_by(Legend.name).all()
    return render_template("admin_legends.html", legends=legends)


def save_legend_from_form(legend):
    """Validate form data and update a Legend object."""

    name = request.form.get("name", "").strip()
    nationality = request.form.get("nationality", "").strip()
    position = request.form.get("position", "").strip().upper()
    picture_url = request.form.get("picture_url", "").strip()
    peak_season = request.form.get("peak_season", "").strip()
    legendary_team = request.form.get("legendary_team", "").strip()

    if not name:
        raise ValueError("Legend name is required.")

    if position not in ("PG", "SG", "SF", "PF", "C"):
        raise ValueError("Please select a valid position.")

    if (len(name) > 100 or len(nationality) > 50
            or len(picture_url) > 500 or len(peak_season) > 20
            or len(legendary_team) > 100):
        raise ValueError("One or more text fields are too long.")

    existing = Legend.query.filter(
        Legend.name == name,
        Legend.id != legend.id
    ).first()

    if existing:
        raise ValueError("A legend with this name already exists.")

    ratings = {}
    for field in ("rating", "offense", "defense"):
        value = int(request.form.get(field, "90"))
        if not 0 <= value <= 100:
            raise ValueError(f"{field} must be between 0 and 100.")
        ratings[field] = value

    statistics = {}
    for field in (
        "points_per_game", "assists_per_game",
        "rebounds_per_game", "blocks_per_game",
        "steals_per_game", "fg_percentage"
    ):
        value = float(request.form.get(field, "0"))
        if not math.isfinite(value) or not 0 <= value <= 100:
            raise ValueError(f"{field} must be between 0 and 100.")
        statistics[field] = value

    legend.name = name
    legend.nationality = nationality
    legend.position = position
    legend.picture_url = picture_url
    legend.peak_season = peak_season
    legend.legendary_team = legendary_team

    for field, value in {**ratings, **statistics}.items():
        setattr(legend, field, value)


@admin_required
def admin_add_legend():
    if request.method == "POST":
        legend = Legend()

        try:
            save_legend_from_form(legend)
            db.session.add(legend)
            db.session.commit()
        except (ValueError, TypeError, IntegrityError) as error:
            db.session.rollback()
            flash(f"Could not add legend: {error}", "danger")
            return redirect(url_for("admin_add_legend"))

        flash("Legend added successfully!", "success")
        return redirect(url_for("admin_legends"))

    return render_template("admin_legend_form.html", legend=None)


@admin_required
def admin_edit_legend(legend_id):
    legend = db.get_or_404(Legend, legend_id)

    if request.method == "POST":
        try:
            save_legend_from_form(legend)
            db.session.commit()
        except (ValueError, TypeError, IntegrityError) as error:
            db.session.rollback()
            flash(f"Could not update legend: {error}", "danger")
            return redirect(
                url_for("admin_edit_legend", legend_id=legend_id)
            )

        flash("Legend updated successfully!", "success")
        return redirect(url_for("admin_legends"))

    return render_template("admin_legend_form.html", legend=legend)


@admin_required
def admin_delete_legend(legend_id):
    legend = db.get_or_404(Legend, legend_id)
    name = legend.name

    db.session.delete(legend)
    db.session.commit()

    flash(f"{name} was deleted.", "success")
    return redirect(url_for("admin_legends"))


def admin_user_csrf_token():
    if "admin_user_csrf" not in session:
        session["admin_user_csrf"] = secrets.token_urlsafe(32)
    return session["admin_user_csrf"]


def verify_admin_user_csrf():
    supplied = request.form.get("csrf_token", "")
    expected = session.get("admin_user_csrf", "")

    if not expected or not secrets.compare_digest(supplied, expected):
        abort(400, description="Invalid form security token.")


@admin_required
def admin_users():
    users = User.query.order_by(User.username).all()

    return render_template(
        "admin_users.html",
        users=users,
        csrf_token=admin_user_csrf_token()
    )


@admin_required
def admin_edit_user(user_id):
    user = db.get_or_404(User, user_id)

    if request.method == "POST":
        verify_admin_user_csrf()

        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        role = request.form.get("role", "").strip()

        if not username or not email:
            flash("Username and email are required.", "danger")
            return redirect(url_for("admin_edit_user", user_id=user.id))

        if len(username) > 50 or len(email) > 120:
            flash("Username or email is too long.", "danger")
            return redirect(url_for("admin_edit_user", user_id=user.id))

        if "@" not in email or email.startswith("@") or email.endswith("@"):
            flash("Please enter a valid email address.", "danger")
            return redirect(url_for("admin_edit_user", user_id=user.id))

        if role not in ("user", "admin"):
            flash("Invalid account role.", "danger")
            return redirect(url_for("admin_edit_user", user_id=user.id))

        if user.id == current_user.id and role != "admin":
            flash("You cannot remove your own admin access.", "danger")
            return redirect(url_for("admin_edit_user", user_id=user.id))

        existing_username = User.query.filter(
            User.username == username,
            User.id != user.id
        ).first()

        if existing_username:
            flash("This username is already taken.", "danger")
            return redirect(url_for("admin_edit_user", user_id=user.id))

        existing_email = User.query.filter(
            User.email == email,
            User.id != user.id
        ).first()

        if existing_email:
            flash("This email is already registered.", "danger")
            return redirect(url_for("admin_edit_user", user_id=user.id))

        user.username = username
        user.email = email
        user.role = role

        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("Username or email already exists.", "danger")
            return redirect(url_for("admin_edit_user", user_id=user.id))

        flash("User updated successfully!", "success")
        return redirect(url_for("admin_users"))

    return render_template(
        "admin_user_form.html",
        user=user,
        csrf_token=admin_user_csrf_token()
    )


@admin_required
def admin_delete_user(user_id):
    verify_admin_user_csrf()

    user = db.get_or_404(User, user_id)

    if user.id == current_user.id:
        flash("You cannot delete your own account.", "danger")
        return redirect(url_for("admin_users"))

    if user.role == "admin" and User.query.filter_by(role="admin").count() <= 1:
        flash("You cannot delete the last administrator.", "danger")
        return redirect(url_for("admin_users"))

    username = user.username

    try:
        # Delete dependent records before deleting the account.
        DraftRun.query.filter_by(user_id=user.id).delete()
        UserAchievement.query.filter_by(user_id=user.id).delete()
        UserTitle.query.filter_by(user_id=user.id).delete()

        db.session.delete(user)
        db.session.commit()

    except IntegrityError:
        db.session.rollback()
        flash(
            "This account has other related records and could not be deleted.",
            "danger"
        )
        return redirect(url_for("admin_users"))

    flash(f"User {username} was deleted.", "success")
    return redirect(url_for("admin_users"))

