"""Run ONCE before starting the updated app. Back up the SQLite DB first."""
from sqlalchemy import inspect, text
from app import app, db

COLUMNS = [
    "games_played", "total_points", "total_assists", "total_rebounds",
    "total_blocks", "total_steals", "total_turnovers", "total_fgm",
    "total_fga"
]

with app.app_context():
    inspector = inspect(db.engine)
    if "player" not in inspector.get_table_names():
        raise RuntimeError("Player table does not exist. Check your database path.")
    existing = {c["name"] for c in inspector.get_columns("player")}
    with db.engine.begin() as connection:
        for column in COLUMNS:
            if column not in existing:
                connection.execute(text(f"ALTER TABLE player ADD COLUMN {column} INTEGER"))
                print("Added", column)
            else:
                print("Already exists:", column)
    print("Migration finished. Existing data preserved.")
