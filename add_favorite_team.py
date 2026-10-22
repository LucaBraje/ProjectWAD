from app import app, db
from sqlalchemy import inspect, text

with app.app_context():
    columns = [
        column["name"]
        for column in inspect(db.engine).get_columns("user")
    ]

    if "favorite_team_id" not in columns:
        with db.engine.begin() as connection:
            connection.execute(
                text(
                    "ALTER TABLE user "
                    "ADD COLUMN favorite_team_id INTEGER "
                    "REFERENCES team(id)"
                )
            )

        print("Favorite team column added!")
    else:
        print("Favorite team column already exists.")