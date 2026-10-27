import math
import random

POSITIONS = ("PG", "SG", "SF", "PF", "C")


def _number(value, default=0.0):
    return float(default if value is None else value)


def _clamp(value, low, high):
    return max(low, min(high, value))


def calculate_fantasy_points(stats):
    missed = stats["field_goals_attempted"] - stats["field_goals_made"]
    return round(
        stats["points"] + stats["rebounds"] * 1.2
        + stats["assists"] * 1.5 + stats["steals"] * 2
        + stats["blocks"] * 2 - stats["turnovers"]
        - missed * 0.5, 2
    )


def player_strength(player):
    rating = _number(player.rating, 70)
    offense = _number(player.offense, 70)
    defense = _number(player.defense, 70)
    ppg = _clamp(_number(player.points_per_game), 0, 35)
    return 0.42 * rating + 0.24 * offense + 0.24 * defense + 0.35 * ppg


def team_strength(players):
    ranked = sorted(players, key=player_strength, reverse=True)
    if len(ranked) < 5:
        raise ValueError("Each team needs at least five players.")
    core = ranked[:8]
    return sum(player_strength(p) for p in core) / len(core)


def distribute_total(total, weights, rng):
    """Randomized proportional allocation, with an exact integer total."""
    if not weights:
        raise ValueError("No players available for distribution.")
    if total < 0:
        raise ValueError("Total cannot be negative.")
    positive = [max(0.0, float(w)) for w in weights]
    if not any(positive):
        positive = [1.0] * len(weights)
    draws = [rng.gammavariate(max(0.05, w), 1.0) if w else 0.0
             for w in positive]
    if not any(draws):
        draws = positive
    scale = total / sum(draws)
    exact = [d * scale for d in draws]
    values = [math.floor(v) for v in exact]
    remaining = total - sum(values)
    order = sorted(range(len(values)),
                   key=lambda i: (exact[i] - values[i], rng.random()),
                   reverse=True)
    for i in order[:remaining]:
        values[i] += 1
    return values


def _rotation(players, rng, overtime):
    """Choose up to 12 players and allocate 200 + 25/OT minutes."""
    ranked = sorted(players, key=player_strength, reverse=True)[:12]
    if len(ranked) < 5:
        raise ValueError("Each team needs at least five players.")

    # Most teams use 9-11 players; a 12th player may appear occasionally.
    rotation_size = min(len(ranked), rng.choices([9, 10, 11, 12],
                                                weights=[20, 45, 30, 5])[0])
    active = ranked[:rotation_size]
    strengths = [player_strength(p) for p in active]
    peak = max(strengths)
    # Strongest players have priority, but the distribution isn't deterministic.
    minute_weights = [
        (0.45 + (s / peak) ** 5) * (1.15 if i < 5 else 0.65)
        * rng.uniform(0.87, 1.13)
        for i, s in enumerate(strengths)
    ]
    total_minutes = 200 + 25 * overtime
    cap = 40 + 5 * overtime
    minutes = [0] * len(active)

    # Allocate each player-minute, respecting the game-duration cap.
    for _ in range(total_minutes):
        available = [i for i, m in enumerate(minutes) if m < cap]
        choices = [minute_weights[i] / (1 + (minutes[i] / 22) ** 3)
                   for i in available]
        chosen = rng.choices(available, weights=choices, k=1)[0]
        minutes[chosen] += 1

    return active, minutes


def _team_profile(players):
    core = sorted(players, key=player_strength, reverse=True)[:8]
    if len(core) < 5:
        raise ValueError("Each team needs at least five players.")
    offense = sum(_number(p.offense, 70) for p in core) / len(core)
    defense = sum(_number(p.defense, 70) for p in core) / len(core)
    overall = sum(_number(p.rating, 70) for p in core) / len(core)
    depth = sum(player_strength(p) for p in core) / len(core)
    covered = len({p.position for p in core if p.position in POSITIONS})
    balance = (covered - 5) * 0.6  # Small penalty for missing positions.
    return {"offense": offense, "defense": defense,
            "overall": overall, "depth": depth, "balance": balance}


def _game_scores(home_players, away_players, rng):
    home = _team_profile(home_players)
    away = _team_profile(away_players)
    # Shared pace makes the two teams' scores somewhat correlated.
    pace_shift = rng.gauss(0, 4.0)
    home_attack = (home["offense"] - away["defense"]) * 0.32
    away_attack = (away["offense"] - home["defense"]) * 0.32
    home_quality = (home["depth"] - away["depth"]) * 0.16
    away_quality = -home_quality
    home_expected = 79.5 + pace_shift + home_attack + home_quality + 2.0 + home["balance"]
    away_expected = 79.5 + pace_shift + away_attack + away_quality + away["balance"]
    home_score = max(50, round(rng.gauss(home_expected, 8.2)))
    away_score = max(50, round(rng.gauss(away_expected, 8.2)))
    overtime = 0
    while home_score == away_score:
        overtime += 1
        home_score += max(2, round(rng.gauss(9.5, 3.0)))
        away_score += max(2, round(rng.gauss(9.5, 3.0)))
        if overtime >= 10 and home_score == away_score:
            home_score += 1 if rng.random() < 0.5 else 0
            away_score += 1 if home_score == away_score else 0
    return home_score, away_score, overtime


def _allocate_shooting(points, fg_pct, rng):
    """Approximate FGM/FGA without claiming to model actual shot types."""
    if points <= 0:
        return 0, rng.randint(0, 2)
    # FGM must not exceed points/2, consistent with admin validation.
    # Remaining points implicitly represent 3PT bonus points and free throws.
    max_makes = points // 2
    if max_makes == 0:
        return 0, rng.randint(0, 2)
    target = points / rng.uniform(2.35, 3.0)
    makes = int(_clamp(round(rng.gauss(target, 0.75)), 0, max_makes))
    pct = _clamp(fg_pct / 100, 0.30, 0.68)
    attempts = max(makes, round(makes / pct + rng.gauss(0, 1.2)))
    if makes == 0:
        attempts = max(attempts, rng.randint(0, 3))
    return makes, attempts


def simulate_team_players(players, team_score, rng, overtime=0,
                          opponent_defense=70):
    active, minutes = _rotation(players, rng, overtime)
    # Each player's game-to-game scoring opportunity varies independently.
    scoring_weights = []
    for p, m in zip(active, minutes):
        ppg = _clamp(_number(p.points_per_game), 0, 35)
        offense = _number(p.offense, 70)
        usage = max(2.0, 0.68 * ppg + 0.16 * (offense - 55) + 2.0)
        scoring_weights.append(
            usage * (m / 25) * rng.lognormvariate(0, 0.30)
            * _clamp(1 - (opponent_defense - 70) * 0.003, 0.8, 1.2)
        )
    # A second randomized allocation gives meaningful hot/cold games.
    points = distribute_total(team_score, scoring_weights, rng)

    # Team-wide opportunities: individual stats should not be unbounded.
    rebounds_total = max(20, round(rng.gauss(34 + 0.04 * (80 - team_score), 4)))
    assists_total = max(8, min(team_score // 2, round(rng.gauss(team_score * 0.245, 3))))
    steals_total = max(1, round(rng.gauss(7, 2)))
    blocks_total = max(0, round(rng.gauss(3, 1.6)))
    turnovers_total = max(5, round(rng.gauss(12, 2.5)))

    reb_weights, ast_weights, stl_weights, blk_weights, tov_weights = [], [], [], [], []
    for p, m, pts in zip(active, minutes, points):
        factor = m / 25
        pos = p.position
        defense = _number(p.defense, 70)
        reb_weights.append(max(0.2, (_number(p.rebounds_per_game) +
            {"PG": 1.2, "SG": 1.5, "SF": 2.3, "PF": 3.3, "C": 4.2}.get(pos, 2)) * factor))
        ast_weights.append(max(0.2, (_number(p.assists_per_game) +
            {"PG": 3.8, "SG": 1.9, "SF": 1.3, "PF": 0.8, "C": 0.5}.get(pos, 1)) * factor))
        stl_weights.append(max(0.1, (_number(p.steals_per_game) +
            max(0, defense - 55) / 50 + 0.25) * factor))
        blk_weights.append(max(0.05, (_number(p.blocks_per_game) +
            {"PG": 0.05, "SG": 0.08, "SF": 0.18, "PF": 0.45, "C": 0.75}.get(pos, 0.1)
            + max(0, defense - 70) / 100) * factor))
        tov_weights.append(max(0.2, (1 + pts / 13 +
            (1 if pos == "PG" else 0)) * factor))

    rebounds = distribute_total(rebounds_total, reb_weights, rng)
    assists = distribute_total(assists_total, ast_weights, rng)
    steals = distribute_total(steals_total, stl_weights, rng)
    blocks = distribute_total(blocks_total, blk_weights, rng)
    turnovers = distribute_total(turnovers_total, tov_weights, rng)

    results = []
    for i, p in enumerate(active):
        fg_made, fg_attempted = _allocate_shooting(
            points[i], _number(p.fg_percentage, 45), rng)
        stats = {
            "player_id": p.id, "minutes": minutes[i],
            "points": points[i], "rebounds": rebounds[i],
            "assists": assists[i], "steals": steals[i],
            "blocks": blocks[i], "turnovers": turnovers[i],
            "field_goals_made": fg_made,
            "field_goals_attempted": fg_attempted,
        }
        stats["fantasy_points"] = calculate_fantasy_points(stats)
        results.append(stats)
    return results


def simulate_game(home_players, away_players, seed=None):
    """Pure, seed-reproducible game simulation; no database writes."""
    rng = random.Random(seed)
    home_score, away_score, overtime = _game_scores(home_players, away_players, rng)
    home_defense = _team_profile(home_players)["defense"]
    away_defense = _team_profile(away_players)["defense"]
    home_stats = simulate_team_players(home_players, home_score, rng,
                                       overtime, away_defense)
    away_stats = simulate_team_players(away_players, away_score, rng,
                                       overtime, home_defense)
    assert sum(s["points"] for s in home_stats) == home_score
    assert sum(s["points"] for s in away_stats) == away_score
    return {
        "home_score": home_score, "away_score": away_score,
        "overtime": overtime,
        "home_players": home_stats, "away_players": away_stats,
    }
