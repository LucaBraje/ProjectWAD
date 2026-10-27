"""Achievement definitions and unlock logic, extracted unchanged from app.py."""
from extensions import db
from models import DraftRun, UserAchievement

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


