
from app import app, db
from sqlalchemy import inspect, text

with app.app_context():
    columns = [
        column["name"]
        for column in inspect(db.engine).get_columns("draft_run")
    ]

    if "run_token" not in columns:
        with db.engine.begin() as connection:
            connection.execute(
                text(
                    "ALTER TABLE draft_run "
                    "ADD COLUMN run_token VARCHAR(36)"
                )
            )

            connection.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS "
                    "ix_draft_run_run_token "
                    "ON draft_run (run_token)"
                )
            )

        print("Successfully added run_token!")
    else:
        print("run_token already exists!")
