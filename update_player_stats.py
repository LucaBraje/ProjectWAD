"""Recalculate season averages for players with imported official totals."""


def update_all_player_stats(db, Player):
    updated = 0
    for player in Player.query.all():
        games = player.games_played
        if games is None:
            continue  # Preserve manually entered averages until imported.
        if games < 0:
            raise ValueError(f"Negative games played for player {player.id}")

        totals = ("total_points", "total_assists", "total_rebounds",
                  "total_blocks", "total_steals", "total_turnovers",
                  "total_fgm", "total_fga")
        if any(getattr(player, field) is None for field in totals):
            continue  # Do not overwrite averages using incomplete imports.
        if any(getattr(player, field) < 0 for field in totals):
            raise ValueError(f"Negative totals for player {player.id}")
        if player.total_fgm > player.total_fga:
            raise ValueError(f"FG made exceeds attempts for player {player.id}")

        for total, average in (
            ("total_points", "points_per_game"),
            ("total_assists", "assists_per_game"),
            ("total_rebounds", "rebounds_per_game"),
            ("total_blocks", "blocks_per_game"),
            ("total_steals", "steals_per_game"),
        ):
            setattr(player, average,
                    round(getattr(player, total) / games, 2) if games else 0.0)

        player.fg_percentage = (
            round(player.total_fgm / player.total_fga * 100, 2)
            if player.total_fga else 0.0
        )
        updated += 1

    if updated:
        db.session.commit()
    print(f"Recalculated season averages for {updated} players.")
    return updated
