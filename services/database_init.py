"""Database table creation and the existing player-stat refresh."""
from extensions import db
from models import Player, Team


def initialize_database(app):
    with app.app_context():
        db.create_all()
        from update_player_stats import update_all_player_stats
        update_all_player_stats(db, Player)
        print("Database tables checked successfully!")
        print(f"Teams in database: {Team.query.count()}")
        print(f"Players in database: {Player.query.count()}")
