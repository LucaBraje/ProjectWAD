"""Draft Mode game calculations, extracted without changing the algorithms."""
import math
import random
from models import Player, Team, Legend

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

