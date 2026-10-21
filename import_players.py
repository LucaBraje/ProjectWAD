import csv
from pathlib import Path

from app import app, db, Player, Team

CSV_FILE = Path(__file__).resolve().parent / "players.csv"

def import_players():
    added = 0
    skipped = 0
    missing_teams = set()

    with app.app_context():
        with open(
            CSV_FILE,
            "r",
            encoding="utf-8-sig",
            newline=""
        ) as file:
            reader = csv.DictReader(file)

            for row in reader:
                name = row["name"].strip()
                team_name = row["team"].strip()

                if not name or not team_name:
                    skipped += 1
                    continue

                # Find the team in the database
                team = Team.query.filter_by(
                    name=team_name
                ).first()

                if team is None:
                    missing_teams.add(team_name)
                    skipped += 1
                    continue

                # Avoid importing the same player twice
                existing = Player.query.filter_by(
                    name=name,
                    team_id=team.id
                ).first()

                if existing:
                    skipped += 1
                    continue

                
                
                
                player = Player(
                    name=name,
                    nationality=row.get("nationality", "").strip() or None,
                    position=row["position"].strip(),
                    rating=int(row.get("rating") or 70),
                    defense=int(row.get("defense") or 70),
                    offense=int(row.get("offense") or 70),
                    points_per_game=float(row.get("points_per_game") or 0),
                    assists_per_game=float(row.get("assists_per_game") or 0),
                    rebounds_per_game=float(row.get("rebounds_per_game") or 0),
                    blocks_per_game=float(row.get("blocks_per_game") or 0),
                    steals_per_game=float(row.get("steals_per_game") or 0),
                    fg_percentage=float(row.get("fg_percentage") or 0),
                    picture_url=row.get("picture_url", "").strip() or None,
                    team_id=team.id,
                )

                db.session.add(player)
                added += 1

        
        db.session.commit()

    print(f"Players added: {added}")
    print(f"Rows skipped: {skipped}")

    if missing_teams:
        print("Teams not found in database:")
        for team_name in sorted(missing_teams):
            print(f"- {team_name}")


if __name__ == "__main__":
    import_players()
