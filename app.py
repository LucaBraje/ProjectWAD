from flask import Flask, render_template, jsonify, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    logout_user,
    login_required,
    current_user
)

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)
import os

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "development-only-change-me")
# SQLite database
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///draft_euroleague.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
# FLASK-LOGIN CONFIGURATION
login_manager = LoginManager()
login_manager.init_app(app)

login_manager.login_view = "login"
login_manager.login_message = "Please log in to access this page."
login_manager.login_message_category = "warning"

# TEAM DATABASE MODEL
class Team(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    country = db.Column(db.String(100))
    record = db.Column(db.String(20))
    image_url = db.Column(db.String(500))

    players = db.relationship("Player", backref="team", lazy=True)
    pictures = db.relationship("TeamPicture", backref="team", lazy=True)


# PLAYER DATABASE MODEL
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

    team_id = db.Column(
        db.Integer,
        db.ForeignKey("team.id"),
        nullable=False
    )


# TEAM PICTURES DATABASE MODEL
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


# USER DATABASE MODEL
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
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))



# HOMEPAGE
@app.route("/")
def home():
    return render_template("index.html")


# PLAYER DIRECTORY PAGE
@app.route("/players")
def player_directory():
    return render_template("players.html")


# TEAMS OVERVIEW PAGE
@app.route("/teams")
def team_directory():
    teams = Team.query.order_by(Team.name).all()
    return render_template("teams.html", teams=teams)


# INDIVIDUAL TEAM PROFILE PAGE
@app.route("/teams/<int:team_id>")
def team_profile(team_id):
    team = Team.query.get_or_404(team_id)

    players = Player.query.filter_by(
        team_id=team.id
    ).order_by(Player.rating.desc()).all()

    return render_template(
        "team_profile.html",
        team=team,
        players=players
    )

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
            "nationality": player.nationality,
            "picture_url": player.picture_url,
            "position": player.position,
            "rating": player.rating,
            "defense": player.defense,
            "offense": player.offense,
            "points_per_game": player.points_per_game,
            "assists_per_game": player.assists_per_game,
            "rebounds_per_game": player.rebounds_per_game,
            "blocks_per_game": player.blocks_per_game,
            "steals_per_game": player.steals_per_game,
            "fg_percentage": player.fg_percentage,
            "team": player.team.name,
            "team_image_url": player.team.image_url,
        }
        for player in players
    ])


# TEAMS API, INCLUDING LOGOS
@app.route("/api/teams")
def get_teams():
    teams = Team.query.order_by(Team.name).all()

    return jsonify([
        {
            "id": team.id,
            "name": team.name,
            "country": team.country,
            "record": team.record,
            "image_url": team.image_url,
        }
        for team in teams
    ])


# CREATE DATABASE TABLES
def initialize_database():
    with app.app_context():
        db.create_all()
        print("Database tables checked successfully!")
        print(f"Teams in database: {Team.query.count()}")
        print(f"Players in database: {Player.query.count()}")




# USER REGISTRATION
@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        # Check that all fields are filled in
        if not username or not email or not password or not confirm_password:
            flash("Please fill in all fields.", "danger")
            return redirect(url_for("register"))

        # Check field lengths
        if len(username) > 50 or len(email) > 120:
            flash("Username or email is too long.", "danger")
            return redirect(url_for("register"))

        # Check that passwords match
        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return redirect(url_for("register"))

        # Basic password length requirement
        if len(password) < 8:
            flash("Password must contain at least 8 characters.", "danger")
            return redirect(url_for("register"))

        # Check whether the username already exists
        existing_username = User.query.filter_by(
            username=username
        ).first()

        if existing_username:
            flash("This username is already taken.", "danger")
            return redirect(url_for("register"))

        # Check whether the email already exists
        existing_email = User.query.filter_by(
            email=email
        ).first()

        if existing_email:
            flash("An account with this email already exists.", "danger")
            return redirect(url_for("register"))

        # Create the account
        new_user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            role="user"
        )

        db.session.add(new_user)
        db.session.commit()

        flash("Account created successfully! You can now log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")




# USER LOGIN
@app.route("/login", methods=["GET", "POST"])
def login():

    # Already logged-in users don't need to log in again
    if current_user.is_authenticated:
        return redirect(url_for("home"))

    if request.method == "POST":

        username_or_email = request.form.get(
            "username_or_email", ""
        ).strip()

        password = request.form.get("password", "")

        # Find the user by username or email
        user = User.query.filter(
            (User.username == username_or_email) |
            (User.email == username_or_email.lower())
        ).first()

        # Verify credentials
        if user and check_password_hash(user.password_hash, password):

            login_user(user)

            flash(
                f"Welcome back, {user.username}!",
                "success"
            )

            return redirect(url_for("home"))

        flash("Invalid username/email or password.", "danger")

    return render_template("login.html")

# USER LOGOUT
@app.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()

    flash("You have been logged out.", "success")

    return redirect(url_for("home"))


initialize_database()


if __name__ == "__main__":
    app.run(debug=True)
