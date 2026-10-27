"""Fantasy squad builder, lineup and dashboard endpoints.

Registered with explicit endpoint names to preserve existing url_for calls.
"""
from datetime import datetime, timezone
from decimal import Decimal
from flask import render_template, jsonify, request, redirect, url_for, flash, abort, current_app
from flask_login import login_required, current_user
from sqlalchemy import func
from extensions import db
from models import (Team, Player, FantasySquad, FantasySquadPlayer, FantasyRoundLineup,
                    FantasyRoundScore, SimulationSeason, SimulationWeek, SimulationGame,
                    SimulationPlayerStats)
from services.fantasy_service import (FANTASY_BUDGET, FANTASY_POSITIONS,
    fantasy_player_price, fantasy_current_season, fantasy_squad_editable,
    fantasy_validate_squad, fantasy_get_lineup, fantasy_lineup_editable,
    fantasy_default_lineup, fantasy_validate_lineup)

valid_admin_form_token = None

def configure(dependencies):
    global valid_admin_form_token
    valid_admin_form_token = dependencies["valid_admin_form_token"]

@login_required
def fantasy():

    season = fantasy_current_season()

    if season is None:
        flash("No active Fantasy season is available.", "warning")
        return redirect(url_for("home"))

    squad = FantasySquad.query.filter_by(
        user_id=current_user.id,
        season_id=season.id
    ).first()

    selected_ids = []

    if squad:
        selected_ids = [
            entry.player_id
            for entry in squad.players
        ]

    players = (
        Player.query
        .order_by(Player.rating.desc(), Player.name)
        .all()
    )

    player_data = []

    for player in players:

        player_data.append({
            "id": player.id,
            "name": player.name,
            "position": player.position,
            "rating": player.rating or 70,
            "team_id": player.team_id,
            "team": player.team.name,
            "picture_url": player.picture_url,
            "price": fantasy_player_price(player)
        })

    teams = Team.query.order_by(Team.name).all()

    return render_template(
        "fantasy.html",
        season=season,
        squad=squad,
        players=player_data,
        teams=teams,
        selected_ids=selected_ids,
        editable=fantasy_squad_editable(season),
        budget=FANTASY_BUDGET
    )


@login_required
def fantasy_save():

    if not valid_admin_form_token():
        abort(400, description="Invalid form security token.")

    season = fantasy_current_season()

    if not fantasy_squad_editable(season):
        flash(
            "Squad editing is closed because Round 1 "
            "has already started.",
            "danger"
        )
        return redirect(url_for("fantasy"))

    try:

        raw_ids = request.form.get("player_ids", "")

        player_ids = [
            int(value)
            for value in raw_ids.split(",")
            if value.strip()
        ]

        players, total_price = fantasy_validate_squad(
            player_ids
        )

        squad = FantasySquad.query.filter_by(
            user_id=current_user.id,
            season_id=season.id
        ).first()

        if squad is None:

            squad = FantasySquad(
                user_id=current_user.id,
                season_id=season.id,
                name="My Fantasy Team"
            )

            db.session.add(squad)
            db.session.flush()

        else:

            # A changed squad invalidates previously saved lineups.
            FantasyRoundLineup.query.filter_by(
                squad_id=squad.id
            ).delete(synchronize_session=False)

            squad.players.clear()
            db.session.flush()

        squad.budget_remaining = (
            FANTASY_BUDGET - total_price
        )

        for player in players:

            entry = FantasySquadPlayer(
                squad_id=squad.id,
                player_id=player.id,
                purchase_price=fantasy_player_price(player)
            )

            squad.players.append(entry)

        db.session.commit()

        flash(
            "Your Fantasy squad was saved successfully!",
            "success"
        )

    except (ValueError, TypeError) as error:

        db.session.rollback()
        flash(str(error), "danger")

    except Exception:

        db.session.rollback()
        current_app.logger.exception("Failed to save Fantasy squad")

        flash(
            "Could not save your Fantasy squad.",
            "danger"
        )

    return redirect(url_for("fantasy"))


@login_required
def fantasy_lineup():

    # Support both an active season and the most recently
    # completed season, so users can review their final lineup.
    season = (
        SimulationSeason.query
        .filter_by(status="active")
        .order_by(SimulationSeason.id.desc())
        .first()
    )

    if season is None:
        season = (
            SimulationSeason.query
            .filter_by(status="completed")
            .order_by(SimulationSeason.id.desc())
            .first()
        )

    if season is None:
        flash("No Fantasy season is available.", "warning")
        return redirect(url_for("home"))

    squad = FantasySquad.query.filter_by(
        user_id=current_user.id,
        season_id=season.id
    ).first()

    if squad is None or len(squad.players) != 10:
        flash("Build your Fantasy squad first.", "warning")
        return redirect(url_for("fantasy"))

    requested_round = request.args.get(
        "round", season.current_week, type=int
    )

    if requested_round < 1 or requested_round > season.current_week:
        abort(404)

    week = SimulationWeek.query.filter_by(
        season_id=season.id,
        week_number=requested_round
    ).first_or_404()

    lineup_entries = fantasy_get_lineup(squad, week)

    if len(lineup_entries) == 10:
        starter_ids = [
            entry.player_id
            for entry in lineup_entries
            if entry.is_starter
        ]

        captain_id = next(
            (
                entry.player_id
                for entry in lineup_entries
                if entry.is_captain
            ),
            None
        )

    elif fantasy_lineup_editable(season, week):
        starter_ids, captain_id = fantasy_default_lineup(
            squad, week
        )
        starter_ids = list(starter_ids)

    else:
        # Do not invent a historical lineup after a round
        # has already locked.
        starter_ids = []
        captain_id = None

    players = sorted(
        [entry.player for entry in squad.players],
        key=lambda player: (
            ("PG", "SG", "SF", "PF", "C").index(player.position),
            -(player.rating or 0)
        )
    )

    return render_template(
        "fantasy_lineup.html",
        season=season,
        week=week,
        squad=squad,
        players=players,
        starter_ids=starter_ids,
        captain_id=captain_id,
        editable=fantasy_lineup_editable(season, week),
        lineup_exists=len(lineup_entries) == 10
    )


@login_required
def fantasy_lineup_save():

    if not valid_admin_form_token():
        abort(400, description="Invalid form security token.")

    season = fantasy_current_season()

    if season is None:
        abort(404)

    week = SimulationWeek.query.filter_by(
        season_id=season.id,
        week_number=season.current_week
    ).first_or_404()

    if not fantasy_lineup_editable(season, week):
        flash("This round's lineup is locked.", "danger")
        return redirect(url_for("fantasy_lineup"))

    squad = FantasySquad.query.filter_by(
        user_id=current_user.id,
        season_id=season.id
    ).first()

    if squad is None:
        flash("Create your Fantasy squad first.", "warning")
        return redirect(url_for("fantasy"))

    try:
        raw_starters = request.form.getlist("starters")
        raw_captain = request.form.get("captain", "")

        starter_ids = [int(value) for value in raw_starters]
        captain_id = int(raw_captain)

        fantasy_validate_lineup(
            squad, starter_ids, captain_id
        )

        # Replace this round's lineup atomically.
        FantasyRoundLineup.query.filter_by(
            squad_id=squad.id,
            week_id=week.id
        ).delete(synchronize_session=False)

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

        db.session.commit()
        flash("Starting five and captain saved!", "success")

    except (ValueError, TypeError) as error:
        db.session.rollback()
        flash(str(error), "danger")

    except Exception:
        db.session.rollback()
        current_app.logger.exception("Failed to save Fantasy lineup")
        flash("Could not save the lineup.", "danger")

    return redirect(url_for("fantasy_lineup"))


@login_required
def fantasy_dashboard():

    from decimal import Decimal, ROUND_HALF_UP

    # --------------------------------------------------------
    # 1. FIND THE SEASON
    # --------------------------------------------------------

    season = (
        SimulationSeason.query
        .filter_by(status="active")
        .order_by(SimulationSeason.id.desc())
        .first()
    )

    if season is None:
        season = (
            SimulationSeason.query
            .filter_by(status="completed")
            .order_by(SimulationSeason.id.desc())
            .first()
        )

    if season is None:
        flash("No Fantasy season is available.", "warning")
        return redirect(url_for("fantasy"))

    # --------------------------------------------------------
    # 2. FIND THE USER'S FANTASY SQUAD
    # --------------------------------------------------------

    squad = FantasySquad.query.filter_by(
        user_id=current_user.id,
        season_id=season.id
    ).first()

    if squad is None or len(squad.players) != 10:
        flash(
            "Create your 10-player Fantasy squad first.",
            "warning"
        )
        return redirect(url_for("fantasy"))

    # --------------------------------------------------------
    # 3. LOAD OFFICIAL ROUND SCORES
    # --------------------------------------------------------

    score_records = (
        db.session.query(FantasyRoundScore, SimulationWeek)
        .join(
            SimulationWeek,
            FantasyRoundScore.week_id == SimulationWeek.id
        )
        .filter(
            FantasyRoundScore.squad_id == squad.id,
            SimulationWeek.season_id == season.id,
            SimulationWeek.status == "finalized"
        )
        .order_by(SimulationWeek.week_number)
        .all()
    )

    # Use integer hundredths until values are displayed.
    season_total_cents = sum(
        score.total_points
        for score, week in score_records
    )

    latest_round = (
        score_records[-1][1].week_number
        if score_records else None
    )

    latest_score_cents = (
        score_records[-1][0].total_points
        if score_records else 0
    )

    # --------------------------------------------------------
    # 4. BUILD ROUND HISTORY
    # --------------------------------------------------------

    round_history = []
    running_total_cents = 0

    for score, week in score_records:

        running_total_cents += score.total_points

        round_history.append({
            "round": week.week_number,
            "points": score.total_points / 100,
            "cumulative": running_total_cents / 100
        })

    # --------------------------------------------------------
    # 5. SELECT A FINALIZED ROUND
    # --------------------------------------------------------

    selected_round = request.args.get(
        "round",
        type=int
    )

    if selected_round is None:
        selected_round = latest_round

    selected_week = None
    selected_score = None

    if selected_round is not None:

        selected_week = SimulationWeek.query.filter_by(
            season_id=season.id,
            week_number=selected_round,
            status="finalized"
        ).first()

        if selected_week is None:
            abort(404)

        selected_score = FantasyRoundScore.query.filter_by(
            squad_id=squad.id,
            week_id=selected_week.id
        ).first()

        if selected_score is None:
            abort(404)

    # --------------------------------------------------------
    # 6. BUILD PLAYER PERFORMANCE BREAKDOWN
    # --------------------------------------------------------

    starters = []
    bench = []

    if selected_week is not None:

        lineup = FantasyRoundLineup.query.filter_by(
            squad_id=squad.id,
            week_id=selected_week.id
        ).all()

        # Get all performances from the selected round.
        performances = (
            db.session.query(SimulationPlayerStats)
            .join(
                SimulationGame,
                SimulationPlayerStats.game_id == SimulationGame.id
            )
            .filter(
                SimulationGame.week_id == selected_week.id,
                SimulationGame.status == "finalized"
            )
            .all()
        )

        points_by_player = {}

        for stat in performances:
            if stat.player_id in points_by_player:
                abort(
                    500,
                    description="Duplicate player performance in round."
                )

            points_by_player[stat.player_id] = Decimal(
                str(stat.fantasy_points)
            )

        position_order = {
            "PG": 0,
            "SG": 1,
            "SF": 2,
            "PF": 3,
            "C": 4
        }

        for entry in lineup:

            player = entry.player

            base_points = points_by_player.get(
                entry.player_id,
                Decimal("0")
            )

            if entry.is_captain:
                multiplier = Decimal("2")
                role = "Captain"

            elif entry.is_starter:
                multiplier = Decimal("1")
                role = "Starter"

            else:
                multiplier = Decimal("0.5")
                role = "Bench"

            contribution = base_points * multiplier

            player_data = {
                "id": player.id,
                "name": player.name,
                "position": player.position,
                "team": player.team.name,
                "picture_url": player.picture_url,
                "rating": player.rating or 70,
                "role": role,
                "is_captain": entry.is_captain,
                "base_points": float(base_points),
                "multiplier": float(multiplier),
                "contribution": float(contribution)
            }

            if entry.is_starter:
                starters.append(player_data)
            else:
                bench.append(player_data)

        starters.sort(
            key=lambda p: position_order.get(p["position"], 99)
        )

        bench.sort(
            key=lambda p: position_order.get(p["position"], 99)
        )

    # --------------------------------------------------------
    # 7. CHECK WHETHER THE CURRENT LINEUP IS EDITABLE
    # --------------------------------------------------------

    current_week = SimulationWeek.query.filter_by(
        season_id=season.id,
        week_number=season.current_week
    ).first()

    can_manage_lineup = (
        current_week is not None
        and season.status == "active"
        and current_week.status == "scheduled"
    )

    # --------------------------------------------------------
    # 8. RENDER DASHBOARD
    # --------------------------------------------------------

    return render_template(
        "fantasy_dashboard.html",
        season=season,
        squad=squad,
        season_total=season_total_cents / 100,
        latest_round=latest_round,
        latest_score=latest_score_cents / 100,
        round_history=round_history,
        selected_round=selected_round,
        selected_score=(
            selected_score.total_points / 100
            if selected_score is not None else None
        ),
        starters=starters,
        bench=bench,
        can_manage_lineup=can_manage_lineup,
        completed_rounds=len(round_history)
    )
