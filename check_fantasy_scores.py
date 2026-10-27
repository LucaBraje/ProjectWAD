from app import app, db, FantasyRoundScore, FantasySquad, SimulationWeek

with app.app_context():

    scores = FantasyRoundScore.query.all()

    print("\n========== FANTASY ROUND SCORES ==========\n")

    if not scores:
        print("No Fantasy scores found.")

    for score in scores:

        squad = db.session.get(
            FantasySquad,
            score.squad_id
        )

        week = db.session.get(
            SimulationWeek,
            score.week_id
        )

        print(f"Squad: {squad.name}")
        print(f"Round: {week.week_number}")
        print(f"Fantasy points: {score.total_points / 100:.2f}")
        print("----------------------------------------")

    print(f"\nTotal score records: {len(scores)}")