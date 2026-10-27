"""Database models: minigames."""
from extensions import db


class HigherLowerStats(db.Model):
    __tablename__ = "higher_lower_stats"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        unique=True,
        nullable=False
    )

    best_streak = db.Column(db.Integer, default=0)
    total_games = db.Column(db.Integer, default=0)
    total_correct = db.Column(db.Integer, default=0)
    total_guesses = db.Column(db.Integer, default=0)
    current_streak = db.Column(db.Integer, default=0)

    user = db.relationship(
        "User",
        backref=db.backref(
            "higher_lower_stats",
            uselist=False
        )
    )
