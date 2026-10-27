"""Draft EuroLeague application entry point.

Routes live in routes/, data models in models/, and business logic in services/.
The public `app`, `db`, model names, and legacy helper exports remain available
for scripts that use `from app import ...`.
"""
import os
from flask import Flask
from extensions import db, login_manager
from models import (
    Team, SimulationSeason, SimulationWeek, SimulationGame,
    SimulationPlayerStats, Legend, Player, TeamPicture, User,
    FantasySquad, FantasySquadPlayer, FantasyRoundLineup,
    FantasyRoundScore, HigherLowerStats, DraftRun, UserAchievement, UserTitle,
)
from services.admin_csrf import admin_form_token, valid_admin_form_token
from services.database_init import initialize_database as _initialize_database
from services.fantasy_service import (
    FANTASY_BUDGET, FANTASY_POSITIONS, fantasy_player_price,
    fantasy_current_season, fantasy_squad_editable, fantasy_validate_squad,
    fantasy_get_lineup, fantasy_lineup_editable, fantasy_lock_round_lineups,
    fantasy_default_lineup, fantasy_validate_lineup,
    fantasy_calculate_round_scores, fantasy_delete_round_data,
)
from services.minigame_service import (
    HL_STATISTICS, HL_SESSION_KEY, HL_ACHIEVEMENTS,
    hl_get_stats, hl_unlock_achievements, hl_valid_players,
    hl_available_statistics, hl_choose_pair, hl_format_value,
    hl_player_data, hl_make_round, hl_public_round,
)
from services.draft_service import (
    DRAFT_POSITIONS, POSITION_VALUES, draft_player_positions,
    calculate_draft_rating, opponent_strength, draft_game,
    draft_series, run_draft_season,
)
from services.achievement_service import (
    DRAFT_ACHIEVEMENTS, GRID_ACHIEVEMENTS, PROFILE_TITLES,
    unlock_draft_achievements, sync_grid_achievements,
)
from games.basketball_grid_backend import register_basketball_grid
from games.guess_the_player_backend import register_guess_the_player
from routes import register_routes

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "development-only-change-me")
app.config["ALLOW_SEASON_RESET"] = os.environ.get("ALLOW_SEASON_RESET", "0") == "1"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///draft_euroleague.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)
login_manager.init_app(app)
login_manager.login_view = "login"
login_manager.login_message = "Please log in to access this page."
login_manager.login_message_category = "warning"

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

@app.context_processor
def inject_admin_form_token():
    return {"admin_form_token": admin_form_token}

# Register external minigames before db.create_all() so their tables exist.
BasketballGridGame = register_basketball_grid(app, db, Player, User)
GuessPlayerStats = register_guess_the_player(app, db, Player, User, UserAchievement)

register_routes(
    app,
    schedule_dependencies={
        "fantasy_lock_round_lineups": fantasy_lock_round_lineups,
        "fantasy_calculate_round_scores": fantasy_calculate_round_scores,
        "valid_admin_form_token": valid_admin_form_token,
        "fantasy_delete_round_data": fantasy_delete_round_data,
        "unlock_draft_achievements": unlock_draft_achievements,
        "DRAFT_ACHIEVEMENTS": DRAFT_ACHIEVEMENTS,
        "BasketballGridGame": BasketballGridGame,
    },
)

def initialize_database():
    """Backward-compatible no-argument initialization entry point."""
    return _initialize_database(app)

if __name__ == "__main__":
    initialize_database()
    app.run(debug=True)
