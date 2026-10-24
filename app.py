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
from basketball_grid_backend import register_basketball_grid

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


#Legends
class Legend(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(100), unique=True, nullable=False)
    nationality = db.Column(db.String(50))
    position = db.Column(db.String(10), nullable=False)

    rating = db.Column(db.Integer, default=90)
    offense = db.Column(db.Integer, default=90)
    defense = db.Column(db.Integer, default=90)

    points_per_game = db.Column(db.Float, default=0.0)
    assists_per_game = db.Column(db.Float, default=0.0)
    rebounds_per_game = db.Column(db.Float, default=0.0)
    blocks_per_game = db.Column(db.Float, default=0.0)
    steals_per_game = db.Column(db.Float, default=0.0)
    fg_percentage = db.Column(db.Float, default=0.0)

    picture_url = db.Column(db.String(500))
    peak_season = db.Column(db.String(20))
    legendary_team = db.Column(db.String(100))




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

    # Official EuroLeague season totals (populated by a separate sync script).
    # NULL means not yet imported; existing averages are preserved until then.
    games_played = db.Column(db.Integer, nullable=True)
    total_points = db.Column(db.Integer, nullable=True)
    total_assists = db.Column(db.Integer, nullable=True)
    total_rebounds = db.Column(db.Integer, nullable=True)
    total_blocks = db.Column(db.Integer, nullable=True)
    total_steals = db.Column(db.Integer, nullable=True)
    total_turnovers = db.Column(db.Integer, nullable=True)
    total_fgm = db.Column(db.Integer, nullable=True)
    total_fga = db.Column(db.Integer, nullable=True)


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
# HIGHER OR LOWER — USER STATISTICS
# =====================================================

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


# =====================================================
# ADMIN - PLAYER SEASON STATISTICS
# =====================================================

PLAYER_TOTAL_FIELDS = (
    "games_played",
    "total_points",
    "total_assists",
    "total_rebounds",
    "total_blocks",
    "total_steals",
    "total_turnovers",
    "total_fgm",
    "total_fga",
)


def read_player_statistics(form):
    """
    Validate the submitted season totals.
    Return a dictionary containing totals and calculated averages.
    """

    stats = {}

    for field in PLAYER_TOTAL_FIELDS:
        raw_value = form.get(field, "").strip()

        if not raw_value:
            raise ValueError(f"{field} is required.")

        try:
            value = int(raw_value)
        except ValueError:
            raise ValueError(f"{field} must be a whole number.")

        if value < 0:
            raise ValueError(f"{field} cannot be negative.")

        stats[field] = value

    games = stats["games_played"]
    fgm = stats["total_fgm"]
    fga = stats["total_fga"]

    if fgm > fga:
        raise ValueError(
            "Field goals made cannot exceed field goals attempted."
        )

    if games == 0 and any(
        stats[field] > 0
        for field in PLAYER_TOTAL_FIELDS
        if field != "games_played"
    ):
        raise ValueError(
            "Games played must be greater than zero "
            "when season totals are entered."
        )

    def average(total):
        return round(total / games, 2) if games > 0 else 0.0

    stats["points_per_game"] = average(stats["total_points"])
    stats["assists_per_game"] = average(stats["total_assists"])
    stats["rebounds_per_game"] = average(stats["total_rebounds"])
    stats["blocks_per_game"] = average(stats["total_blocks"])
    stats["steals_per_game"] = average(stats["total_steals"])

    stats["fg_percentage"] = (
        round(fgm / fga * 100, 2)
        if fga > 0
        else 0.0
    )

    return stats


def apply_player_statistics(player, stats):
    """Assign validated statistics to a Player model."""

    for field, value in stats.items():
        setattr(player, field, value)


# =====================================================
# ADMIN - ADD PLAYER
# =====================================================

@app.route("/admin/players/add", methods=["GET", "POST"])
@admin_required
def admin_add_player():

    teams = Team.query.order_by(Team.name).all()

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        nationality = request.form.get("nationality", "").strip()
        position = request.form.get("position", "").strip()
        picture_url = request.form.get("picture_url", "").strip()

        try:
            team_id = int(request.form.get("team_id", ""))

            rating = int(request.form.get("rating", "70"))
            offense = int(request.form.get("offense", "70"))
            defense = int(request.form.get("defense", "70"))

            if not name:
                raise ValueError("Player name is required.")

            if len(name) > 100 or len(nationality) > 50:
                raise ValueError("Name or nationality is too long.")

            if position not in ("PG", "SG", "SF", "PF", "C"):
                raise ValueError("Invalid player position.")

            if len(picture_url) > 200:
                raise ValueError(
                    "Picture URL must be 200 characters or fewer."
                )

            if not all(
                0 <= value <= 100
                for value in (rating, offense, defense)
            ):
                raise ValueError(
                    "Ratings must be between 0 and 100."
                )

            team = db.session.get(Team, team_id)

            if team is None:
                raise ValueError("Please select a valid team.")

            # Read totals and calculate averages.
            statistics = read_player_statistics(request.form)

        except (ValueError, TypeError) as error:
            flash(f"Invalid player information: {error}", "danger")
            return redirect(url_for("admin_add_player"))

        player = Player(
            name=name,
            nationality=nationality,
            position=position,
            picture_url=picture_url,
            rating=rating,
            offense=offense,
            defense=defense,
            team_id=team_id
        )

        apply_player_statistics(player, statistics)

        db.session.add(player)
        db.session.commit()

        flash("Player added successfully!", "success")
        return redirect(url_for("admin_players"))

    return render_template(
        "admin_player_form.html",
        player=None,
        teams=teams
    )





# =====================================================
# ADMIN - EDIT PLAYER
# =====================================================

@app.route("/admin/players/<int:player_id>/edit", methods=["GET", "POST"])
@admin_required
def admin_edit_player(player_id):

    player = db.get_or_404(Player, player_id)
    teams = Team.query.order_by(Team.name).all()

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        nationality = request.form.get("nationality", "").strip()
        position = request.form.get("position", "").strip()
        picture_url = request.form.get("picture_url", "").strip()

        try:
            team_id = int(request.form.get("team_id", ""))

            rating = int(request.form.get("rating", "70"))
            offense = int(request.form.get("offense", "70"))
            defense = int(request.form.get("defense", "70"))

            if not name:
                raise ValueError("Player name is required.")

            if len(name) > 100 or len(nationality) > 50:
                raise ValueError("Name or nationality is too long.")

            if position not in ("PG", "SG", "SF", "PF", "C"):
                raise ValueError("Invalid player position.")

            if len(picture_url) > 200:
                raise ValueError(
                    "Picture URL must be 200 characters or fewer."
                )

            if not all(
                0 <= value <= 100
                for value in (rating, offense, defense)
            ):
                raise ValueError(
                    "Ratings must be between 0 and 100."
                )

            team = db.session.get(Team, team_id)

            if team is None:
                raise ValueError("Please select a valid team.")

            # Read totals and calculate averages.
            statistics = read_player_statistics(request.form)

        except (ValueError, TypeError) as error:
            flash(f"Invalid player information: {error}", "danger")

            return redirect(
                url_for("admin_edit_player", player_id=player.id)
            )

        # Update player information.
        player.name = name
        player.nationality = nationality
        player.position = position
        player.picture_url = picture_url

        # Update ratings.
        player.rating = rating
        player.offense = offense
        player.defense = defense

        # Update team.
        player.team_id = team_id

        # Update totals and calculated averages.
        apply_player_statistics(player, statistics)

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
            "games_played": player.games_played,
            "total_points": player.total_points,
            "total_assists": player.total_assists,
            "total_rebounds": player.total_rebounds,
            "total_blocks": player.total_blocks,
            "total_steals": player.total_steals,
            "total_turnovers": player.total_turnovers,
            "total_fgm": player.total_fgm,
            "total_fga": player.total_fga,
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

BasketballGridGame = register_basketball_grid(
    app, db, Player, User
)

# CREATE DATABASE TABLES
def initialize_database():
    with app.app_context():
        db.create_all()

        # Update averages from imported season totals, without resetting players
        # who have not yet been matched to official EuroLeague statistics.
        from update_player_stats import update_all_player_stats
        update_all_player_stats(db, Player)

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
    legends = Legend.query.order_by(Legend.id).all()

    return jsonify({
        "legends": [
            {
                "id": p.id, "name": p.name, "nationality": p.nationality,
                "position": p.position, "rating": p.rating,
                "offense": p.offense, "defense": p.defense,
                "picture_url": p.picture_url,
                "points_per_game": p.points_per_game,
                "assists_per_game": p.assists_per_game,
                "rebounds_per_game": p.rebounds_per_game,
                "blocks_per_game": p.blocks_per_game,
                "steals_per_game": p.steals_per_game,
                "fg_percentage": p.fg_percentage,
                "team_name": p.legendary_team,
                "peak_season": p.peak_season, "is_legend": True
            } for p in legends
        ],
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
POSITION_VALUES = {
    position: index
    for index, position in enumerate(DRAFT_POSITIONS, start=1)
}

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

        # Calculate how far each player is from their natural position.
    position_difference = 0
    out_of_position = 0

    for assigned_position, player in lineup.items():
        natural_positions = draft_player_positions(player)

        distance = min(
            abs(
                POSITION_VALUES[natural] -
                POSITION_VALUES[assigned_position]
            )
            for natural in natural_positions
            if natural in POSITION_VALUES
        ) if any(p in POSITION_VALUES for p in natural_positions) else 4

        position_difference += distance

        if distance > 0:
            out_of_position += 1

    # Each position of distance reduces the multiplier by 0.1.
    multiplier = 2.0 - position_difference * 0.1

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
    """
    Simulate one basketball game.

    Returns a dictionary containing:
    - winner
    - loser
    - home score
    - away score
    - overtime information

    home_advantage is kept for compatibility with
    the existing simulation code.
    """

    strength_a = float(a["strength"])
    strength_b = float(b["strength"])

    # Team strength affects expected scoring.
    # Strength is approximately 60-200 in our system.
    expected_a = (
        81
        + (strength_a - 130) * 0.11
        - (strength_b - 130) * 0.045
        + home_advantage * 0.35
    )

    expected_b = (
        81
        + (strength_b - 130) * 0.11
        - (strength_a - 130) * 0.045
        - home_advantage * 0.15
    )

    # Random variation creates close games and upsets.
    score_a = max(45, round(random.gauss(expected_a, 8)))
    score_b = max(45, round(random.gauss(expected_b, 8)))

    overtime = 0

    # Resolve tied games through overtime.
    while score_a == score_b:
        overtime += 1

        score_a += max(1, round(random.gauss(9, 3)))
        score_b += max(1, round(random.gauss(9, 3)))

    winner = a if score_a > score_b else b
    loser = b if winner is a else a

    return {
        "winner": winner,
        "loser": loser,
        "home_score": score_a,
        "away_score": score_b,
        "overtime": overtime
    }


def draft_series(a, b):
    """
    Best-of-five playoff series.

    The first team has home-court advantage
    in games 1, 2 and 5.
    """

    wins_a = 0
    wins_b = 0
    games = []

    home_pattern = [True, True, False, False, True]

    for game_number, a_is_home in enumerate(home_pattern, 1):

        home = a if a_is_home else b
        away = b if a_is_home else a

        game = draft_game(home, away, home_advantage=4)

        if game["winner"] is a:
            wins_a += 1
        else:
            wins_b += 1

        games.append({
            "game": game_number,
            "home": home["name"],
            "away": away["name"],
            "home_score": game["home_score"],
            "away_score": game["away_score"],
            "overtime": game["overtime"]
        })

        if wins_a == 3 or wins_b == 3:
            break

    winner = a if wins_a == 3 else b

    return {
        "winner": winner,
        "team_a": a["name"],
        "team_b": b["name"],
        "wins_a": wins_a,
        "wins_b": wins_b,
        "games": games
    }




def run_draft_season(club, rating, teams, players):
    """
    Simulate a 20-team EuroLeague season:
    - 38 regular-season games per team
    - 38 matchdays
    - Play-in tournament
    - Best-of-five quarterfinals
    - Final Four

    The user's drafted team replaces their selected club.
    """

    user_team = {
        "id": "drafted-team",
        "name": club.name,
        "strength": rating["total_points"],
        "wins": 0,
        "losses": 0,
        "points_for": 0,
        "points_against": 0
    }

    competitors = [user_team]

    # The drafted team replaces the selected club.
    for team in teams:
        if team.id == club.id:
            continue

        competitors.append({
            "id": team.id,
            "name": team.name,
            "strength": opponent_strength(team, players),
            "wins": 0,
            "losses": 0,
            "points_for": 0,
            "points_against": 0
        })

    # Build the double round-robin schedule.
    # Circle method: 19 opponents, home and away.
    rotation = competitors[:]
    first_half = []

    for round_index in range(19):
        fixtures = []

        for i in range(10):
            a = rotation[i]
            b = rotation[19 - i]

            # Alternate home assignments.
            if (round_index + i) % 2 == 0:
                home, away = a, b
            else:
                home, away = b, a

            fixtures.append((home, away))

        first_half.append(fixtures)

        # Keep the first team fixed.
        rotation = (
            [rotation[0]]
            + [rotation[-1]]
            + rotation[1:-1]
        )

    schedule = first_half + [
        [(away, home) for home, away in fixtures]
        for fixtures in first_half
    ]

    matchdays = []

    # REGULAR SEASON
    for matchday_number, fixtures in enumerate(schedule, 1):
        matches = []

        for home, away in fixtures:
            game = draft_game(home, away, home_advantage=4)

            home["points_for"] += game["home_score"]
            home["points_against"] += game["away_score"]

            away["points_for"] += game["away_score"]
            away["points_against"] += game["home_score"]

            game["winner"]["wins"] += 1
            game["loser"]["losses"] += 1

            matches.append({
                "home_id": home["id"],
                "away_id": away["id"],
                "home": home["name"],
                "away": away["name"],
                "home_score": game["home_score"],
                "away_score": game["away_score"],
                "overtime": game["overtime"],
                "is_user_game": (
                    home is user_team or away is user_team
                )
            })

        matchdays.append({
            "matchday": matchday_number,
            "matches": matches
        })

    def rank_key(team):
        return (
            team["wins"],
            team["points_for"] - team["points_against"],
            team["strength"]
        )

    standings = sorted(
        competitors,
        key=rank_key,
        reverse=True
    )

    seed = standings.index(user_team) + 1

    standings_data = []

    for position, team in enumerate(standings, 1):
        standings_data.append({
            "position": position,
            "id": team["id"],
            "name": team["name"],
            "wins": team["wins"],
            "losses": team["losses"],
            "points_for": team["points_for"],
            "points_against": team["points_against"],
            "point_difference": (
                team["points_for"] - team["points_against"]
            ),
            "is_user_team": team is user_team
        })

    result = {
        "wins": user_team["wins"],
        "losses": user_team["losses"],
        "seed": seed,
        "totalTeams": len(competitors),
        "teamStrength": rating["total_points"],
        "outcome": "",
        "details": "",
        "matchdays": matchdays,
        "standings": standings_data,
        "play_in": [],
        "playoffs": [],
        "final_four": []
    }

    def finish(outcome, details):
        result["outcome"] = outcome
        result["details"] = details
        return result

    def knockout_game(home, away, stage):
        game = draft_game(home, away, home_advantage=4)

        return {
            "stage": stage,
            "home": home["name"],
            "away": away["name"],
            "home_score": game["home_score"],
            "away_score": game["away_score"],
            "overtime": game["overtime"],
            "winner": game["winner"]["name"]
        }, game["winner"]

   
    # =====================================================
    # COMPLETE EUROLEAGUE POSTSEASON
    # Always simulate the entire tournament.
    # =====================================================

    user_outcome = None
    user_details = None

    if seed > 10:
        user_outcome = "OUT OF PLAYOFFS"
        user_details = "Your team finished outside the top ten."

    # PLAY-IN TOURNAMENT
    seventh = standings[6]
    eighth = standings[7]
    ninth = standings[8]
    tenth = standings[9]

    game78, seventh_seed = knockout_game(
        seventh, eighth, "7 vs 8"
    )

    loser78 = (
        eighth if seventh_seed is seventh else seventh
    )

    game910, winner910 = knockout_game(
        ninth, tenth, "9 vs 10"
    )

    game8, eighth_seed = knockout_game(
        loser78, winner910, "Final play-in"
    )

    result["play_in"] = [game78, game910, game8]

    if 7 <= seed <= 10 and user_team not in (
        seventh_seed, eighth_seed
    ):
        user_outcome = "PLAY-IN ELIMINATION"
        user_details = (
            "Your team was eliminated in the play-in tournament."
        )

    # PLAYOFF QUARTERFINALS
    playoff_teams = (
        standings[:6] + [seventh_seed, eighth_seed]
    )

    matchups = [
        (playoff_teams[0], playoff_teams[7]),
        (playoff_teams[1], playoff_teams[6]),
        (playoff_teams[2], playoff_teams[5]),
        (playoff_teams[3], playoff_teams[4])
    ]

    final_four_teams = []

    for a, b in matchups:
        series = draft_series(a, b)

        final_four_teams.append(series["winner"])

        result["playoffs"].append({
            "team_a": series["team_a"],
            "team_b": series["team_b"],
            "wins_a": series["wins_a"],
            "wins_b": series["wins_b"],
            "winner": series["winner"]["name"],
            "games": series["games"]
        })

    if (
        user_outcome is None
        and user_team not in final_four_teams
    ):
        user_outcome = "PLAYOFF ELIMINATION"
        user_details = (
            "Your team lost its best-of-five quarterfinal series."
        )

    # FINAL FOUR
    final_four_teams.sort(
        key=lambda team: standings.index(team)
    )

    semifinal1, finalist_a = knockout_game(
        final_four_teams[0],
        final_four_teams[3],
        "Semifinal 1"
    )

    semifinal2, finalist_b = knockout_game(
        final_four_teams[1],
        final_four_teams[2],
        "Semifinal 2"
    )

    result["final_four"].extend([
        semifinal1,
        semifinal2
    ])

    if (
        user_outcome is None
        and user_team not in (finalist_a, finalist_b)
    ):
        user_outcome = "FINAL FOUR"
        user_details = (
            "Your team reached the Final Four "
            "but lost in the semifinals."
        )

    # CHAMPIONSHIP GAME
    championship, champion = knockout_game(
        finalist_a,
        finalist_b,
        "EuroLeague Final"
    )

    result["final_four"].append(championship)

    if user_outcome is None:
        if champion is user_team:
            user_outcome = "EUROLEAGUE CHAMPIONS"
            user_details = (
                "Congratulations! Your team won the EuroLeague!"
            )
        else:
            user_outcome = "EUROLEAGUE FINALIST"
            user_details = (
                "Your team reached the championship game "
                "but finished runner-up."
            )

    result["champion"] = champion["name"]

    return finish(user_outcome, user_details)





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
        club_id = int(club_id)
        references = {}
        for pos in DRAFT_POSITIONS:
            item = lineup_data[pos]
            if not isinstance(item, dict) or item.get("type") not in ("player", "legend"):
                raise ValueError("Invalid player reference")
            player_id = int(item["id"])
            if player_id <= 0:
                raise ValueError("Invalid player ID")
            references[pos] = {"type": item["type"], "id": player_id}
    except (ValueError, TypeError, KeyError):
        return jsonify({"error": "Invalid player or club ID."}), 400

    keys = [(p["type"], p["id"]) for p in references.values()]
    if len(set(keys)) != 5:
        return jsonify({"error": "You cannot draft the same player twice."}), 400
    if sum(p["type"] == "legend" for p in references.values()) > 1:
        return jsonify({"error": "Only one legend is allowed per draft."}), 400

    club = db.session.get(Team, club_id)
    if club is None:
        return jsonify({"error": "Club not found."}), 404

    lineup = {}
    for pos, ref in references.items():
        model = Legend if ref["type"] == "legend" else Player
        entry = db.session.get(model, ref["id"])
        if entry is None:
            return jsonify({"error": "One or more players were not found."}), 400
        lineup[pos] = entry

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
                    "totalTeams": Team.query.count(),
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
        lineup=references,
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
# PROFILE: UPDATE USERNAME AND EMAIL
# ---------------------------------------

@app.route("/api/profile/account", methods=["POST"])
@login_required
def update_profile_account():
    """Update the authenticated user's account details."""
    # Browser-side protection against cross-site requests.
    origin = request.headers.get("Origin")
    if origin and origin.rstrip("/") != request.host_url.rstrip("/"):
        return jsonify({"error": "Invalid request origin."}), 403

    # Only accept JSON objects, not forms or arbitrary content.
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Expected JSON account details."}), 400

    username = data.get("username")
    email = data.get("email")

    if not isinstance(username, str) or not isinstance(email, str):
        return jsonify({"error": "Username and email must be text."}), 400

    username = username.strip()
    email = email.strip().lower()

    # Match the database column limits (User.username=50, User.email=120).
    if not 3 <= len(username) <= 50:
        return jsonify({"error": "Username must be 3 to 50 characters."}), 400

    if not 3 <= len(email) <= 120 or email.count("@") != 1:
        return jsonify({"error": "Enter a valid email address."}), 400

    local, domain = email.rsplit("@", 1)
    if (not local or not domain or "." not in domain or
            any(char.isspace() for char in email)):
        return jsonify({"error": "Enter a valid email address."}), 400

    # Do not treat the current user's own values as duplicates.
    existing_username = User.query.filter(
        func.lower(User.username) == username.lower(),
        User.id != current_user.id
    ).first()
    if existing_username:
        return jsonify({"error": "This username is already taken."}), 409

    existing_email = User.query.filter(
        func.lower(User.email) == email,
        User.id != current_user.id
    ).first()
    if existing_email:
        return jsonify({"error": "An account with this email already exists."}), 409

    try:
        current_user.username = username
        current_user.email = email
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "Username or email is already in use."}), 409
    except Exception:
        db.session.rollback()
        app.logger.exception("Failed to update profile account")
        return jsonify({"error": "Could not save account details."}), 500

    return jsonify({
        "success": True,
        "username": current_user.username,
        "email": current_user.email
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


# ==========================================
# BASKETBALL GRID — PROFILE INTEGRATION
# ==========================================
GRID_ACHIEVEMENTS = {
    "bg_first_game": {"name": "Grid Rookie", "description": "Finish your first Basketball Grid game.", "icon": "🏀"},
    "bg_first_win": {"name": "Grid Winner", "description": "Win your first Basketball Grid game.", "icon": "🏆"},
    "bg_five_wins": {"name": "Grid Specialist", "description": "Win five Basketball Grid games.", "icon": "🎯"},
    "bg_twenty_wins": {"name": "Grid Master", "description": "Win twenty Basketball Grid games.", "icon": "👑"},
    "bg_nine_correct": {"name": "Perfect Grid", "description": "Complete all nine squares in a game.", "icon": "💎"},
    "bg_25_games": {"name": "Grid Veteran", "description": "Finish 25 Basketball Grid games.", "icon": "🎖️"},
}

def sync_grid_achievements(user_id, grid_record):
    if grid_record is None:
        return
    eligible = set()
    if grid_record.games >= 1:
        eligible.add("bg_first_game")
    if grid_record.wins >= 1:
        eligible.add("bg_first_win")
    if grid_record.wins >= 5:
        eligible.add("bg_five_wins")
    if grid_record.wins >= 20:
        eligible.add("bg_twenty_wins")
    if grid_record.best_correct >= 9:
        eligible.add("bg_nine_correct")
    if grid_record.games >= 25:
        eligible.add("bg_25_games")
    existing = {item.achievement_key for item in UserAchievement.query.filter_by(user_id=user_id).all()}
    for key in eligible - existing:
        db.session.add(UserAchievement(user_id=user_id, achievement_key=key))
    if eligible - existing:
        db.session.commit()

@app.get("/api/games/basketball-grid/profile")
@login_required
def basketball_grid_profile():
    grid_record = BasketballGridGame.query.filter_by(user_id=current_user.id).first()
    sync_grid_achievements(current_user.id, grid_record)
    games = grid_record.games if grid_record else 0
    wins = grid_record.wins if grid_record else 0
    stats = {
        "games": games,
        "wins": wins,
        "losses": grid_record.losses if grid_record else 0,
        "best_correct": grid_record.best_correct if grid_record else 0,
        "win_rate": round(wins * 100 / games, 1) if games else 0,
    }
    unlocked = {item.achievement_key for item in UserAchievement.query.filter_by(user_id=current_user.id).all()}
    return jsonify({
        "stats": stats,
        "achievements": [dict(key=key, **definition, unlocked=(key in unlocked)) for key, definition in GRID_ACHIEVEMENTS.items()]
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
    "draft_veteran": "Draft Veteran",
    
    "hl_first_game": "First Comparison",
    "hl_streak_5": "Getting Warm",
    "hl_streak_10": "On Fire",
    "hl_streak_20": "EuroLeague Expert",
    "hl_correct_50": "Sharp Shooter",
    "hl_games_25": "Dedicated Analyst",
    "gp_first_win": "First Identification",
    "gp_five_wins": "Scout",
    "gp_twenty_wins": "Master Scout",
    "gp_first_try": "Perfect Read",
    "gp_streak_5": "Unstoppable Scout",
    "gp_games_25": "Dedicated Scout",
    "bg_first_game": "Grid Rookie",
    "bg_first_win": "Grid Winner",
    "bg_five_wins": "Grid Specialist",
    "bg_twenty_wins": "Grid Master",
    "bg_nine_correct": "Perfect Grid",
    "bg_25_games": "Grid Veteran",

}


@app.route("/api/profile/titles", methods=["GET"])
@login_required
def profile_titles():
    sync_grid_achievements(current_user.id, BasketballGridGame.query.filter_by(user_id=current_user.id).first())
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


@app.route("/api/legends", methods=["GET"])
def get_legends():
    position = request.args.get("position", "").upper().strip()

    query = Legend.query

    if position:
        if position not in ("PG", "SG", "SF", "PF", "C"):
            return jsonify({"error": "Invalid position"}), 400

        query = query.filter_by(position=position)

    legends = query.order_by(
        Legend.rating.desc(),
        Legend.name.asc()
    ).all()

    return jsonify([
        {
            "id": legend.id,
            "name": legend.name,
            "nationality": legend.nationality,
            "position": legend.position,
            "rating": legend.rating,
            "offense": legend.offense,
            "defense": legend.defense,
            "points_per_game": legend.points_per_game,
            "assists_per_game": legend.assists_per_game,
            "rebounds_per_game": legend.rebounds_per_game,
            "blocks_per_game": legend.blocks_per_game,
            "steals_per_game": legend.steals_per_game,
            "fg_percentage": legend.fg_percentage,
            "picture_url": legend.picture_url,
            "peak_season": legend.peak_season,
            "legendary_team": legend.legendary_team,
            "stats_type": legend.stats_type,
            "is_legend": True
        }
        for legend in legends
    ])


# =====================================================
# ADMIN - LEGEND MANAGEMENT
# =====================================================

@app.route("/admin/legends")
@admin_required
def admin_legends():
    legends = Legend.query.order_by(Legend.name).all()
    return render_template("admin_legends.html", legends=legends)


def save_legend_from_form(legend):
    """Validate form data and update a Legend object."""

    name = request.form.get("name", "").strip()
    nationality = request.form.get("nationality", "").strip()
    position = request.form.get("position", "").strip().upper()
    picture_url = request.form.get("picture_url", "").strip()
    peak_season = request.form.get("peak_season", "").strip()
    legendary_team = request.form.get("legendary_team", "").strip()

    if not name:
        raise ValueError("Legend name is required.")

    if position not in ("PG", "SG", "SF", "PF", "C"):
        raise ValueError("Please select a valid position.")

    if (len(name) > 100 or len(nationality) > 50
            or len(picture_url) > 500 or len(peak_season) > 20
            or len(legendary_team) > 100):
        raise ValueError("One or more text fields are too long.")

    existing = Legend.query.filter(
        Legend.name == name,
        Legend.id != legend.id
    ).first()

    if existing:
        raise ValueError("A legend with this name already exists.")

    ratings = {}
    for field in ("rating", "offense", "defense"):
        value = int(request.form.get(field, "90"))
        if not 0 <= value <= 100:
            raise ValueError(f"{field} must be between 0 and 100.")
        ratings[field] = value

    statistics = {}
    for field in (
        "points_per_game", "assists_per_game",
        "rebounds_per_game", "blocks_per_game",
        "steals_per_game", "fg_percentage"
    ):
        value = float(request.form.get(field, "0"))
        if not math.isfinite(value) or not 0 <= value <= 100:
            raise ValueError(f"{field} must be between 0 and 100.")
        statistics[field] = value

    legend.name = name
    legend.nationality = nationality
    legend.position = position
    legend.picture_url = picture_url
    legend.peak_season = peak_season
    legend.legendary_team = legendary_team

    for field, value in {**ratings, **statistics}.items():
        setattr(legend, field, value)


@app.route("/admin/legends/add", methods=["GET", "POST"])
@admin_required
def admin_add_legend():
    if request.method == "POST":
        legend = Legend()

        try:
            save_legend_from_form(legend)
            db.session.add(legend)
            db.session.commit()
        except (ValueError, TypeError, IntegrityError) as error:
            db.session.rollback()
            flash(f"Could not add legend: {error}", "danger")
            return redirect(url_for("admin_add_legend"))

        flash("Legend added successfully!", "success")
        return redirect(url_for("admin_legends"))

    return render_template("admin_legend_form.html", legend=None)


@app.route("/admin/legends/<int:legend_id>/edit",
           methods=["GET", "POST"])
@admin_required
def admin_edit_legend(legend_id):
    legend = db.get_or_404(Legend, legend_id)

    if request.method == "POST":
        try:
            save_legend_from_form(legend)
            db.session.commit()
        except (ValueError, TypeError, IntegrityError) as error:
            db.session.rollback()
            flash(f"Could not update legend: {error}", "danger")
            return redirect(
                url_for("admin_edit_legend", legend_id=legend_id)
            )

        flash("Legend updated successfully!", "success")
        return redirect(url_for("admin_legends"))

    return render_template("admin_legend_form.html", legend=legend)


@app.route("/admin/legends/<int:legend_id>/delete",
           methods=["POST"])
@admin_required
def admin_delete_legend(legend_id):
    legend = db.get_or_404(Legend, legend_id)
    name = legend.name

    db.session.delete(legend)
    db.session.commit()

    flash(f"{name} was deleted.", "success")
    return redirect(url_for("admin_legends"))


# =====================================================
# ADMIN - USER MANAGEMENT
# =====================================================

from flask import session
import secrets


def admin_user_csrf_token():
    if "admin_user_csrf" not in session:
        session["admin_user_csrf"] = secrets.token_urlsafe(32)
    return session["admin_user_csrf"]


def verify_admin_user_csrf():
    supplied = request.form.get("csrf_token", "")
    expected = session.get("admin_user_csrf", "")

    if not expected or not secrets.compare_digest(supplied, expected):
        abort(400, description="Invalid form security token.")


@app.route("/admin/users")
@admin_required
def admin_users():
    users = User.query.order_by(User.username).all()

    return render_template(
        "admin_users.html",
        users=users,
        csrf_token=admin_user_csrf_token()
    )


@app.route("/admin/users/<int:user_id>/edit",
           methods=["GET", "POST"])
@admin_required
def admin_edit_user(user_id):
    user = db.get_or_404(User, user_id)

    if request.method == "POST":
        verify_admin_user_csrf()

        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        role = request.form.get("role", "").strip()

        if not username or not email:
            flash("Username and email are required.", "danger")
            return redirect(url_for("admin_edit_user", user_id=user.id))

        if len(username) > 50 or len(email) > 120:
            flash("Username or email is too long.", "danger")
            return redirect(url_for("admin_edit_user", user_id=user.id))

        if "@" not in email or email.startswith("@") or email.endswith("@"):
            flash("Please enter a valid email address.", "danger")
            return redirect(url_for("admin_edit_user", user_id=user.id))

        if role not in ("user", "admin"):
            flash("Invalid account role.", "danger")
            return redirect(url_for("admin_edit_user", user_id=user.id))

        if user.id == current_user.id and role != "admin":
            flash("You cannot remove your own admin access.", "danger")
            return redirect(url_for("admin_edit_user", user_id=user.id))

        existing_username = User.query.filter(
            User.username == username,
            User.id != user.id
        ).first()

        if existing_username:
            flash("This username is already taken.", "danger")
            return redirect(url_for("admin_edit_user", user_id=user.id))

        existing_email = User.query.filter(
            User.email == email,
            User.id != user.id
        ).first()

        if existing_email:
            flash("This email is already registered.", "danger")
            return redirect(url_for("admin_edit_user", user_id=user.id))

        user.username = username
        user.email = email
        user.role = role

        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("Username or email already exists.", "danger")
            return redirect(url_for("admin_edit_user", user_id=user.id))

        flash("User updated successfully!", "success")
        return redirect(url_for("admin_users"))

    return render_template(
        "admin_user_form.html",
        user=user,
        csrf_token=admin_user_csrf_token()
    )


@app.route("/admin/users/<int:user_id>/delete",
           methods=["POST"])
@admin_required
def admin_delete_user(user_id):
    verify_admin_user_csrf()

    user = db.get_or_404(User, user_id)

    if user.id == current_user.id:
        flash("You cannot delete your own account.", "danger")
        return redirect(url_for("admin_users"))

    if user.role == "admin" and User.query.filter_by(role="admin").count() <= 1:
        flash("You cannot delete the last administrator.", "danger")
        return redirect(url_for("admin_users"))

    username = user.username

    try:
        # Delete dependent records before deleting the account.
        DraftRun.query.filter_by(user_id=user.id).delete()
        UserAchievement.query.filter_by(user_id=user.id).delete()
        UserTitle.query.filter_by(user_id=user.id).delete()

        db.session.delete(user)
        db.session.commit()

    except IntegrityError:
        db.session.rollback()
        flash(
            "This account has other related records and could not be deleted.",
            "danger"
        )
        return redirect(url_for("admin_users"))

    flash(f"User {username} was deleted.", "success")
    return redirect(url_for("admin_users"))




@app.route("/api/profile/titles/equip", methods=["POST"])
@login_required
def equip_profile_title():
    sync_grid_achievements(current_user.id, BasketballGridGame.query.filter_by(user_id=current_user.id).first())
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


# =====================================================
# OTHER GAMES PAGE
# =====================================================

@app.route("/other-games")
def other_games():
    return render_template("other_games.html")


# =====================================================
# HIGHER OR LOWER — CLASSIC ENDLESS MODE
# =====================================================

# Available statistics and their labels.
HL_STATISTICS = {
    "rating": "Overall Rating",
    "points_per_game": "Points Per Game",
    "assists_per_game": "Assists Per Game",
    "rebounds_per_game": "Rebounds Per Game",
    "steals_per_game": "Steals Per Game",
    "blocks_per_game": "Blocks Per Game",
    "fg_percentage": "Field Goal Percentage"
}

HL_SESSION_KEY = "higher_or_lower_game"


# =====================================================
# HIGHER OR LOWER — ACHIEVEMENTS
# =====================================================

HL_ACHIEVEMENTS = {
    "hl_first_game": {
        "name": "First Comparison",
        "description": "Complete your first Higher or Lower game.",
        "title": "First Comparison"
    },
    "hl_streak_5": {
        "name": "Getting Warm",
        "description": "Reach a streak of 5.",
        "title": "Getting Warm"
    },
    "hl_streak_10": {
        "name": "On Fire",
        "description": "Reach a streak of 10.",
        "title": "On Fire"
    },
    "hl_streak_20": {
        "name": "EuroLeague Expert",
        "description": "Reach a streak of 20.",
        "title": "EuroLeague Expert"
    },
    "hl_correct_50": {
        "name": "Sharp Shooter",
        "description": "Make 50 correct guesses.",
        "title": "Sharp Shooter"
    },
    "hl_games_25": {
        "name": "Dedicated Analyst",
        "description": "Complete 25 games.",
        "title": "Dedicated Analyst"
    }
}


def hl_get_stats():
    """Get or create the logged-in user's game statistics."""
    stats = HigherLowerStats.query.filter_by(
        user_id=current_user.id
    ).first()

    if stats is None:
        stats = HigherLowerStats(user_id=current_user.id)
        db.session.add(stats)
        db.session.flush()

    return stats


def hl_unlock_achievements(stats):
    """Add newly earned achievements to the existing user system."""
    eligible = set()

    if stats.total_games >= 1:
        eligible.add("hl_first_game")

    if stats.best_streak >= 5:
        eligible.add("hl_streak_5")

    if stats.best_streak >= 10:
        eligible.add("hl_streak_10")

    if stats.best_streak >= 20:
        eligible.add("hl_streak_20")

    if stats.total_correct >= 50:
        eligible.add("hl_correct_50")

    if stats.total_games >= 25:
        eligible.add("hl_games_25")

    existing = {
        item.achievement_key
        for item in UserAchievement.query.filter_by(
            user_id=current_user.id
        ).all()
    }

    unlocked = []

    for key in sorted(eligible - existing):
        db.session.add(UserAchievement(
            user_id=current_user.id,
            achievement_key=key
        ))

        unlocked.append({
            "key": key,
            "name": HL_ACHIEVEMENTS[key]["name"]
        })

    return unlocked

# =====================================================
# HELPERS
# =====================================================

def hl_valid_players(players, stat_key):
    """
    Return players with valid, positive values
    for the selected statistic.
    """

    valid = []

    for player in players:

        value = getattr(player, stat_key, None)

        if value is None:
            continue

        try:
            value = float(value)
        except (TypeError, ValueError):
            continue

        if value <= 0:
            continue

        valid.append(player)

    return valid


def hl_available_statistics(players):
    """
    Find statistics that have at least two
    different positive values in the database.
    """

    available = []

    for stat_key in HL_STATISTICS:

        valid = hl_valid_players(players, stat_key)

        distinct_values = {
            float(getattr(player, stat_key))
            for player in valid
        }

        if len(distinct_values) >= 2:
            available.append(stat_key)

    return available


def hl_choose_pair(players, stat_key, first_id=None):
    """
    Select two different players whose values
    for the chosen statistic are not equal.

    If possible, use first_id as the first player.
    """

    eligible = hl_valid_players(players, stat_key)

    if len(eligible) < 2:
        raise ValueError(
            "Not enough players with valid statistics."
        )

    first = None

    if first_id is not None:

        first = next(
            (
                player for player in eligible
                if player.id == first_id
            ),
            None
        )

    if first is None:
        first = random.choice(eligible)

    first_value = float(
        getattr(first, stat_key)
    )

    possible_second = [
        player
        for player in eligible
        if (
            player.id != first.id
            and float(getattr(player, stat_key)) != first_value
        )
    ]

    # A carried-over player might have a value
    # that matches every other eligible player.
    if not possible_second:

        possible_first = [
            player
            for player in eligible
            if any(
                other.id != player.id
                and float(getattr(other, stat_key))
                != float(getattr(player, stat_key))
                for other in eligible
            )
        ]

        if not possible_first:
            raise ValueError(
                "No valid player comparisons are available."
            )

        first = random.choice(possible_first)

        first_value = float(
            getattr(first, stat_key)
        )

        possible_second = [
            player
            for player in eligible
            if (
                player.id != first.id
                and float(getattr(player, stat_key))
                != first_value
            )
        ]

    second = random.choice(possible_second)

    return first, second


def hl_format_value(value, stat_key):
    """
    Format a statistic for display.
    """

    if value is None:
        return "—"

    if stat_key == "rating":
        return str(int(value))

    if stat_key == "fg_percentage":
        return f"{float(value):.1f}%"

    return f"{float(value):.1f}"


def hl_player_data(player):
    """
    Return public player information.

    The hidden statistic is NOT included here.
    """

    return {
        "id": player.id,
        "name": player.name,
        "team": (
            player.team.name
            if player.team
            else "EuroLeague"
        ),
        "picture_url": player.picture_url or ""
    }


def hl_make_round(players, mode, streak, first_id=None):
    """
    Generate a new comparison.

    mode can be a specific statistic or 'random'.
    """

    available = hl_available_statistics(players)

    if not available:
        raise ValueError(
            "The database needs at least two players "
            "with different valid statistics."
        )

    if mode == "random":
        stat_key = random.choice(available)
    else:
        stat_key = mode

        if stat_key not in available:
            raise ValueError(
                "Not enough valid player data "
                "for this statistic."
            )

    first, second = hl_choose_pair(
        players,
        stat_key,
        first_id=first_id
    )

    return {
        "mode": mode,
        "stat": stat_key,
        "first_id": first.id,
        "second_id": second.id,
        "streak": streak,
        "active": True
    }


def hl_public_round(state, players_by_id, best):
    """
    Prepare the game data sent to JavaScript.

    Only the first player's statistic is visible.
    """

    first = players_by_id[state["first_id"]]
    second = players_by_id[state["second_id"]]

    stat_key = state["stat"]

    first_data = hl_player_data(first)

    first_data["value_display"] = hl_format_value(
        getattr(first, stat_key),
        stat_key
    )

    second_data = hl_player_data(second)

    return {
        "stat_key": stat_key,
        "stat_label": HL_STATISTICS[stat_key],
        "round": state["streak"] + 1,
        "streak": state["streak"],
        "best": best,
        "player_one": first_data,
        "player_two": second_data
    }


# =====================================================
# PAGE ROUTE
# =====================================================

@app.route("/games/higher-or-lower")
def higher_or_lower():
    return render_template("higher_or_lower.html")


# =====================================================
# START A NEW GAME
# =====================================================

@app.route(
    "/api/games/higher-or-lower/start",
    methods=["POST"]
)

# =====================================================
# HIGHER OR LOWER — START
# =====================================================

@app.route(
    "/api/games/higher-or-lower/start",
    methods=["POST"]
)
@login_required
def hl_start():
    data = request.get_json(silent=True) or {}
    mode = data.get("stat", "random")

    if mode != "random" and mode not in HL_STATISTICS:
        return jsonify({"error": "Invalid statistic."}), 400

    players = Player.query.all()

    try:
        state = hl_make_round(players, mode, streak=0)
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    stats = hl_get_stats()

    # Starting a new run abandons any previous unfinished run.
    stats.current_streak = 0
    db.session.commit()

    session[HL_SESSION_KEY] = state

    players_by_id = {p.id: p for p in players}

    return jsonify(
        hl_public_round(
            state,
            players_by_id,
            stats.best_streak or 0
        )
    )


# =====================================================
# HIGHER OR LOWER — GUESS
# =====================================================

@app.route(
    "/api/games/higher-or-lower/guess",
    methods=["POST"]
)
@login_required
def hl_guess():
    data = request.get_json(silent=True) or {}
    guess = data.get("guess")

    if guess not in ("higher", "lower"):
        return jsonify({"error": "Invalid guess."}), 400

    state = session.get(HL_SESSION_KEY)

    if not state or not state.get("active"):
        return jsonify({
            "error": "No active game. Start a new game."
        }), 400

    players = Player.query.all()
    players_by_id = {p.id: p for p in players}

    first = players_by_id.get(state["first_id"])
    second = players_by_id.get(state["second_id"])

    if first is None or second is None:
        session.pop(HL_SESSION_KEY, None)
        return jsonify({
            "error": "Player data changed. Restart the game."
        }), 409

    stat_key = state["stat"]

    first_value = float(getattr(first, stat_key))
    second_value = float(getattr(second, stat_key))

    correct_answer = (
        "higher" if second_value > first_value else "lower"
    )

    correct = guess == correct_answer

    revealed_value = hl_format_value(
        second_value,
        stat_key
    )

    stats = hl_get_stats()

    # Every submitted guess counts.
    stats.total_guesses = (stats.total_guesses or 0) + 1

    if correct:
        new_streak = state["streak"] + 1

        # Prepare the next round before saving the answer.
        try:
            next_state = hl_make_round(
                players,
                state["mode"],
                streak=new_streak,
                first_id=second.id
            )
        except ValueError:
            db.session.rollback()
            return jsonify({
                "error": "Cannot generate the next comparison."
            }), 409

        stats.total_correct = (stats.total_correct or 0) + 1
        stats.current_streak = new_streak
        stats.best_streak = max(
            stats.best_streak or 0,
            new_streak
        )

        unlocked = hl_unlock_achievements(stats)
        best = stats.best_streak

        db.session.commit()
        session[HL_SESSION_KEY] = next_state

        return jsonify({
            "correct": True,
            "revealed_value": revealed_value,
            "streak": new_streak,
            "best": best,
            "new_achievements": unlocked,
            "next_round": hl_public_round(
                next_state,
                players_by_id,
                best
            )
        })

    # One incorrect guess ends the run.
    final_streak = state["streak"]

    stats.total_games = (stats.total_games or 0) + 1
    stats.current_streak = 0
    stats.best_streak = max(
        stats.best_streak or 0,
        final_streak
    )

    unlocked = hl_unlock_achievements(stats)
    best = stats.best_streak

    db.session.commit()

    state["active"] = False
    session[HL_SESSION_KEY] = state

    return jsonify({
        "correct": False,
        "game_over": True,
        "revealed_value": revealed_value,
        "correct_answer": correct_answer,
        "streak": final_streak,
        "best": best,
        "new_achievements": unlocked
    })






# =====================================================
# HIGHER OR LOWER — PROFILE STATISTICS
# =====================================================

@app.route("/api/games/higher-or-lower/my-stats")
@login_required
def hl_my_stats():
    stats = HigherLowerStats.query.filter_by(
        user_id=current_user.id
    ).first()

    achievements = UserAchievement.query.filter_by(
        user_id=current_user.id
    ).all()

    unlocked = {
        achievement.achievement_key
        for achievement in achievements
    }

    if stats is None:
        best = games = correct = guesses = 0
    else:
        best = stats.best_streak or 0
        games = stats.total_games or 0
        correct = stats.total_correct or 0
        guesses = stats.total_guesses or 0

    accuracy = round(
        correct / guesses * 100, 1
    ) if guesses else 0

    return jsonify({
        "best_streak": best,
        "total_games": games,
        "total_correct": correct,
        "total_guesses": guesses,
        "accuracy": accuracy,
        "achievements": [
            {
                "key": key,
                "name": definition["name"],
                "description": definition["description"],
                "unlocked": key in unlocked
            }
            for key, definition in HL_ACHIEVEMENTS.items()
        ]
    })





# Register Guess the Player models and routes BEFORE db.create_all().
from guess_the_player_backend import register_guess_the_player

GuessPlayerStats = register_guess_the_player(
    app, db, Player, User, UserAchievement
)


# Initialize database only when running app.py directly.
# This prevents migration scripts from triggering initialization.
if __name__ == "__main__":
    initialize_database()
    app.run(debug=True)