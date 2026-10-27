
"""Guess the Player: register with the existing Flask app before db.create_all()."""

import random
from flask import jsonify, render_template, request, session
from flask_login import current_user, login_required

MAX_GUESSES = 8
SESSION_KEY = "guess_player_classic_v1"

ACHIEVEMENTS = {
    "gp_first_win": ("First Identification", "Win your first Guess the Player game."),
    "gp_five_wins": ("Scout", "Win five Guess the Player games."),
    "gp_twenty_wins": ("Master Scout", "Win twenty Guess the Player games."),
    "gp_first_try": ("Perfect Read", "Identify a player on the first guess."),
    "gp_streak_5": ("Unstoppable Scout", "Win five consecutive games."),
    "gp_games_25": ("Dedicated Scout", "Complete 25 Guess the Player games."),
}


def register_guess_the_player(app, db, Player, User, UserAchievement):

    class GuessPlayerStats(db.Model):
        __tablename__ = "guess_player_stats"

        id = db.Column(db.Integer, primary_key=True)
        user_id = db.Column(
            db.Integer,
            db.ForeignKey("user.id"),
            unique=True,
            nullable=False
        )
        games = db.Column(db.Integer, nullable=False, default=0)
        wins = db.Column(db.Integer, nullable=False, default=0)
        losses = db.Column(db.Integer, nullable=False, default=0)
        current_streak = db.Column(db.Integer, nullable=False, default=0)
        best_streak = db.Column(db.Integer, nullable=False, default=0)
        total_guesses = db.Column(db.Integer, nullable=False, default=0)
        best_win_guesses = db.Column(db.Integer, nullable=True)

    # =====================================================
    # HELPERS
    # =====================================================

    def get_game_state():
        """
        Retrieve the active game only if it belongs
        to the currently logged-in user.

        Prevents different accounts using the same browser
        from sharing guesses.
        """
        state = session.get(SESSION_KEY)

        if state and state.get("user_id") != current_user.id:
            session.pop(SESSION_KEY, None)
            return None

        return state

    def stats_row():
        row = GuessPlayerStats.query.filter_by(
            user_id=current_user.id
        ).first()

        if row is None:
            row = GuessPlayerStats(user_id=current_user.id)
            db.session.add(row)
            db.session.flush()

        return row

    def summary(row):
        if row is None:
            return dict(
                games=0,
                wins=0,
                losses=0,
                current_streak=0,
                best_streak=0,
                total_guesses=0,
                best_win_guesses=None,
                win_rate=0
            )

        return dict(
            games=row.games,
            wins=row.wins,
            losses=row.losses,
            current_streak=row.current_streak,
            best_streak=row.best_streak,
            total_guesses=row.total_guesses,
            best_win_guesses=row.best_win_guesses,
            win_rate=round(row.wins / row.games * 100, 1)
            if row.games else 0
        )

    def player_json(p):
        return {
            "id": p.id,
            "name": p.name,
            "team": p.team.name if p.team else "Unknown",
            "nationality": p.nationality or "Unknown",
            "position": p.position or "Unknown",
            "rating": p.rating,
            "offense": p.offense,
            "defense": p.defense,
            "picture_url": p.picture_url or ""
        }

    def compare(guess, target):
        result = player_json(guess)
        target_data = player_json(target)

        result["correct"] = guess.id == target.id
        result["matches"] = {}

        for field in (
            "team",
            "nationality",
            "position",
            "rating",
            "offense",
            "defense"
        ):
            a = result[field]
            b = target_data[field]

            if field in ("rating", "offense", "defense"):
                result["matches"][field] = {
                    "match": (
                        a is not None
                        and b is not None
                        and a == b
                    ),
                    "direction": (
                        "up" if a is not None and b is not None and a < b
                        else "down" if a is not None and b is not None and a > b
                        else None
                    )
                }
            else:
                result["matches"][field] = {
                    "match": bool(a and b and a == b),
                    "direction": None
                }

        return result

    def unlock(row, guess_count):
        eligible = set()

        if row.wins >= 1:
            eligible.add("gp_first_win")

        if row.wins >= 5:
            eligible.add("gp_five_wins")

        if row.wins >= 20:
            eligible.add("gp_twenty_wins")

        if row.wins and guess_count == 1:
            eligible.add("gp_first_try")

        if row.best_streak >= 5:
            eligible.add("gp_streak_5")

        if row.games >= 25:
            eligible.add("gp_games_25")

        owned = {
            a.achievement_key
            for a in UserAchievement.query.filter_by(
                user_id=current_user.id
            ).all()
        }

        newly_unlocked = eligible - owned

        for key in newly_unlocked:
            db.session.add(
                UserAchievement(
                    user_id=current_user.id,
                    achievement_key=key
                )
            )

        return [
            {"key": key, "name": ACHIEVEMENTS[key][0]}
            for key in sorted(newly_unlocked)
        ]

    # =====================================================
    # GAME PAGE
    # =====================================================

    @app.route("/games/guess-the-player")
    def guess_the_player():
        return render_template("guess_the_player.html")

    # =====================================================
    # PLAYER SEARCH
    # =====================================================

    @app.get("/api/games/guess-the-player/players")
    @login_required
    def gp_players():
        search = request.args.get("q", "").strip()

        query = Player.query

        if search:
            query = query.filter(
                Player.name.ilike(f"%{search}%")
            )

        players = [
            {
                "id": p.id,
                "name": p.name,
                "team": p.team.name if p.team else "",
                "position": p.position,
                "picture_url": p.picture_url or ""
            }
            for p in query.order_by(Player.name).limit(30).all()
        ]

        return jsonify({"players": players})

    # =====================================================
    # START NEW GAME
    # =====================================================

    @app.post("/api/games/guess-the-player/start")
    @login_required
    def gp_start():
        ids = [
            id_
            for (id_,) in db.session.query(Player.id).all()
        ]

        if len(ids) < 2:
            return jsonify({
                "error": "At least two players are needed in the database."
            }), 400

        target_id = random.SystemRandom().choice(ids)

        # FIX: Associate the game with the logged-in user.
        session[SESSION_KEY] = {
            "user_id": current_user.id,
            "target_id": target_id,
            "guesses": [],
            "active": True
        }

        row = GuessPlayerStats.query.filter_by(
            user_id=current_user.id
        ).first()

        return jsonify({
            "remaining": MAX_GUESSES,
            "max_guesses": MAX_GUESSES,
            "stats": summary(row),
            "guesses": [],
            "active": True
        })

    # =====================================================
    # RESTORE GAME STATE
    # =====================================================

    @app.get("/api/games/guess-the-player/state")
    @login_required
    def gp_state():

        # FIX: Only restore games belonging to this account.
        state = get_game_state()

        row = GuessPlayerStats.query.filter_by(
            user_id=current_user.id
        ).first()

        if not state:
            return jsonify({
                "active": False,
                "guesses": [],
                "stats": summary(row),
                "max_guesses": MAX_GUESSES
            })

        target = db.session.get(
            Player,
            state["target_id"]
        )

        if not target:
            session.pop(SESSION_KEY, None)

            return jsonify({
                "active": False,
                "guesses": [],
                "stats": summary(row),
                "max_guesses": MAX_GUESSES
            })

        comparisons = []

        for player_id in state["guesses"]:
            player = db.session.get(Player, player_id)

            if player is not None:
                comparisons.append(compare(player, target))

        data = {
            "active": state["active"],
            "guesses": comparisons,
            "remaining": MAX_GUESSES - len(state["guesses"]),
            "max_guesses": MAX_GUESSES,
            "stats": summary(row)
        }

        if not state["active"]:
            data["answer"] = player_json(target)
            data["won"] = bool(
                state["guesses"]
                and state["guesses"][-1] == target.id
            )

        return jsonify(data)

    # =====================================================
    # SUBMIT GUESS
    # =====================================================

    @app.post("/api/games/guess-the-player/guess")
    @login_required
    def gp_guess():

        # FIX: Reject games belonging to another account.
        state = get_game_state()

        if not state or not state.get("active"):
            return jsonify({
                "error": "Start a new game first."
            }), 409

        payload = request.get_json(silent=True) or {}

        try:
            player_id = int(payload.get("player_id"))
        except (TypeError, ValueError):
            return jsonify({
                "error": "Choose a valid player."
            }), 400

        if player_id in state["guesses"]:
            return jsonify({
                "error": "You already guessed this player."
            }), 400

        player = db.session.get(Player, player_id)
        target = db.session.get(
            Player,
            state["target_id"]
        )

        if player is None:
            return jsonify({
                "error": "Player not found."
            }), 404

        if target is None:
            session.pop(SESSION_KEY, None)

            return jsonify({
                "error": "Player database changed. Start a new game."
            }), 409

        state["guesses"].append(player_id)

        won = player_id == target.id

        ended = (
            won
            or len(state["guesses"]) >= MAX_GUESSES
        )

        unlocked = []

        row = GuessPlayerStats.query.filter_by(
            user_id=current_user.id
        ).first()

        if ended:
            state["active"] = False

            row = stats_row()
            row.games += 1
            row.total_guesses += len(state["guesses"])

            if won:
                row.wins += 1
                row.current_streak += 1

                row.best_streak = max(
                    row.best_streak,
                    row.current_streak
                )

                if (
                    row.best_win_guesses is None
                    or len(state["guesses"]) < row.best_win_guesses
                ):
                    row.best_win_guesses = len(state["guesses"])

            else:
                row.losses += 1
                row.current_streak = 0

            unlocked = unlock(
                row,
                len(state["guesses"]) if won else 0
            )

            db.session.commit()

        session[SESSION_KEY] = state

        result = {
            "guess": compare(player, target),
            "guesses_used": len(state["guesses"]),
            "remaining": MAX_GUESSES - len(state["guesses"]),
            "game_over": ended,
            "won": won,
            "stats": summary(row),
            "new_achievements": unlocked
        }

        if ended:
            result["answer"] = player_json(target)

        return jsonify(result)

    # =====================================================
    # USER STATISTICS AND ACHIEVEMENTS
    # =====================================================

    @app.get("/api/games/guess-the-player/my-stats")
    @login_required
    def gp_my_stats():

        row = GuessPlayerStats.query.filter_by(
            user_id=current_user.id
        ).first()

        owned = {
            a.achievement_key
            for a in UserAchievement.query.filter_by(
                user_id=current_user.id
            ).all()
        }

        return jsonify({
            "stats": summary(row),
            "achievements": [
                {
                    "key": key,
                    "name": name,
                    "description": description,
                    "unlocked": key in owned
                }
                for key, (name, description) in ACHIEVEMENTS.items()
            ]
        })

    return GuessPlayerStats
