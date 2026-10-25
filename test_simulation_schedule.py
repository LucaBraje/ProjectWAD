from collections import Counter

from app import (
    app,
    SimulationSeason,
    SimulationWeek,
    SimulationGame
)


with app.app_context():

    season = SimulationSeason.query.filter_by(
        status="active"
    ).first()

    if not season:
        print("No active season found.")
        raise SystemExit(1)

    weeks = SimulationWeek.query.filter_by(
        season_id=season.id
    ).all()

    games = (
        SimulationGame.query
        .join(SimulationWeek)
        .filter(SimulationWeek.season_id == season.id)
        .all()
    )

    print("Total weeks:", len(weeks))
    print("Total games:", len(games))

    assert len(weeks) == 38
    assert len(games) == 380

    home_games = Counter()
    away_games = Counter()
    matchups = Counter()

    for game in games:

        home_games[game.home_team_id] += 1
        away_games[game.away_team_id] += 1

        matchups[
            (game.home_team_id, game.away_team_id)
        ] += 1

    team_ids = set(home_games) | set(away_games)

    assert len(team_ids) == 20

    for team_id in team_ids:
        assert home_games[team_id] == 19
        assert away_games[team_id] == 19

    for home_id in team_ids:
        for away_id in team_ids:

            if home_id != away_id:
                assert matchups[(home_id, away_id)] == 1

    for week in weeks:

        teams_this_week = []

        for game in week.games:
            teams_this_week.append(game.home_team_id)
            teams_this_week.append(game.away_team_id)

        assert len(week.games) == 10
        assert len(set(teams_this_week)) == 20

    print("All schedule checks passed!")

    first_week = SimulationWeek.query.filter_by(
        season_id=season.id,
        week_number=1
    ).first()

    print("\nWEEK 1 FIXTURES")
    print("--------------------")

    for game in first_week.games:
        print(
            f"{game.home_team.name} "
            f"vs {game.away_team.name}"
        )