
import csv
from pathlib import Path

from app import app, db, Team

CSV_FILE = Path(__file__).resolve().parent / "teams.csv"


def import_teams():
    added = 0
    updated = 0
    skipped = 0

    with app.app_context():
        with open(CSV_FILE, "r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)

            for row in reader:
                name = (row.get("name") or "").strip()

                if not name:
                    skipped += 1
                    continue

                country = (row.get("country") or "").strip() or None
                record = (row.get("record") or "").strip() or None
                image_url = (row.get("image_url") or "").strip() or None

                team = Team.query.filter_by(name=name).first()

                if team is None:
                    team = Team(
                        name=name,
                        country=country,
                        record=record,
                        image_url=image_url,
                    )
                    db.session.add(team)
                    added += 1
                else:
                    team.country = country
                    team.record = record
                    team.image_url = image_url
                    updated += 1

        db.session.commit()

        print(f"Teams added: {added}")
        print(f"Teams updated: {updated}")
        print(f"Rows skipped: {skipped}")
        print(f"Total teams in database: {Team.query.count()}")


if __name__ == "__main__":
    import_teams()
