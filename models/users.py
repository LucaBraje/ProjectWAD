"""Database models: users."""
from extensions import db
from flask_login import UserMixin


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(
        db.String(50),
        unique=True,
        nullable=False
    )

    email = db.Column(
        db.String(120),
        unique=True,
        nullable=False
    )

    password_hash = db.Column(
        db.String(255),
        nullable=False
    )

    role = db.Column(
        db.String(20),
        nullable=False,
        default="user"
    )
    favorite_team_id = db.Column(
    db.Integer,
    db.ForeignKey("team.id"),
    nullable=True
)

    favorite_team = db.relationship(
        "Team",
        foreign_keys=[favorite_team_id]
    )
