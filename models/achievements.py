"""Database models: achievements."""
from extensions import db
from datetime import datetime, timezone


class UserAchievement(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False,
        index=True
    )

    achievement_key = db.Column(
        db.String(100),
        nullable=False
    )

    unlocked_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    user = db.relationship(
        "User",
        backref=db.backref("achievements", lazy=True)
    )

    __table_args__ = (
        db.UniqueConstraint(
            "user_id",
            "achievement_key",
            name="unique_user_achievement"
        ),
    )

class UserTitle(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False,
        unique=True
    )

    # The title currently equipped by this user.
    title_key = db.Column(
        db.String(100),
        nullable=False
    )

    user = db.relationship(
        "User",
        backref=db.backref(
            "equipped_title",
            uselist=False
        )
    )
