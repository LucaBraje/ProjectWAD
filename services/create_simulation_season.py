from app import (
    app,
    db,
    Team,
    SimulationSeason,
    SimulationWeek,
    SimulationGame
)

from services.fixture_generator import generate_round_robin


def create_season():

    with app.app_context():

        # Make sure the new tables exist
        db.create_all()

        # Prevent creating another active season
        existing_season = SimulationSeason.query.filter_by(
            status="active"
        ).first()

        if existing_season:
            print(
                f"An active season already exists: "
                f"{existing_season.name}"
            )
            return

        teams = Team.query.order_by(Team.id).all()

        if len(teams) != 20:
            print(
                f"Expected 20 teams, found {len(teams)}."
            )
            return

        team_ids = [team.id for team in teams]

        # Generate 38 weeks of fixtures
        schedule = generate_round_robin(
            team_ids,
            seed=2026
        )

        season = SimulationSeason(
            name="Draft EuroLeague Season 1",
            status="active",
            current_week=1
        )

        try:
            db.session.add(season)
            db.session.flush()

            for week_number, matches in enumerate(
                schedule,
                start=1
            ):

                week = SimulationWeek(
                    season_id=season.id,
                    week_number=week_number,
                    status="scheduled"
                )

                db.session.add(week)
                db.session.flush()

                for home_id, away_id in matches:

                    game = SimulationGame(
                        week_id=week.id,
                        home_team_id=home_id,
                        away_team_id=away_id,
                        status="scheduled"
                    )

                    db.session.add(game)

            db.session.commit()

        except Exception:
            db.session.rollback()
            raise

        print("Season created successfully!")
        print(f"Season: {season.name}")
        print(f"Teams: {len(teams)}")
        print(f"Weeks: {len(schedule)}")
        print(
            f"Games: {sum(len(week) for week in schedule)}"
        )


if __name__ == "__main__":
    create_season()