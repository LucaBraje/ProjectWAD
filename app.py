
from flask import Flask, render_template, jsonify, request
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# SQLite database file
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///draft_euroleague.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


# TEAM DATABASE MODEL
class Team(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    country = db.Column(db.String(100))

    players = db.relationship("Player", backref="team", lazy=True)


# PLAYER DATABASE MODEL
class Player(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    position = db.Column(db.String(10), nullable=False)
    rating = db.Column(db.Integer, default=70)

    team_id = db.Column(
        db.Integer, db.ForeignKey("team.id"), nullable=False
    )


# HOMEPAGE
@app.route("/")
def home():
    return render_template("index.html")


# PLAYER DIRECTORY PAGE
@app.route("/players")
def player_directory():
    return render_template("players.html")


# DATABASE-POWERED PLAYER API
@app.route("/api/players")
def get_players():
    query = Player.query.join(Team)

    search = request.args.get("search", "").strip()
    team_name = request.args.get("team", "")
    position = request.args.get("position", "")

    if search:
        query = query.filter(Player.name.ilike(f"%{search}%"))

    if team_name:
        query = query.filter(Team.name == team_name)

    if position:
        query = query.filter(Player.position == position)

    players = query.order_by(Player.name).all()

    return jsonify([
        {
            "id": player.id,
            "name": player.name,
            "position": player.position,
            "rating": player.rating,
            "team": player.team.name
        }
        for player in players
    ])

@app.route("/api/teams")
def get_teams():
    teams = Team.query.order_by(Team.name).all()

    return jsonify([
        {
            "id": team.id,
            "name": team.name,
            "country": team.country
        }
        for team in teams
    ])


# CREATE DATABASE AND ADD SAMPLE DATA
def initialize_database():
    with app.app_context():
        db.create_all()

        # Add sample data only if the database has no teams
        if Team.query.first() is None:
            real_madrid = Team(
                name="Real Madrid",
                country="Spain"
            )
            monaco = Team(
                name="AS Monaco",
                country="Monaco"
            )
            efes = Team(
                name="Anadolu Efes",
                country="Türkiye"
            )

            db.session.add_all([real_madrid, monaco, efes])
            db.session.commit()

            sample_players = [
                Player(
                    name="Walter Tavares",
                    position="C",
                    rating=94,
                    team_id=real_madrid.id
                ),
                Player(
                    name="Facundo Campazzo",
                    position="PG",
                    rating=88,
                    team_id=real_madrid.id
                ),
                Player(
                    name="Mike James",
                    position="PG",
                    rating=92,
                    team_id=monaco.id
                ),
                Player(
                    name="Alpha Diallo",
                    position="SF",
                    rating=84,
                    team_id=monaco.id
                ),
                Player(
                    name="Shane Larkin",
                    position="PG",
                    rating=89,
                    team_id=efes.id
                ),
            ]

            db.session.add_all(sample_players)
            db.session.commit()


initialize_database()

if __name__ == "__main__":
    app.run(debug=True)
