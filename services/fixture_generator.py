# ============================================================
# EUROLEAGUE FIXTURE GENERATOR
# ============================================================

import random


def generate_round_robin(team_ids, seed=None):
    """
    Generate a double round-robin schedule.

    Every team plays every other team twice:
    once at home and once away.

    Returns:
        [
            [(home_id, away_id), ...],
            ...
        ]
    """

    teams = list(team_ids)

    if len(teams) < 2 or len(teams) % 2 != 0:
        raise ValueError(
            "The number of teams must be even and at least 2."
        )

    if len(set(teams)) != len(teams):
        raise ValueError("Duplicate team IDs are not allowed.")

    rng = random.Random(seed)
    rng.shuffle(teams)

    number_of_teams = len(teams)
    first_half = []

    # Circle method
    for round_index in range(number_of_teams - 1):

        matches = []

        for i in range(number_of_teams // 2):

            team_a = teams[i]
            team_b = teams[number_of_teams - 1 - i]

            # Alternate home and away
            if i == 0:
                if round_index % 2 == 0:
                    home, away = team_a, team_b
                else:
                    home, away = team_b, team_a
            elif (round_index + i) % 2 == 0:
                home, away = team_a, team_b
            else:
                home, away = team_b, team_a

            matches.append((home, away))

        first_half.append(matches)

        # Keep the first team fixed
        teams = (
            [teams[0]]
            + [teams[-1]]
            + teams[1:-1]
        )

    # Reverse home and away for the second half
    second_half = []

    for matches in first_half:
        reverse_matches = [
            (away, home)
            for home, away in matches
        ]

        second_half.append(reverse_matches)

    return first_half + second_half