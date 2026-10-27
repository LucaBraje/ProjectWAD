"""Database models: teams."""
from extensions import db


class Team(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    country = db.Column(db.String(100))
    record = db.Column(db.String(20))
    image_url = db.Column(db.String(500))
    biography = db.Column(db.Text, nullable=True)

    players = db.relationship("Player", backref="team", lazy=True)
    pictures = db.relationship("TeamPicture", backref="team", lazy=True)

class TeamPicture(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    picture_url = db.Column(db.String(200), nullable=False)
    description = db.Column(db.String(100))
    is_primary = db.Column(db.Boolean, default=False)

    team_id = db.Column(
        db.Integer,
        db.ForeignKey("team.id"),
        nullable=False
    )
