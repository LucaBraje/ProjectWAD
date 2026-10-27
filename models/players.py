"""Database models: players."""
from extensions import db


class Player(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    picture_url = db.Column(db.String(200))
    name = db.Column(db.String(100), nullable=False)
    nationality = db.Column(db.String(50))
    position = db.Column(db.String(10), nullable=False)
    rating = db.Column(db.Integer, default=70)
    defense = db.Column(db.Integer, default=70)
    offense = db.Column(db.Integer, default=70)
    points_per_game = db.Column(db.Float, default=0.0)
    assists_per_game = db.Column(db.Float, default=0.0)
    rebounds_per_game = db.Column(db.Float, default=0.0)
    blocks_per_game = db.Column(db.Float, default=0.0)
    steals_per_game = db.Column(db.Float, default=0.0)
    fg_percentage = db.Column(db.Float, default=0.0)

    # Official EuroLeague season totals (populated by a separate sync script).
    # NULL means not yet imported; existing averages are preserved until then.
    games_played = db.Column(db.Integer, nullable=True)
    total_points = db.Column(db.Integer, nullable=True)
    total_assists = db.Column(db.Integer, nullable=True)
    total_rebounds = db.Column(db.Integer, nullable=True)
    total_blocks = db.Column(db.Integer, nullable=True)
    total_steals = db.Column(db.Integer, nullable=True)
    total_turnovers = db.Column(db.Integer, nullable=True)
    total_fgm = db.Column(db.Integer, nullable=True)
    total_fga = db.Column(db.Integer, nullable=True)


    team_id = db.Column(
        db.Integer,
        db.ForeignKey("team.id"),
        nullable=False
    )

class Legend(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(100), unique=True, nullable=False)
    nationality = db.Column(db.String(50))
    position = db.Column(db.String(10), nullable=False)

    rating = db.Column(db.Integer, default=90)
    offense = db.Column(db.Integer, default=90)
    defense = db.Column(db.Integer, default=90)

    points_per_game = db.Column(db.Float, default=0.0)
    assists_per_game = db.Column(db.Float, default=0.0)
    rebounds_per_game = db.Column(db.Float, default=0.0)
    blocks_per_game = db.Column(db.Float, default=0.0)
    steals_per_game = db.Column(db.Float, default=0.0)
    fg_percentage = db.Column(db.Float, default=0.0)

    picture_url = db.Column(db.String(500))
    peak_season = db.Column(db.String(20))
    legendary_team = db.Column(db.String(100))
