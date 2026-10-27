"""Database models: fantasy."""
from extensions import db
from datetime import datetime, timezone


class FantasySquad(db.Model):
    __tablename__ = "fantasy_squad"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    season_id = db.Column(
        db.Integer,
        db.ForeignKey("simulation_season.id"),
        nullable=False
    )

    name = db.Column(
        db.String(100),
        nullable=False,
        default="My Fantasy Team"
    )

    budget_remaining = db.Column(
        db.Integer,
        nullable=False,
        default=10000
    )

    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc)
    )

    user = db.relationship("User")
    season = db.relationship("SimulationSeason")

    players = db.relationship(
        "FantasySquadPlayer",
        backref="squad",
        lazy=True,
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        db.UniqueConstraint(
            "user_id",
            "season_id",
            name="uq_fantasy_user_season"
        ),
    )

class FantasySquadPlayer(db.Model):
    __tablename__ = "fantasy_squad_player"

    id = db.Column(db.Integer, primary_key=True)

    squad_id = db.Column(
        db.Integer,
        db.ForeignKey("fantasy_squad.id"),
        nullable=False
    )

    player_id = db.Column(
        db.Integer,
        db.ForeignKey("player.id"),
        nullable=False
    )

    # Price stored in hundredths of a million.
    # Example: 12.50M = 1250
    purchase_price = db.Column(
        db.Integer,
        nullable=False
    )

    player = db.relationship("Player")

    __table_args__ = (
        db.UniqueConstraint(
            "squad_id",
            "player_id",
            name="uq_fantasy_squad_player"
        ),
    )

class FantasyRoundLineup(db.Model):
    __tablename__ = "fantasy_round_lineup"

    id = db.Column(db.Integer, primary_key=True)

    squad_id = db.Column(
        db.Integer,
        db.ForeignKey("fantasy_squad.id"),
        nullable=False
    )

    week_id = db.Column(
        db.Integer,
        db.ForeignKey("simulation_week.id"),
        nullable=False
    )

    player_id = db.Column(
        db.Integer,
        db.ForeignKey("player.id"),
        nullable=False
    )

    is_starter = db.Column(
        db.Boolean,
        nullable=False,
        default=False
    )

    is_captain = db.Column(
        db.Boolean,
        nullable=False,
        default=False
    )

    squad = db.relationship("FantasySquad")
    week = db.relationship("SimulationWeek")
    player = db.relationship("Player")

    __table_args__ = (
        db.UniqueConstraint(
            "squad_id",
            "week_id",
            "player_id",
            name="uq_fantasy_lineup_player"
        ),
    )

class FantasyRoundScore(db.Model):
    __tablename__ = "fantasy_round_score"

    id = db.Column(db.Integer, primary_key=True)

    squad_id = db.Column(
        db.Integer,
        db.ForeignKey("fantasy_squad.id"),
        nullable=False
    )

    week_id = db.Column(
        db.Integer,
        db.ForeignKey("simulation_week.id"),
        nullable=False
    )

    # Store points as hundredths to avoid rounding errors.
    # Example: 12345 = 123.45 Fantasy points.
    total_points = db.Column(
        db.Integer,
        nullable=False,
        default=0
    )

    calculated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    squad = db.relationship(
        "FantasySquad",
        backref=db.backref(
            "round_scores",
            lazy=True,
            cascade="all, delete-orphan"
        )
    )

    week = db.relationship("SimulationWeek")

    __table_args__ = (
        db.UniqueConstraint(
            "squad_id",
            "week_id",
            name="uq_fantasy_squad_week_score"
        ),
    )
