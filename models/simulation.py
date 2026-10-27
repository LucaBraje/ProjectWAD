"""Database models: simulation."""
from extensions import db
from datetime import datetime, timezone


class SimulationSeason(db.Model):
    __tablename__ = "simulation_season"

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(100), nullable=False)

    status = db.Column(
        db.String(20),
        nullable=False,
        default="active"
    )

    current_week = db.Column(
        db.Integer,
        nullable=False,
        default=1
    )

    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc)
    )

    weeks = db.relationship(
        "SimulationWeek",
        backref="season",
        lazy=True,
        cascade="all, delete-orphan"
    )

class SimulationWeek(db.Model):
    __tablename__ = "simulation_week"

    id = db.Column(db.Integer, primary_key=True)

    season_id = db.Column(
        db.Integer,
        db.ForeignKey("simulation_season.id"),
        nullable=False
    )

    week_number = db.Column(db.Integer, nullable=False)

    status = db.Column(
        db.String(20),
        nullable=False,
        default="scheduled"
    )

    games = db.relationship(
        "SimulationGame",
        backref="week",
        lazy=True,
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        db.UniqueConstraint(
            "season_id",
            "week_number",
            name="uq_simulation_season_week"
        ),
    )

class SimulationGame(db.Model):
    __tablename__ = "simulation_game"

    id = db.Column(db.Integer, primary_key=True)

    week_id = db.Column(
        db.Integer,
        db.ForeignKey("simulation_week.id"),
        nullable=False
    )

    home_team_id = db.Column(
        db.Integer,
        db.ForeignKey("team.id"),
        nullable=False
    )

    away_team_id = db.Column(
        db.Integer,
        db.ForeignKey("team.id"),
        nullable=False
    )

    home_score = db.Column(db.Integer, nullable=True)
    away_score = db.Column(db.Integer, nullable=True)

    status = db.Column(
        db.String(20),
        nullable=False,
        default="scheduled"
    )

    home_team = db.relationship(
        "Team",
        foreign_keys=[home_team_id]
    )

    away_team = db.relationship(
        "Team",
        foreign_keys=[away_team_id]
    )

    __table_args__ = (
        db.CheckConstraint(
            "home_team_id != away_team_id",
            name="ck_simulation_different_teams"
        ),
        db.UniqueConstraint(
            "week_id",
            "home_team_id",
            name="uq_simulation_week_home"
        ),
        db.UniqueConstraint(
            "week_id",
            "away_team_id",
            name="uq_simulation_week_away"
        ),
    )

class SimulationPlayerStats(db.Model):
    __tablename__ = "simulation_player_stats"

    id = db.Column(db.Integer, primary_key=True)

    game_id = db.Column(
        db.Integer,
        db.ForeignKey("simulation_game.id"),
        nullable=False
    )

    player_id = db.Column(
        db.Integer,
        db.ForeignKey("player.id"),
        nullable=False
    )

    team_id = db.Column(
        db.Integer,
        db.ForeignKey("team.id"),
        nullable=False
    )

    minutes = db.Column(db.Float, nullable=False, default=0)

    points = db.Column(db.Integer, nullable=False, default=0)
    rebounds = db.Column(db.Integer, nullable=False, default=0)
    assists = db.Column(db.Integer, nullable=False, default=0)
    steals = db.Column(db.Integer, nullable=False, default=0)
    blocks = db.Column(db.Integer, nullable=False, default=0)
    turnovers = db.Column(db.Integer, nullable=False, default=0)

    field_goals_made = db.Column(
        db.Integer, nullable=False, default=0
    )

    field_goals_attempted = db.Column(
        db.Integer, nullable=False, default=0
    )

    fantasy_points = db.Column(
        db.Float, nullable=False, default=0
    )

    player = db.relationship("Player")
    team = db.relationship("Team")
    game = db.relationship(
        "SimulationGame",
        backref=db.backref("player_stats", lazy=True)
    )

    __table_args__ = (
        db.UniqueConstraint(
            "game_id",
            "player_id",
            name="uq_simulation_game_player"
        ),
    )
