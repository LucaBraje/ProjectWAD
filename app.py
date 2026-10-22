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
from functools import wraps
from flask import abort
from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)
import os
import math
from datetime import datetime, timezone
from sqlalchemy import func
import random
from uuid import uuid4

from flask import request, jsonify
from sqlalchemy.exc import IntegrityError

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
    biography = db.Column(db.Text, nullable=True)

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
    favorite_team_id = db.Column(
    db.Integer,
    db.ForeignKey("team.id"),
    nullable=True
)

    favorite_team = db.relationship(
        "Team",
        foreign_keys=[favorite_team_id]
    )
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))



# =====================================================
# DRAFT MODE - SAVED RESULTS
# =====================================================

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


# =====================================================
# USER ACHIEVEMENTS AND TITLES
# =====================================================

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


DRAFT_ACHIEVEMENTS = {
    "first_draft": {
        "name": "Rookie GM",
        "description": "Complete your first Draft Mode simulation.",
        "title": "Rookie GM"
    },
    "first_playoffs": {
        "name": "Playoff Contender",
        "description": "Qualify for the EuroLeague playoffs.",
        "title": "Playoff Contender"
    },
    "first_final_four": {
        "name": "Final Four Veteran",
        "description": "Reach the EuroLeague Final Four.",
        "title": "Final Four Veteran"
    },
    "first_championship": {
        "name": "EuroLeague Champion",
        "description": "Win your first EuroLeague championship.",
        "title": "EuroLeague Champion"
    },
    "five_championships": {
        "name": "Dynasty Builder",
        "description": "Win five EuroLeague championships.",
        "title": "Dynasty Builder"
    },
    "elite_draft": {
        "name": "Draft Master",
        "description": "Build a team worth at least 180 points.",
        "title": "Draft Master"
    },
    "perfect_positions": {
        "name": "Perfect Architect",
        "description": "Draft five players in their natural positions.",
        "title": "Perfect Architect"
    },
    "draft_veteran": {
        "name": "Draft Veteran",
        "description": "Complete 50 drafts.",
        "title": "Draft Veteran"
    }
}

# =====================================================
# DRAFT ACHIEVEMENT UNLOCKING
# =====================================================

def unlock_draft_achievements(user_id, draft_run):
    """
    Check which achievements the user has earned.

    Call this only after a completed DraftRun
    has been added to the database session.
    """

    unlocked = []

    total_drafts = DraftRun.query.filter_by(
        user_id=user_id
    ).count()

    championships = DraftRun.query.filter_by(
        user_id=user_id,
        outcome="EUROLEAGUE CHAMPIONS"
    ).count()

    playoff_outcomes = {
        "PLAYOFF ELIMINATION",
        "FINAL FOUR",
        "EUROLEAGUE FINALIST",
        "EUROLEAGUE CHAMPIONS"
    }

    final_four_outcomes = {
        "FINAL FOUR",
        "EUROLEAGUE FINALIST",
        "EUROLEAGUE CHAMPIONS"
    }

    eligible = set()

    if total_drafts >= 1:
        eligible.add("first_draft")

    if draft_run.outcome in playoff_outcomes:
        eligible.add("first_playoffs")

    if draft_run.outcome in final_four_outcomes:
        eligible.add("first_final_four")

    if championships >= 1:
        eligible.add("first_championship")

    if championships >= 5:
        eligible.add("five_championships")

    if draft_run.team_score >= 180:
        eligible.add("elite_draft")

    if draft_run.out_of_position == 0:
        eligible.add("perfect_positions")

    if total_drafts >= 50:
        eligible.add("draft_veteran")

    for achievement_key in eligible:

        existing = UserAchievement.query.filter_by(
            user_id=user_id,
            achievement_key=achievement_key
        ).first()

        if existing:
            continue

        achievement = UserAchievement(
            user_id=user_id,
            achievement_key=achievement_key
        )

        db.session.add(achievement)

        unlocked.append({
            "key": achievement_key,
            "name": DRAFT_ACHIEVEMENTS[achievement_key]["name"],
            "title": DRAFT_ACHIEVEMENTS[achievement_key]["title"]
        })

    return unlocked


# ADMIN ACCESS DECORATOR
def admin_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):

        if current_user.role != "admin":
            abort(403)

        return f(*args, **kwargs)

    return decorated_function

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


# ADMIN DASHBOARD
@app.route("/admin")
@admin_required
def admin_dashboard():
    return render_template("admin.html")


# ADMIN - PLAYER MANAGEMENT
@app.route("/admin/players")
@admin_required
def admin_players():
    players = Player.query.order_by(Player.name).all()

    return render_template(
        "admin_players.html",
        players=players
    )


# ADMIN - ADD PLAYER
@app.route("/admin/players/add", methods=["GET", "POST"])
@admin_required
def admin_add_player():
    teams = Team.query.order_by(Team.name).all()

    if request.method == "POST":

        # BASIC PLAYER INFORMATION
        name = request.form.get("name", "").strip()
        nationality = request.form.get("nationality", "").strip()
        position = request.form.get("position", "").strip()
        picture_url = request.form.get("picture_url", "").strip()

        try:
            # TEAM
            team_id = int(request.form.get("team_id", ""))

            # PLAYER RATINGS
            rating = int(request.form.get("rating", "70"))
            offense = int(request.form.get("offense", "70"))
            defense = int(request.form.get("defense", "70"))

            # PLAYER STATISTICS
            points_per_game = float(request.form.get("points_per_game", "0"))
            assists_per_game = float(request.form.get("assists_per_game", "0"))
            rebounds_per_game = float(request.form.get("rebounds_per_game", "0"))
            blocks_per_game = float(request.form.get("blocks_per_game", "0"))
            steals_per_game = float(request.form.get("steals_per_game", "0"))
            fg_percentage = float(request.form.get("fg_percentage", "0"))

            # VALIDATE BASIC INFORMATION
            if not name or not position:
                raise ValueError("Name and position are required.")

            if len(name) > 100 or len(nationality) > 50 or len(position) > 10:
                raise ValueError("One or more text fields are too long.")

            if position not in ["PG", "SG", "SF", "PF", "C"]:
                raise ValueError("Invalid player position.")

            if len(picture_url) > 200:
                raise ValueError("Picture URL must be 200 characters or fewer.")

            # VALIDATE RATINGS
            if not all(math.isfinite(value) and 0 <= value <= 100 for value in stats):
                raise ValueError("Ratings must be between 0 and 100.")

            # VALIDATE STATISTICS
            stats = [
                points_per_game,
                assists_per_game,
                rebounds_per_game,
                blocks_per_game,
                steals_per_game
            ]

            if not all(math.isfinite(value) and 0 <= value <= 100 for value in stats):
                raise ValueError("Statistics must be between 0 and 100.")

            if not 0 <= fg_percentage <= 100:
                raise ValueError("FG% must be between 0 and 100.")

            # VALIDATE TEAM
            team = db.session.get(Team, team_id)

            if team is None:
                raise ValueError("Please select a valid team.")

        except (ValueError, TypeError) as error:
            flash(f"Invalid player information: {error}", "danger")
            return redirect(url_for("admin_add_player"))

        # CREATE NEW PLAYER
        player = Player(
            name=name,
            nationality=nationality,
            position=position,
            picture_url=picture_url,
            rating=rating,
            offense=offense,
            defense=defense,
            points_per_game=points_per_game,
            assists_per_game=assists_per_game,
            rebounds_per_game=rebounds_per_game,
            blocks_per_game=blocks_per_game,
            steals_per_game=steals_per_game,
            fg_percentage=fg_percentage,
            team_id=team_id
        )

        # SAVE TO DATABASE
        db.session.add(player)
        db.session.commit()

        flash("Player added successfully!", "success")
        return redirect(url_for("admin_players"))

    return render_template(
        "admin_player_form.html",
        player=None,
        teams=teams
    )


# ADMIN - EDIT PLAYER
@app.route("/admin/players/<int:player_id>/edit", methods=["GET", "POST"])
@admin_required
def admin_edit_player(player_id):

    player = db.get_or_404(Player, player_id)
    teams = Team.query.order_by(Team.name).all()

    if request.method == "POST":

        # BASIC PLAYER INFORMATION
        name = request.form.get("name", "").strip()
        nationality = request.form.get("nationality", "").strip()
        position = request.form.get("position", "").strip()
        picture_url = request.form.get("picture_url", "").strip()

        try:
            # TEAM
            team_id = int(request.form.get("team_id", ""))

            # PLAYER RATINGS
            rating = int(request.form.get("rating", "70"))
            offense = int(request.form.get("offense", "70"))
            defense = int(request.form.get("defense", "70"))

            # PLAYER STATISTICS
            points_per_game = float(request.form.get("points_per_game", "0"))
            assists_per_game = float(request.form.get("assists_per_game", "0"))
            rebounds_per_game = float(request.form.get("rebounds_per_game", "0"))
            blocks_per_game = float(request.form.get("blocks_per_game", "0"))
            steals_per_game = float(request.form.get("steals_per_game", "0"))
            fg_percentage = float(request.form.get("fg_percentage", "0"))

            # VALIDATE BASIC INFORMATION
            if not name or not position:
                raise ValueError("Name and position are required.")

            if len(name) > 100 or len(nationality) > 50 or len(position) > 10:
                raise ValueError("One or more text fields are too long.")

            if position not in ["PG", "SG", "SF", "PF", "C"]:
                raise ValueError("Invalid player position.")

            if len(picture_url) > 200:
                raise ValueError("Picture URL must be 200 characters or fewer.")

            # VALIDATE RATINGS
            if not all(0 <= value <= 100 for value in (rating, offense, defense)):
                raise ValueError("Ratings must be between 0 and 100.")

            # VALIDATE STATISTICS
            stats = [
                points_per_game,
                assists_per_game,
                rebounds_per_game,
                blocks_per_game,
                steals_per_game
            ]

            if not all(0 <= value <= 100 for value in stats):
                raise ValueError("Statistics must be between 0 and 100.")

            if not 0 <= fg_percentage <= 100:
                raise ValueError("FG% must be between 0 and 100.")

            # VALIDATE TEAM
            team = db.session.get(Team, team_id)

            if team is None:
                raise ValueError("Please select a valid team.")

        except (ValueError, TypeError) as error:
            flash(f"Invalid player information: {error}", "danger")
            return redirect(
                url_for("admin_edit_player", player_id=player.id)
            )

        # UPDATE BASIC INFORMATION
        player.name = name
        player.nationality = nationality
        player.position = position
        player.picture_url = picture_url

        # UPDATE RATINGS
        player.rating = rating
        player.offense = offense
        player.defense = defense

        # UPDATE STATISTICS
        player.points_per_game = points_per_game
        player.assists_per_game = assists_per_game
        player.rebounds_per_game = rebounds_per_game
        player.blocks_per_game = blocks_per_game
        player.steals_per_game = steals_per_game
        player.fg_percentage = fg_percentage

        # UPDATE TEAM (TRANSFER PLAYER)
        player.team_id = team_id

        # SAVE CHANGES
        db.session.commit()

        flash("Player updated successfully!", "success")
        return redirect(url_for("admin_players"))

    return render_template(
        "admin_player_form.html",
        player=player,
        teams=teams
    )


# ADMIN - DELETE PLAYER
@app.route("/admin/players/<int:player_id>/delete", methods=["POST"])
@admin_required
def admin_delete_player(player_id):
    player = db.get_or_404(Player, player_id)

    player_name = player.name

    db.session.delete(player)
    db.session.commit()

    flash(f"{player_name} was deleted.", "success")
    return redirect(url_for("admin_players"))




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

# USER PROFILE
@app.route("/profile")
@login_required
def profile():
    return render_template("profile.html")

# ADMIN - TEAM MANAGEMENT
@app.route("/admin/teams")
@admin_required
def admin_teams():
    teams = Team.query.order_by(Team.name).all()

    return render_template(
        "admin_teams.html",
        teams=teams
    )
# ADMIN - ADD TEAM
@app.route("/admin/teams/add", methods=["GET", "POST"])
@admin_required
def admin_add_team():

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        country = request.form.get("country", "").strip()
        record = request.form.get("record", "").strip()
        image_url = request.form.get("image_url", "").strip()
        biography = request.form.get("biography", "").strip()

        if not name:
            flash("Team name is required.", "danger")
            return redirect(url_for("admin_add_team"))

        if len(name) > 100 or len(country) > 100:
            flash("Team name or country is too long.", "danger")
            return redirect(url_for("admin_add_team"))

        if len(record) > 20 or len(image_url) > 500:
            flash("Record or logo path is too long.", "danger")
            return redirect(url_for("admin_add_team"))

        existing_team = Team.query.filter_by(name=name).first()

        if existing_team:
            flash("A team with this name already exists.", "danger")
            return redirect(url_for("admin_add_team"))

        team = Team(
            name=name,
            country=country,
            record=record,
            image_url=image_url,
            biography=biography
        )

        db.session.add(team)
        db.session.commit()

        flash("Team added successfully!", "success")
        return redirect(url_for("admin_teams"))

    return render_template("admin_team_form.html", team=None)
# ADMIN - EDIT TEAM
@app.route("/admin/teams/<int:team_id>/edit", methods=["GET", "POST"])
@admin_required
def admin_edit_team(team_id):

    team = db.get_or_404(Team, team_id)

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        country = request.form.get("country", "").strip()
        record = request.form.get("record", "").strip()
        image_url = request.form.get("image_url", "").strip()
        biography = request.form.get("biography", "").strip()

        if not name:
            flash("Team name is required.", "danger")
            return redirect(url_for("admin_edit_team", team_id=team.id))

        if len(name) > 100 or len(country) > 100:
            flash("Team name or country is too long.", "danger")
            return redirect(url_for("admin_edit_team", team_id=team.id))

        if len(record) > 20 or len(image_url) > 500:
            flash("Record or logo path is too long.", "danger")
            return redirect(url_for("admin_edit_team", team_id=team.id))

        existing_team = Team.query.filter(
            Team.name == name,
            Team.id != team.id
        ).first()

        if existing_team:
            flash("Another team already uses that name.", "danger")
            return redirect(url_for("admin_edit_team", team_id=team.id))

        team.name = name
        team.country = country
        team.record = record
        team.image_url = image_url
        team.biography = biography

        db.session.commit()

        flash("Team updated successfully!", "success")
        return redirect(url_for("admin_teams"))

    return render_template("admin_team_form.html", team=team)

# ADMIN - DELETE TEAM
@app.route("/admin/teams/<int:team_id>/delete", methods=["POST"])
@admin_required
def admin_delete_team(team_id):

    team = db.get_or_404(Team, team_id)

    if team.players:
        flash(
            "You cannot delete a team that still has players. "
            "Transfer or delete its players first.",
            "danger"
        )
        return redirect(url_for("admin_teams"))

    team_name = team.name

    # Remove associated team pictures first
    for picture in team.pictures:
        db.session.delete(picture)

    db.session.delete(team)
    db.session.commit()

    flash(f"{team_name} was deleted.", "success")
    return redirect(url_for("admin_teams"))


@app.route('/draft')
def draft_mode():
    return render_template('draft.html')


@app.route('/api/draft/pool')
def draft_pool():
    teams = Team.query.order_by(Team.id).all()
    players = Player.query.order_by(Player.id).all()

    return jsonify({
        'teams': [
            {
                'id': team.id,
                'name': team.name,
                'image_url': team.image_url,
            }
            for team in teams
        ],
        'players': [
            {
                'id': player.id,
                'name': player.name,
                'picture_url': player.picture_url,
                'nationality': player.nationality,
                'position': player.position,
                'rating': player.rating,
                'offense': player.offense,
                'defense': player.defense,
                'points_per_game': player.points_per_game,
                'assists_per_game': player.assists_per_game,
                'rebounds_per_game': player.rebounds_per_game,
                "blocks_per_game": player.blocks_per_game,
                "steals_per_game": player.steals_per_game,
                'team_name': player.team.name if player.team else None,
                'team_id': player.team_id,
            }
            for player in players
        ],
    })


# =====================================================
# SERVER-SIDE DRAFT SIMULATION
# =====================================================

DRAFT_POSITIONS = ("PG", "SG", "SF", "PF", "C")


def draft_player_positions(player):
    return {
        value.strip().upper()
        for value in (player.position or "").replace(",", "/").split("/")
    }


def calculate_draft_rating(lineup):
    players = list(lineup.values())

    def total(field):
        return sum(float(getattr(p, field) or 0) for p in players)

    def average(field):
        return total(field) / 5

    def normalize(value, target):
        return max(0, min(100, value / target * 100))

    overall = normalize(average("rating"), 100)
    offense = normalize(average("offense"), 100)
    defense = normalize(average("defense"), 100)

    scoring = normalize(total("points_per_game"), 70)

    all_around = (
        normalize(total("assists_per_game"), 18) * 0.35
        + normalize(total("rebounds_per_game"), 28) * 0.35
        + normalize(total("steals_per_game"), 7) * 0.15
        + normalize(total("blocks_per_game"), 4.5) * 0.15
    )

    base_score = (
        overall * 0.15
        + offense * 0.25
        + defense * 0.25
        + scoring * 0.20
        + all_around * 0.15
    )

    # Match the current JavaScript rule: exact position only.
    out_of_position = sum(
        1
        for pos, player in lineup.items()
        if (player.position or "").strip().upper() != pos
    )

    multiplier = 2.0 - out_of_position * 0.3

    return {
        "base_score": base_score,
        "out_of_position": out_of_position,
        "position_multiplier": multiplier,
        "total_points": base_score * multiplier
    }


def opponent_strength(team, players):
    available = [
        p for p in players
        if p.team_id == team.id
    ]

    starters = []

    for pos in DRAFT_POSITIONS:
        if not available:
            break

        matching = [
            p for p in available
            if pos in draft_player_positions(p)
        ]

        pool = matching if matching else available

        chosen = max(
            pool,
            key=lambda p: p.rating or 0
        )

        starters.append(chosen)
        available.remove(chosen)

    if not starters:
        return 120.0

    def avg(field):
        return sum(
            float(getattr(p, field) or 0)
            for p in starters
        ) / len(starters)

    strength = (
        avg("rating") * 0.20
        + avg("offense") * 0.40
        + avg("defense") * 0.40
    ) * 1.65

    return max(60, min(190, strength))


def draft_game(a, b, home_advantage=0):
    difference = (
        a["strength"] - b["strength"] + home_advantage
    )

    probability = 1 / (1 + math.exp(-difference / 22))

    return a if random.random() < probability else b


def draft_series(a, b):
    wins_a = 0
    wins_b = 0

    for home in (4, 4, -4, -4, 4):
        winner = draft_game(a, b, home)

        if winner is a:
            wins_a += 1
        else:
            wins_b += 1

        if wins_a == 3 or wins_b == 3:
            break

    return a if wins_a == 3 else b


def run_draft_season(club, rating, teams, players):
    user_team = {
        "id": "drafted-team",
        "name": club.name,
        "strength": rating["total_points"],
        "wins": 0,
        "losses": 0
    }

    competitors = [user_team]

    for team in teams:
        competitors.append({
            "id": team.id,
            "name": team.name,
            "strength": opponent_strength(team, players),
            "wins": 0,
            "losses": 0
        })

    # Double round-robin regular season.
    for i in range(len(competitors)):
        for j in range(i + 1, len(competitors)):
            a = competitors[i]
            b = competitors[j]

            for home in (4, -4):
                winner = draft_game(a, b, home)
                loser = b if winner is a else a

                winner["wins"] += 1
                loser["losses"] += 1

    standings = sorted(
        competitors,
        key=lambda t: (t["wins"], t["strength"]),
        reverse=True
    )

    seed = standings.index(user_team) + 1

    result = {
        "wins": user_team["wins"],
        "losses": user_team["losses"],
        "seed": seed,
        "totalTeams": len(competitors),
        "teamStrength": rating["total_points"],
        "outcome": "",
        "details": ""
    }

    def finish(outcome, details):
        result["outcome"] = outcome
        result["details"] = details
        return result

    if seed > 10:
        return finish(
            "OUT OF PLAYOFFS",
            "Your team failed to qualify for the postseason."
        )

    # Play-in: 7 vs 8 and 9 vs 10.
    seventh = standings[6]
    eighth = standings[7]
    ninth = standings[8]
    tenth = standings[9]

    seventh_seed = draft_game(seventh, eighth, 4)
    loser_78 = (
        eighth if seventh_seed is seventh else seventh
    )

    winner_910 = draft_game(ninth, tenth, 4)
    eighth_seed = draft_game(loser_78, winner_910, 4)

    if seed >= 7 and user_team not in (
        seventh_seed, eighth_seed
    ):
        return finish(
            "PLAY-IN ELIMINATION",
            "Your team reached the play-in but did not qualify for the playoffs."
        )

    playoff_teams = (
        standings[:6] + [seventh_seed, eighth_seed]
    )

    matchups = [
        (playoff_teams[0], playoff_teams[7]),
        (playoff_teams[1], playoff_teams[6]),
        (playoff_teams[2], playoff_teams[5]),
        (playoff_teams[3], playoff_teams[4])
    ]

    final_four = [
        draft_series(a, b)
        for a, b in matchups
    ]

    if user_team not in final_four:
        return finish(
            "PLAYOFF ELIMINATION",
            "Your team lost its best-of-five quarterfinal series."
        )

    final_four.sort(key=lambda t: standings.index(t))

    finalist_a = draft_game(final_four[0], final_four[3])
    finalist_b = draft_game(final_four[1], final_four[2])

    if user_team not in (finalist_a, finalist_b):
        return finish(
            "FINAL FOUR",
            "Your team reached the Final Four but lost in the semifinals."
        )

    champion = draft_game(finalist_a, finalist_b)

    if champion is not user_team:
        return finish(
            "EUROLEAGUE FINALIST",
            "Your team reached the final but finished as runner-up."
        )

    return finish(
        "EUROLEAGUE CHAMPIONS",
        "Congratulations! Your team won the EuroLeague!"
    )




@app.route("/api/draft/simulate", methods=["POST"])
def simulate_draft_api():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "Invalid request."}), 400

    club_id = data.get("club_id")
    lineup_data = data.get("lineup")
    run_token = data.get("run_token")

    if not isinstance(lineup_data, dict):
        return jsonify({"error": "Invalid lineup."}), 400

    if set(lineup_data.keys()) != set(DRAFT_POSITIONS):
        return jsonify({
            "error": "Your lineup must contain PG, SG, SF, PF and C."
        }), 400

    try:
        player_ids = {
            pos: int(lineup_data[pos])
            for pos in DRAFT_POSITIONS
        }
        club_id = int(club_id)
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid player or club ID."}), 400

    if len(set(player_ids.values())) != 5:
        return jsonify({
            "error": "You cannot draft the same player twice."
        }), 400

    club = db.session.get(Team, club_id)

    if club is None:
        return jsonify({"error": "Club not found."}), 404

    players = Player.query.filter(
        Player.id.in_(list(player_ids.values()))
    ).all()

    if len(players) != 5:
        return jsonify({"error": "One or more players were not found."}), 400

    players_by_id = {p.id: p for p in players}

    lineup = {
        pos: players_by_id[player_ids[pos]]
        for pos in DRAFT_POSITIONS
    }

    rating = calculate_draft_rating(lineup)

    # Guests receive a result but don't save anything.
    is_logged_in = current_user.is_authenticated

    # For logged-in users, check whether this draft was saved already.
    if is_logged_in:
        try:
            token = str(uuid4()) if run_token is None else str(
                __import__("uuid").UUID(str(run_token))
            )
        except (ValueError, TypeError, AttributeError):
            return jsonify({"error": "Invalid simulation token."}), 400

        existing = DraftRun.query.filter_by(
            run_token=token
        ).first()

        if existing:
            if existing.user_id != current_user.id:
                return jsonify({"error": "Invalid simulation token."}), 409

            return jsonify({
                "saved": True,
                "already_saved": True,
                "run_id": existing.id,
                "result": {
                    "wins": existing.wins,
                    "losses": existing.losses,
                    "seed": existing.seed,
                    "totalTeams": Team.query.count() + 1,
                    "teamStrength": existing.team_score,
                    "outcome": existing.outcome,
                    "details": "This simulation was already saved."
                },
                "new_achievements": []
            })

    all_teams = Team.query.order_by(Team.id).all()
    all_players = Player.query.all()

    result = run_draft_season(
        club, rating, all_teams, all_players
    )

    if not is_logged_in:
        return jsonify({
            "saved": False,
            "result": result,
            "new_achievements": []
        })

    draft_run = DraftRun(
        user_id=current_user.id,
        club_id=club.id,
        team_score=rating["total_points"],
        base_score=rating["base_score"],
        out_of_position=rating["out_of_position"],
        wins=result["wins"],
        losses=result["losses"],
        seed=result["seed"],
        outcome=result["outcome"],
        lineup=player_ids,
        run_token=token
    )

    try:
        db.session.add(draft_run)

        # Make the new run visible to achievement queries.
        db.session.flush()

        unlocked = unlock_draft_achievements(
            current_user.id,
            draft_run
        )

        db.session.commit()

    except IntegrityError:
        db.session.rollback()
        return jsonify({
            "error": "This draft was already submitted. Please refresh your draft history."
        }), 409

    except Exception:
        db.session.rollback()
        app.logger.exception("Failed to save draft")
        return jsonify({
            "error": "Could not save the simulation."
        }), 500

    return jsonify({
        "saved": True,
        "already_saved": False,
        "run_id": draft_run.id,
        "result": result,
        "new_achievements": unlocked
    })

# =====================================================
# CURRENT USER'S DRAFT STATISTICS
# =====================================================

@app.route("/api/draft/my-stats", methods=["GET"])
@login_required
def my_draft_stats():

    user_id = current_user.id

    drafts = DraftRun.query.filter_by(
        user_id=user_id
    )

    total_drafts = drafts.count()

    best_score = db.session.query(
        func.max(DraftRun.team_score)
    ).filter(
        DraftRun.user_id == user_id
    ).scalar()

    average_score = db.session.query(
        func.avg(DraftRun.team_score)
    ).filter(
        DraftRun.user_id == user_id
    ).scalar()

    championships = drafts.filter_by(
        outcome="EUROLEAGUE CHAMPIONS"
    ).count()

    playoff_outcomes = [
        "PLAYOFF ELIMINATION",
        "FINAL FOUR",
        "EUROLEAGUE FINALIST",
        "EUROLEAGUE CHAMPIONS"
    ]

    final_four_outcomes = [
        "FINAL FOUR",
        "EUROLEAGUE FINALIST",
        "EUROLEAGUE CHAMPIONS"
    ]

    playoffs = drafts.filter(
        DraftRun.outcome.in_(playoff_outcomes)
    ).count()

    final_fours = drafts.filter(
        DraftRun.outcome.in_(final_four_outcomes)
    ).count()

    best_draft = drafts.order_by(
        DraftRun.team_score.desc()
    ).first()

    achievements = UserAchievement.query.filter_by(
        user_id=user_id
    ).all()

    equipped = UserTitle.query.filter_by(
        user_id=user_id
    ).first()

    return jsonify({
        "total_drafts": total_drafts,
        "best_score": round(best_score or 0, 1),
        "average_score": round(average_score or 0, 1),
        "championships": championships,
        "playoff_appearances": playoffs,
        "final_four_appearances": final_fours,

        "best_draft": {
            "score": best_draft.team_score,
            "lineup": best_draft.lineup,
            "club_id": best_draft.club_id,
            "outcome": best_draft.outcome
        } if best_draft else None,

        "achievements": [
            {
                "key": a.achievement_key,
                "name": DRAFT_ACHIEVEMENTS.get(
                    a.achievement_key, {}
                ).get("name", a.achievement_key)
            }
            for a in achievements
        ],

        "equipped_title": (
            equipped.title_key if equipped else None
        )
    })


# ---------------------------------------
# PROFILE: FAVORITE TEAM
# ---------------------------------------

@app.route("/api/profile/favorite-team", methods=["GET", "POST"])
@login_required
def profile_favorite_team():
    if request.method == "GET":
        teams = Team.query.order_by(Team.name).all()

        return jsonify({
            "favorite_team_id": current_user.favorite_team_id,
            "teams": [
                {
                    "id": team.id,
                    "name": team.name,
                    "image_url": team.image_url
                }
                for team in teams
            ]
        })

    data = request.get_json(silent=True) or {}
    team_id = data.get("team_id")

    # Allow users to clear their favorite team.
    if team_id is None:
        current_user.favorite_team_id = None
        db.session.commit()

        return jsonify({
            "success": True,
            "favorite_team_id": None
        })

    try:
        team_id = int(team_id)
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid team ID."}), 400

    team = db.session.get(Team, team_id)

    if team is None:
        return jsonify({"error": "Team not found."}), 404

    current_user.favorite_team_id = team.id
    db.session.commit()

    return jsonify({
        "success": True,
        "favorite_team_id": team.id,
        "team_name": team.name,
        "image_url": team.image_url
    })


# ---------------------------------------
# PROFILE: EQUIPPABLE TITLES
# ---------------------------------------

# Each title is unlocked by its corresponding achievement.
# These keys match the Draft achievements we created.
PROFILE_TITLES = {
    "first_draft": "Rookie GM",
    "first_playoffs": "Playoff Contender",
    "first_final_four": "Final Four Challenger",
    "first_championship": "EuroLeague Champion",
    "five_championships": "Dynasty Builder",
    "elite_draft": "Elite Architect",
    "perfect_positions": "Master Tactician",
    "draft_veteran": "Draft Veteran"
}


@app.route("/api/profile/titles", methods=["GET"])
@login_required
def profile_titles():
    achievements = UserAchievement.query.filter_by(
        user_id=current_user.id
    ).all()

    unlocked_keys = {
        achievement.achievement_key
        for achievement in achievements
    }

    equipped = UserTitle.query.filter_by(
        user_id=current_user.id
    ).first()

    equipped_key = equipped.title_key if equipped else None

    return jsonify({
        "equipped_title": equipped_key,
        "titles": [
            {
                "key": key,
                "name": name,
                "unlocked": key in unlocked_keys,
                "equipped": key == equipped_key
            }
            for key, name in PROFILE_TITLES.items()
        ]
    })


@app.route("/api/profile/titles/equip", methods=["POST"])
@login_required
def equip_profile_title():
    data = request.get_json(silent=True) or {}
    title_key = data.get("title_key")

    # None means unequip the current title.
    if title_key is not None:
        if not isinstance(title_key, str):
            return jsonify({"error": "Invalid title."}), 400

        if title_key not in PROFILE_TITLES:
            return jsonify({"error": "Unknown title."}), 400

        achievement = UserAchievement.query.filter_by(
            user_id=current_user.id,
            achievement_key=title_key
        ).first()

        if achievement is None:
            return jsonify({
                "error": "You haven't unlocked this title yet."
            }), 403

    equipped = UserTitle.query.filter_by(
        user_id=current_user.id
    ).first()

    if equipped is None and title_key is not None:
        equipped = UserTitle(
            user_id=current_user.id,
            title_key=title_key
        )
        db.session.add(equipped)

    elif equipped is not None:
        if title_key is None:
            db.session.delete(equipped)
        else:
            equipped.title_key = title_key

    db.session.commit()

    return jsonify({
        "success": True,
        "equipped_title": title_key,
        "title_name": (
            PROFILE_TITLES[title_key]
            if title_key is not None
            else None
        )
    })




initialize_database()


if __name__ == "__main__":
    app.run(debug=True)
