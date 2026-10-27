"""Database models: draft."""
from extensions import db
from datetime import datetime, timezone


class DraftRun(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    run_token = db.Column(
    db.String(36),
    unique=True,
    nullable=False
)


    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False,
        index=True
    )

    club_id = db.Column(
        db.Integer,
        db.ForeignKey("team.id"),
        nullable=False
    )

    team_score = db.Column(db.Float, nullable=False)
    base_score = db.Column(db.Float, nullable=False)

    out_of_position = db.Column(db.Integer, nullable=False)

    wins = db.Column(db.Integer, nullable=False)
    losses = db.Column(db.Integer, nullable=False)
    seed = db.Column(db.Integer, nullable=False)

    outcome = db.Column(db.String(50), nullable=False)

    # Example: {"PG": 12, "SG": 25, ...}
    lineup = db.Column(db.JSON, nullable=False)

    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    user = db.relationship(
        "User",
        backref=db.backref("draft_runs", lazy=True)
    )

    club = db.relationship("Team")
