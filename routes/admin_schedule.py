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

# Dependencies supplied by app.py at registration time to avoid importing app.py
# as a second Flask application when running `python app.py`.
fantasy_lock_round_lineups = None
fantasy_calculate_round_scores = None
valid_admin_form_token = None
fantasy_delete_round_data = None


def configure(dependencies):
    global fantasy_lock_round_lineups, fantasy_calculate_round_scores, valid_admin_form_token, fantasy_delete_round_data
    fantasy_lock_round_lineups = dependencies["fantasy_lock_round_lineups"]
    fantasy_calculate_round_scores = dependencies["fantasy_calculate_round_scores"]
    valid_admin_form_token = dependencies["valid_admin_form_token"]
    fantasy_delete_round_data = dependencies["fantasy_delete_round_data"]

@admin_required
def admin_schedule():

    season = SimulationSeason.query.filter_by(
    status="active"
).first()

# If there is no active season, display the most recently
# completed season instead of an empty dashboard.
    if season is None:
        season = (
            SimulationSeason.query
            .filter_by(status="completed")
            .order_by(SimulationSeason.id.desc())
            .first()
        )

    if season is None:
        return render_template(
            "admin_schedule.html",
            season=None,
            week=None,
            games=[],
            completed_weeks=0,
            total_weeks=38
        )

    week = SimulationWeek.query.filter_by(
        season_id=season.id,
        week_number=season.current_week
    ).first()

    games = []

    if week is not None:
        games = (
            SimulationGame.query
            .filter_by(week_id=week.id)
            .order_by(SimulationGame.id)
            .all()
        )

    completed_weeks = SimulationWeek.query.filter_by(
        season_id=season.id,
        status="finalized"
    ).count()

    return render_template(
        "admin_schedule.html",
        season=season,
        week=week,
        games=games,
        completed_weeks=completed_weeks,
        total_weeks=38
    )


@admin_required
def admin_schedule_lock():

    # --------------------------------------------------------
    # 1. CSRF PROTECTION
    # --------------------------------------------------------

    if not valid_admin_form_token():
        abort(400, description="Invalid form security token.")

    # --------------------------------------------------------
    # 2. FIND ACTIVE SEASON
    # --------------------------------------------------------

    season = SimulationSeason.query.filter_by(
        status="active"
    ).first()

    if season is None:
        flash("No active season found.", "danger")
        return redirect(url_for("admin_schedule"))

    # --------------------------------------------------------
    # 3. FIND CURRENT ROUND
    # --------------------------------------------------------

    week = SimulationWeek.query.filter_by(
        season_id=season.id,
        week_number=season.current_week
    ).first()

    if week is None:
        flash("Current round was not found.", "danger")
        return redirect(url_for("admin_schedule"))

    # --------------------------------------------------------
    # 4. CHECK ROUND STATUS
    # --------------------------------------------------------

    if week.status != "scheduled":
        flash(
            "This round cannot be locked in its current state.",
            "warning"
        )
        return redirect(url_for("admin_schedule"))

    # --------------------------------------------------------
    # 5. VALIDATE NUMBER OF GAMES
    # --------------------------------------------------------

    games_count = SimulationGame.query.filter_by(
        week_id=week.id
    ).count()

    if games_count != 10:
        flash(
            "Cannot lock this round: expected exactly 10 games.",
            "danger"
        )
        return redirect(url_for("admin_schedule"))

    # --------------------------------------------------------
    # 6. LOCK FANTASY LINEUPS AND ROUND
    # --------------------------------------------------------

    try:

        # Automatically create missing Fantasy lineups.
        # Existing valid lineups are preserved.
        fantasy_lock_round_lineups(season, week)

        # Lock the current round.
        week.status = "locked"

        # Save everything in one database transaction.
        db.session.commit()

    # --------------------------------------------------------
    # 7. HANDLE VALIDATION ERRORS
    # --------------------------------------------------------

    except ValueError as error:

        db.session.rollback()

        flash(
            f"Cannot lock round: {error}",
            "danger"
        )

        return redirect(url_for("admin_schedule"))

    # --------------------------------------------------------
    # 8. HANDLE UNEXPECTED ERRORS
    # --------------------------------------------------------

    except Exception:

        db.session.rollback()

        current_app.logger.exception(
            "Failed to lock round and Fantasy lineups"
        )

        flash(
            "Could not lock the round. "
            "Check the Flask terminal for details.",
            "danger"
        )

        return redirect(url_for("admin_schedule"))

    # --------------------------------------------------------
    # 9. SUCCESS MESSAGE
    # --------------------------------------------------------

    flash(
        f"Round {week.week_number} has been locked successfully! "
        f"All Fantasy lineups are now locked.",
        "success"
    )

    return redirect(url_for("admin_schedule"))


@admin_required
def admin_schedule_simulate():

    if not valid_admin_form_token():
        abort(400, description="Invalid form security token.")

    season = SimulationSeason.query.filter_by(
        status="active"
    ).first()

    if season is None:
        flash("No active season found.", "danger")
        return redirect(url_for("admin_schedule"))

    week = SimulationWeek.query.filter_by(
        season_id=season.id,
        week_number=season.current_week
    ).first()

    if week is None:
        flash("Current round not found.", "danger")
        return redirect(url_for("admin_schedule"))

    if week.status != "locked":
        flash(
            "You must lock the round before simulating it.",
            "warning"
        )
        return redirect(url_for("admin_schedule"))

    games = (
        SimulationGame.query
        .filter_by(week_id=week.id)
        .order_by(SimulationGame.id)
        .all()
    )

    if len(games) != 10:
        flash(
            "Simulation cancelled: expected exactly 10 games.",
            "danger"
        )
        return redirect(url_for("admin_schedule"))

    if any(
        game.status != "scheduled"
        or game.home_score is not None
        or game.away_score is not None
        for game in games
    ):
        flash(
            "Simulation cancelled: some games already have results.",
            "danger"
        )
        return redirect(url_for("admin_schedule"))

    if SimulationPlayerStats.query.filter(
        SimulationPlayerStats.game_id.in_(
            [game.id for game in games]
        )
    ).first() is not None:
        flash(
            "Simulation cancelled: player statistics already exist.",
            "danger"
        )
        return redirect(url_for("admin_schedule"))

    # Load players for all participating teams.
    team_ids = set()

    for game in games:
        team_ids.add(game.home_team_id)
        team_ids.add(game.away_team_id)

    players = Player.query.filter(
        Player.team_id.in_(team_ids)
    ).all()

    players_by_team = {
        team_id: []
        for team_id in team_ids
    }

    for player in players:
        players_by_team[player.team_id].append(player)

    # Validate all rosters before saving anything.
    for team_id, roster in players_by_team.items():
        if len(roster) < 5:
            team = db.session.get(Team, team_id)

            flash(
                f"Cannot simulate: {team.name} has fewer "
                f"than 5 players.",
                "danger"
            )

            return redirect(url_for("admin_schedule"))

    try:
        # Generate all results first.
        # Nothing is saved until the entire round succeeds.
        generated_results = []

        for game in games:

            result = simulate_game(
                players_by_team[game.home_team_id],
                players_by_team[game.away_team_id],
                
            )

            generated_results.append((game, result))

        # Save the game results and player performances.
        for game, result in generated_results:

            game.home_score = result["home_score"]
            game.away_score = result["away_score"]
            game.status = "simulated"

            for team_id, key in (
                (game.home_team_id, "home_players"),
                (game.away_team_id, "away_players")
            ):

                for stats in result[key]:

                    player_result = SimulationPlayerStats(
                        game_id=game.id,
                        player_id=stats["player_id"],
                        team_id=team_id,
                        minutes=stats["minutes"],
                        points=stats["points"],
                        rebounds=stats["rebounds"],
                        assists=stats["assists"],
                        steals=stats["steals"],
                        blocks=stats["blocks"],
                        turnovers=stats["turnovers"],
                        field_goals_made=stats["field_goals_made"],
                        field_goals_attempted=stats["field_goals_attempted"],
                        fantasy_points=stats["fantasy_points"]
                    )

                    db.session.add(player_result)

        week.status = "simulated"

        db.session.commit()

    except Exception:
        db.session.rollback()
        current_app.logger.exception("Round simulation failed")

        flash(
            "Simulation failed. No results were saved. "
            "Check the Flask terminal for details.",
            "danger"
        )

        return redirect(url_for("admin_schedule"))

    flash(
        f"Round {week.week_number} simulated successfully! "
        f"All 10 games have results.",
        "success"
    )

    return redirect(url_for("admin_schedule"))


@admin_required
def admin_schedule_review():

    season = SimulationSeason.query.filter_by(
        status="active"
    ).first()

    if season is None:
        flash("No active season found.", "danger")
        return redirect(url_for("admin_schedule"))

    week = SimulationWeek.query.filter_by(
        season_id=season.id,
        week_number=season.current_week
    ).first()

    if week is None:
        flash("Current round not found.", "danger")
        return redirect(url_for("admin_schedule"))

    if week.status not in ("simulated", "finalized"):
        flash(
            "Simulate the current round before reviewing results.",
            "warning"
        )
        return redirect(url_for("admin_schedule"))

    games = (
        SimulationGame.query
        .filter_by(week_id=week.id)
        .order_by(SimulationGame.id)
        .all()
    )

    game_data = []

    for game in games:

        home_stats = (
            SimulationPlayerStats.query
            .filter_by(
                game_id=game.id,
                team_id=game.home_team_id
            )
            .all()
        )

        away_stats = (
            SimulationPlayerStats.query
            .filter_by(
                game_id=game.id,
                team_id=game.away_team_id
            )
            .all()
        )

        home_stats.sort(
            key=lambda stat: stat.points,
            reverse=True
        )

        away_stats.sort(
            key=lambda stat: stat.points,
            reverse=True
        )

        game_data.append({
            "game": game,
            "home_stats": home_stats,
            "away_stats": away_stats
        })

    return render_template(
        "admin_schedule_review.html",
        season=season,
        week=week,
        game_data=game_data
    )


@admin_required
def admin_schedule_edit_player(stat_id):

    if not valid_admin_form_token():
        abort(400, description="Invalid form security token.")

    stat = db.get_or_404(SimulationPlayerStats, stat_id)

    game = db.get_or_404(SimulationGame, stat.game_id)
    week = db.get_or_404(SimulationWeek, game.week_id)

    season = SimulationSeason.query.filter_by(
        status="active"
    ).first()

    if (
        season is None
        or week.season_id != season.id
        or week.week_number != season.current_week
    ):
        abort(403)

    if week.status != "simulated" or game.status != "simulated":
        flash(
            "Only simulated, unfinalized results can be edited.",
            "warning"
        )
        return redirect(url_for("admin_schedule_review"))

    fields = (
        "points",
        "rebounds",
        "assists",
        "steals",
        "blocks",
        "turnovers",
        "field_goals_made",
        "field_goals_attempted"
    )

    values = {}

    try:
        for field in fields:
            raw_value = request.form.get(field, "")

            if not raw_value.isdecimal():
                raise ValueError(
                    f"{field.replace('_', ' ').title()} "
                    "must be a nonnegative integer."
                )

            value = int(raw_value)

            if value > 200:
                raise ValueError(
                    f"{field.replace('_', ' ').title()} "
                    "cannot exceed 200."
                )

            values[field] = value

        if (
            values["field_goals_made"]
            > values["field_goals_attempted"]
        ):
            raise ValueError(
                "Made field goals cannot exceed attempted field goals."
            )

        # Our current simulator approximates scoring rather than
        # storing separate 2PT, 3PT and FT totals.
        #
        # Preserve the basic constraint that made field goals
        # cannot account for more points than the player scored.

        if values["field_goals_made"] * 2 > values["points"]:
            raise ValueError(
                "A player's points cannot be lower than twice "
                "their made field goals."
            )

        old_points = stat.points
        new_points = values["points"]

        point_difference = new_points - old_points

        if stat.team_id == game.home_team_id:
            new_team_score = game.home_score + point_difference

            if new_team_score < 0:
                raise ValueError("Team score cannot be negative.")

            game.home_score = new_team_score

        elif stat.team_id == game.away_team_id:
            new_team_score = game.away_score + point_difference

            if new_team_score < 0:
                raise ValueError("Team score cannot be negative.")

            game.away_score = new_team_score

        else:
            abort(400, description="Player team does not match game.")

        for field, value in values.items():
            setattr(stat, field, value)

        from services.basketball_simulator import (
            calculate_fantasy_points
        )

        stat.fantasy_points = calculate_fantasy_points(values)

        db.session.commit()

        flash(
            f"Updated {stat.player.name}'s performance successfully.",
            "success"
        )

    except ValueError as error:

        db.session.rollback()
        flash(str(error), "danger")

    except Exception:

        db.session.rollback()
        current_app.logger.exception("Failed to update player statistics")

        flash(
            "Could not save the changes. Check the Flask terminal.",
            "danger"
        )

    return redirect(
        url_for(
            "admin_schedule_review",
            _anchor=f"game-{game.id}"
        )
    )


@admin_required
def admin_schedule_finalize():

    # --------------------------------------------------------
    # 1. CSRF PROTECTION
    # --------------------------------------------------------

    if not valid_admin_form_token():
        abort(400, description="Invalid form security token.")

    # --------------------------------------------------------
    # 2. FIND ACTIVE SEASON
    # --------------------------------------------------------

    season = SimulationSeason.query.filter_by(
        status="active"
    ).first()

    if season is None:
        flash("No active season found.", "danger")
        return redirect(url_for("admin_schedule"))

    # --------------------------------------------------------
    # 3. FIND CURRENT ROUND
    # --------------------------------------------------------

    week = SimulationWeek.query.filter_by(
        season_id=season.id,
        week_number=season.current_week
    ).first()

    if week is None:
        flash("Current round not found.", "danger")
        return redirect(url_for("admin_schedule"))

    # Only simulated rounds can be finalized.
    if week.status != "simulated":

        flash(
            "Only a simulated round can be finalized.",
            "warning"
        )

        return redirect(url_for("admin_schedule"))

    # --------------------------------------------------------
    # 4. LOAD ALL GAMES
    # --------------------------------------------------------

    games = (
        SimulationGame.query
        .filter_by(week_id=week.id)
        .order_by(SimulationGame.id)
        .all()
    )

    if len(games) != 10:

        flash(
            "Finalization cancelled: expected exactly 10 games.",
            "danger"
        )

        return redirect(url_for("admin_schedule"))

    # --------------------------------------------------------
    # 5. VALIDATE ALL GAME RESULTS
    # --------------------------------------------------------

    # Import the same scoring function used by the simulator.
    from services.basketball_simulator import calculate_fantasy_points

    participating_teams = set()

    for game in games:

        # Check that the game was simulated.
        if game.status != "simulated":

            flash(
                "Finalization cancelled: not all games are simulated.",
                "danger"
            )

            return redirect(url_for("admin_schedule"))

        # Check that both scores exist.
        if game.home_score is None or game.away_score is None:

            flash(
                "Finalization cancelled: a game has missing scores.",
                "danger"
            )

            return redirect(url_for("admin_schedule"))

        # Scores must be nonnegative integers.
        if (
            type(game.home_score) is not int
            or type(game.away_score) is not int
            or game.home_score < 0
            or game.away_score < 0
        ):

            flash(
                "Finalization cancelled: invalid game score.",
                "danger"
            )

            return redirect(url_for("admin_schedule"))

        # Basketball games cannot finish in a draw.
        if game.home_score == game.away_score:

            flash(
                f"Finalization cancelled: "
                f"{game.home_team.name} vs {game.away_team.name} "
                f"is tied {game.home_score}-{game.away_score}. "
                f"Edit the results before finalizing.",
                "danger"
            )

            return redirect(url_for("admin_schedule"))

        # A team should play exactly once per round.
        if (
            game.home_team_id == game.away_team_id
            or game.home_team_id in participating_teams
            or game.away_team_id in participating_teams
        ):

            flash(
                "Finalization cancelled: duplicate team fixture.",
                "danger"
            )

            return redirect(url_for("admin_schedule"))

        participating_teams.add(game.home_team_id)
        participating_teams.add(game.away_team_id)

        # ----------------------------------------------------
        # 6. LOAD PLAYER STATISTICS
        # ----------------------------------------------------

        player_stats = SimulationPlayerStats.query.filter_by(
            game_id=game.id
        ).all()

        home_stats = []
        away_stats = []
        player_ids = set()

        for stat in player_stats:

            # Prevent duplicate player performances.
            if stat.player_id in player_ids:

                flash(
                    "Finalization cancelled: duplicate player statistics.",
                    "danger"
                )

                return redirect(url_for("admin_schedule"))

            player_ids.add(stat.player_id)

            # Player must belong to one of the competing teams.
            if stat.team_id == game.home_team_id:
                home_stats.append(stat)

            elif stat.team_id == game.away_team_id:
                away_stats.append(stat)

            else:

                flash(
                    "Finalization cancelled: player statistics "
                    "contain an invalid team.",
                    "danger"
                )

                return redirect(url_for("admin_schedule"))

        # Both teams must have valid player performances.
        if len(home_stats) < 5 or len(away_stats) < 5:

            flash(
                f"Finalization cancelled: missing player statistics "
                f"for {game.home_team.name} vs {game.away_team.name}.",
                "danger"
            )

            return redirect(url_for("admin_schedule"))

        # ----------------------------------------------------
        # 7. VALIDATE INDIVIDUAL PLAYER STATISTICS
        # ----------------------------------------------------

        for stat in player_stats:

            numeric_fields = (
                "points",
                "rebounds",
                "assists",
                "steals",
                "blocks",
                "turnovers",
                "field_goals_made",
                "field_goals_attempted"
            )

            values = {}

            for field in numeric_fields:

                value = getattr(stat, field)

                if type(value) is not int or value < 0:

                    flash(
                        f"Finalization cancelled: invalid {field} "
                        f"for {stat.player.name}.",
                        "danger"
                    )

                    return redirect(url_for("admin_schedule"))

                values[field] = value

            # Validate shooting statistics.
            if (
                stat.field_goals_made
                > stat.field_goals_attempted
            ):

                flash(
                    f"Finalization cancelled: invalid field goals "
                    f"for {stat.player.name}.",
                    "danger"
                )

                return redirect(url_for("admin_schedule"))

            if stat.field_goals_made * 2 > stat.points:

                flash(
                    f"Finalization cancelled: inconsistent points "
                    f"and field goals for {stat.player.name}.",
                    "danger"
                )

                return redirect(url_for("admin_schedule"))

            # Validate minutes.
            if (
                stat.minutes is None
                or not math.isfinite(stat.minutes)
                or stat.minutes < 0
            ):

                flash(
                    f"Finalization cancelled: invalid minutes "
                    f"for {stat.player.name}.",
                    "danger"
                )

                return redirect(url_for("admin_schedule"))

            # Recalculate fantasy points to ensure consistency.
            expected_fantasy_points = calculate_fantasy_points(
                values
            )

            if (
                stat.fantasy_points is None
                or not math.isfinite(stat.fantasy_points)
                or not math.isclose(
                    stat.fantasy_points,
                    expected_fantasy_points,
                    abs_tol=0.01
                )
            ):

                flash(
                    f"Finalization cancelled: incorrect fantasy "
                    f"points for {stat.player.name}.",
                    "danger"
                )

                return redirect(url_for("admin_schedule"))

        # ----------------------------------------------------
        # 8. CHECK PLAYER POINTS AGAINST TEAM SCORES
        # ----------------------------------------------------

        home_total = sum(
            stat.points for stat in home_stats
        )

        away_total = sum(
            stat.points for stat in away_stats
        )

        if home_total != game.home_score:

            flash(
                f"Finalization cancelled: "
                f"{game.home_team.name}'s player points "
                f"({home_total}) do not match "
                f"the game score ({game.home_score}).",
                "danger"
            )

            return redirect(url_for("admin_schedule"))

        if away_total != game.away_score:

            flash(
                f"Finalization cancelled: "
                f"{game.away_team.name}'s player points "
                f"({away_total}) do not match "
                f"the game score ({game.away_score}).",
                "danger"
            )

            return redirect(url_for("admin_schedule"))

       # --------------------------------------------------------
    # 9. FINALIZE RESULTS AND CALCULATE FANTASY SCORES
    # --------------------------------------------------------

    try:

        # ----------------------------------------------------
        # 9A. CALCULATE OFFICIAL FANTASY SCORES
        # ----------------------------------------------------

        # Uses the locked Fantasy lineups and approved
        # SimulationPlayerStats.fantasy_points values.
        #
        # This does not commit anything yet.

        scored_squads = fantasy_calculate_round_scores(
            season,
            week,
            games
        )

        # ----------------------------------------------------
        # 9B. FINALIZE ALL BASKETBALL GAMES
        # ----------------------------------------------------

        for game in games:
            game.status = "finalized"

        # ----------------------------------------------------
        # 9C. FINALIZE THE CURRENT ROUND
        # ----------------------------------------------------

        week.status = "finalized"

        # ----------------------------------------------------
        # 9D. COMMIT EVERYTHING TOGETHER
        # ----------------------------------------------------

        # Basketball results, round status, and Fantasy scores
        # are saved in a single database transaction.
        #
        # If anything fails, none of these changes are saved.

        db.session.commit()

    # --------------------------------------------------------
    # 10. HANDLE FANTASY VALIDATION ERRORS
    # --------------------------------------------------------

    except ValueError as error:

        db.session.rollback()

        flash(
            f"Finalization cancelled: {error}",
            "danger"
        )

        return redirect(url_for("admin_schedule"))

    # --------------------------------------------------------
    # 11. HANDLE UNEXPECTED ERRORS
    # --------------------------------------------------------

    except Exception:

        db.session.rollback()

        current_app.logger.exception(
            "Round finalization or Fantasy scoring failed"
        )

        flash(
            "Finalization failed. No results or Fantasy scores "
            "were finalized. Check the Flask terminal.",
            "danger"
        )

        return redirect(url_for("admin_schedule"))

    # --------------------------------------------------------
    # 12. SUCCESS MESSAGE
    # --------------------------------------------------------

    flash(
        f"Round {week.week_number} finalized successfully! "
        f"All 10 game results and player performances "
        f"are now approved. "
        f"Fantasy scores calculated for "
        f"{scored_squads} squad(s).",
        "success"
    )

    return redirect(url_for("admin_schedule"))


@admin_required
def admin_schedule_next():
    if not valid_admin_form_token():
        abort(400, description="Invalid form security token.")

    season = SimulationSeason.query.filter_by(status="active").first()
    if season is None:
        flash("No active season found.", "danger")
        return redirect(url_for("admin_schedule"))

    week = SimulationWeek.query.filter_by(
        season_id=season.id,
        week_number=season.current_week
    ).first()
    if week is None:
        flash("Current round not found.", "danger")
        return redirect(url_for("admin_schedule"))

    if week.status != "finalized":
        flash("You must finalize the current round before advancing.", "warning")
        return redirect(url_for("admin_schedule"))

    games = SimulationGame.query.filter_by(week_id=week.id).all()
    if len(games) != 10 or any(game.status != "finalized" for game in games):
        flash("Cannot advance: not all 10 games are finalized.", "danger")
        return redirect(url_for("admin_schedule"))

    # Finalized Fantasy squads must have an official score before advancing.
    # Incomplete squads are not eligible and do not need a score.
    eligible_squad_ids = [
        squad.id
        for squad in FantasySquad.query.filter_by(season_id=season.id).all()
        if len(squad.players) == 10
    ]
    if eligible_squad_ids:
        scored_squad_ids = {
            score.squad_id
            for score in FantasyRoundScore.query.filter(
                FantasyRoundScore.week_id == week.id,
                FantasyRoundScore.squad_id.in_(eligible_squad_ids)
            ).all()
        }
        if scored_squad_ids != set(eligible_squad_ids):
            flash(
                "Cannot advance: official Fantasy scores are missing "
                "for one or more complete squads.",
                "danger"
            )
            return redirect(url_for("admin_schedule"))

    total_weeks = SimulationWeek.query.filter_by(season_id=season.id).count()
    if total_weeks != 38:
        flash("Cannot advance: the season must contain 38 rounds.", "danger")
        return redirect(url_for("admin_schedule"))

    if season.current_week >= total_weeks:
        finalized_count = SimulationWeek.query.filter_by(
            season_id=season.id, status="finalized"
        ).count()
        if finalized_count != total_weeks:
            flash("Cannot complete season: some rounds are not finalized.", "danger")
            return redirect(url_for("admin_schedule"))
        try:
            # Preserve every Fantasy squad, lineup and score for season review.
            season.status = "completed"
            db.session.commit()
        except Exception:
            db.session.rollback()
            current_app.logger.exception("Season completion failed")
            flash("Could not complete the season.", "danger")
            return redirect(url_for("admin_schedule"))
        flash(
            f"Season {season.name} completed successfully! "
            "All 38 rounds and Fantasy results have been preserved.",
            "success"
        )
        return redirect(url_for("admin_schedule"))

    next_week_number = season.current_week + 1
    next_week = SimulationWeek.query.filter_by(
        season_id=season.id, week_number=next_week_number
    ).first()
    if next_week is None or next_week.status != "scheduled":
        flash(f"Cannot advance: Round {next_week_number} is not scheduled.", "danger")
        return redirect(url_for("admin_schedule"))

    next_games = SimulationGame.query.filter_by(week_id=next_week.id).all()
    if len(next_games) != 10 or any(
        game.status != "scheduled"
        or game.home_score is not None
        or game.away_score is not None
        for game in next_games
    ):
        flash(
            f"Cannot advance: Round {next_week_number} "
            "has invalid or incomplete fixtures.",
            "danger"
        )
        return redirect(url_for("admin_schedule"))

    # A future round should not contain results or frozen Fantasy data.
    if (
        FantasyRoundScore.query.filter_by(week_id=next_week.id).first()
        or FantasyRoundLineup.query.filter_by(week_id=next_week.id).first()
    ):
        flash("Cannot advance: the next round already has Fantasy data.", "danger")
        return redirect(url_for("admin_schedule"))

    try:
        # Users can now edit Round N+1 lineups. The lineup page's
        # fantasy_default_lineup() carries Round N's selection forward.
        season.current_week = next_week_number
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Advancing to next round failed")
        flash("Could not advance to the next round.", "danger")
        return redirect(url_for("admin_schedule"))

    flash(
        f"Round {week.week_number} completed! "
        f"Round {next_week_number} is now active. "
        "Fantasy lineups can be edited until the round locks.",
        "success"
    )
    return redirect(url_for("admin_schedule"))


@admin_required
def admin_schedule_reset_round():
    if not valid_admin_form_token():
        abort(400, description="Invalid form security token.")

    season = SimulationSeason.query.filter_by(status="active").first()
    if season is None:
        flash("No active season found.", "danger")
        return redirect(url_for("admin_schedule"))

    week = SimulationWeek.query.filter_by(
        season_id=season.id, week_number=season.current_week
    ).first()
    if week is None:
        flash("Current round not found.", "danger")
        return redirect(url_for("admin_schedule"))

    if week.status == "finalized":
        flash(
            "A finalized round cannot be reset individually. "
            "Use Reset Entire Season in development mode instead.",
            "warning"
        )
        return redirect(url_for("admin_schedule"))

    if week.status not in ("locked", "simulated"):
        flash("This round is already scheduled. Nothing to reset.", "warning")
        return redirect(url_for("admin_schedule"))

    if request.form.get("confirmation") != "RESET ROUND":
        flash("Reset cancelled: incorrect confirmation.", "danger")
        return redirect(url_for("admin_schedule"))

    try:
        games = SimulationGame.query.filter_by(week_id=week.id).all()
        game_ids = [game.id for game in games]

        # Clear Fantasy snapshots and any stale score for this round only.
        # Earlier finalized rounds and their Fantasy results remain untouched.
        fantasy_delete_round_data([week.id])

        if game_ids:
            SimulationPlayerStats.query.filter(
                SimulationPlayerStats.game_id.in_(game_ids)
            ).delete(synchronize_session=False)

        for game in games:
            game.home_score = None
            game.away_score = None
            game.status = "scheduled"

        week.status = "scheduled"
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Current round reset failed")
        flash("Could not reset the current round. Check the Flask terminal.", "danger")
        return redirect(url_for("admin_schedule"))

    flash(
        f"Round {week.week_number} reset successfully! "
        "Its Fantasy lineups and scores were cleared; "
        "earlier finalized rounds are unchanged.",
        "success"
    )
    return redirect(url_for("admin_schedule"))


@admin_required
def admin_schedule_reset_season():
    if not current_app.config.get("ALLOW_SEASON_RESET", False):
        abort(403, description="Season reset is disabled.")

    if not valid_admin_form_token():
        abort(400, description="Invalid form security token.")

    if request.form.get("confirmation") != "RESET SEASON":
        flash("Reset cancelled: incorrect confirmation.", "danger")
        return redirect(url_for("admin_schedule"))

    season = SimulationSeason.query.filter_by(status="active").first()
    if season is None:
        season = (
            SimulationSeason.query.filter_by(status="completed")
            .order_by(SimulationSeason.id.desc()).first()
        )
    if season is None:
        flash("No season found to reset.", "danger")
        return redirect(url_for("admin_schedule"))

    weeks = (
        SimulationWeek.query.filter_by(season_id=season.id)
        .order_by(SimulationWeek.week_number).all()
    )
    if len(weeks) != 38 or [w.week_number for w in weeks] != list(range(1, 39)):
        flash("Reset cancelled: expected a complete 38-round season.", "danger")
        return redirect(url_for("admin_schedule"))

    games = (
        SimulationGame.query.join(
            SimulationWeek, SimulationGame.week_id == SimulationWeek.id
        ).filter(SimulationWeek.season_id == season.id).all()
    )
    if len(games) != 380:
        flash("Reset cancelled: expected exactly 380 fixtures.", "danger")
        return redirect(url_for("admin_schedule"))

    try:
        # Full reset is destructive to results, but preserves user squads,
        # purchased players, original prices and remaining budgets.
        fantasy_delete_round_data([week.id for week in weeks])

        game_ids = [game.id for game in games]
        if game_ids:
            SimulationPlayerStats.query.filter(
                SimulationPlayerStats.game_id.in_(game_ids)
            ).delete(synchronize_session=False)

        for game in games:
            game.home_score = None
            game.away_score = None
            game.status = "scheduled"

        for week in weeks:
            week.status = "scheduled"

        season.current_week = 1
        season.status = "active"
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Entire season reset failed")
        flash("Season reset failed. No changes were saved. Check the Flask terminal.", "danger")
        return redirect(url_for("admin_schedule"))

    flash(
        f"{season.name} reset successfully! All 38 rounds are scheduled. "
        "Fantasy squads and budgets were preserved; "
        "old Fantasy lineups and scores were cleared.",
        "success"
    )
    return redirect(url_for("admin_schedule"))

