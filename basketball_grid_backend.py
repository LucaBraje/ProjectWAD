
"""EuroLeague Basketball Grid: mixed categories, validated against current Player records.
Register before db.create_all(): register_basketball_grid(app, db, Player, User).
Existing basketball_grid_game table and saved boards remain compatible.
"""
import json
import random
from itertools import combinations

from flask import url_for, jsonify, render_template, request
from flask_login import login_required, current_user

MAX_MISTAKES = 3
POSITIONS = ('PG', 'SG', 'SF', 'PF', 'C')

THRESHOLDS = {
    'points_per_game': (5, 10, 15, 20),
    'assists_per_game': (3, 5, 7),
    'rebounds_per_game': (3, 5, 7),
    'steals_per_game': (1, 2),
    'blocks_per_game': (1, 2),
    'rating': (75, 80, 85, 90),
    'offense': (75, 80, 85, 90),
    'defense': (75, 80, 85, 90),
}

LABELS = {
    'points_per_game': 'PPG',
    'assists_per_game': 'APG',
    'rebounds_per_game': 'RPG',
    'steals_per_game': 'SPG',
    'blocks_per_game': 'BPG',
    'rating': 'Rating',
    'offense': 'Offense',
    'defense': 'Defense',
}

RNG = random.SystemRandom()


def register_basketball_grid(app, db, Player, User):

    # ==========================================
    # DATABASE MODEL
    # ==========================================

    class BasketballGridGame(db.Model):
        __tablename__ = 'basketball_grid_game'

        id = db.Column(db.Integer, primary_key=True)
        user_id = db.Column(
            db.Integer,
            db.ForeignKey('user.id'),
            nullable=False,
            unique=True
        )
        board_json = db.Column(db.Text, nullable=False, default='{}')
        games = db.Column(db.Integer, nullable=False, default=0)
        wins = db.Column(db.Integer, nullable=False, default=0)
        losses = db.Column(db.Integer, nullable=False, default=0)
        best_correct = db.Column(db.Integer, nullable=False, default=0)

    def record():
        row = BasketballGridGame.query.filter_by(
            user_id=current_user.id
        ).first()

        if row is None:
            row = BasketballGridGame(
                user_id=current_user.id,
                board_json='{}'
            )
            db.session.add(row)
            db.session.flush()

        return row

    def stats(row):
        return {
            'games': row.games,
            'wins': row.wins,
            'losses': row.losses,
            'best_correct': row.best_correct,
            'win_rate': round(
                100 * row.wins / row.games, 1
            ) if row.games else 0
        }

    def load_board(row):
        try:
            return json.loads(row.board_json or '{}')
        except (TypeError, ValueError):
            return {}

    # ==========================================
    # PLAYER AND CATEGORY MATCHING
    # ==========================================

    def positions(player):
        return {
            part.strip().upper()
            for part in (player.position or '')
                .replace(',', '/')
                .split('/')
        }

    def matches(player, category):
        kind = category['type']
        value = category['value']

        if kind == 'team':
            return player.team_id == value

        if kind == 'position':
            return value in positions(player)

        if kind == 'nationality':
            return (
                (player.nationality or '').strip().casefold()
                == str(value).casefold()
            )

        if kind == 'threshold':
            number = getattr(
                player, category['field'], None
            )
            return (
                number is not None
                and float(number) >= value
            )

        return False

    def candidate_categories(players):
        teams = {}
        nationalities = {}

        for player in players:
            if player.team_id is not None and player.team:
                teams[player.team_id] = player.team.name

            if player.nationality and player.nationality.strip():
                nationality = player.nationality.strip()
                nationalities[
                    nationality.casefold()
                ] = nationality

        result = [
            {
                'type': 'team',
                'value': team_id,
                'label': name
            }
            for team_id, name in teams.items()
        ]

        result += [
            {
                'type': 'position',
                'value': position,
                'label': position
            }
            for position in POSITIONS
        ]

        result += [
            {
                'type': 'nationality',
                'value': name,
                'label': name
            }
            for name in nationalities.values()
        ]

        for field, thresholds in THRESHOLDS.items():
            for minimum in thresholds:
                result.append({
                    'type': 'threshold',
                    'field': field,
                    'value': minimum,
                    'label': f'{minimum}+ {LABELS[field]}'
                })

        return [
            (
                category,
                {
                    player.id
                    for player in players
                    if matches(player, category)
                }
            )
            for category in result
            if sum(
                matches(player, category)
                for player in players
            ) >= 3
        ]

    # ==========================================
    # GRID GENERATION
    # ==========================================

    def solvable(choices):
        rows, columns = choices[:3], choices[3:]

        cell_options = [
            row[1] & column[1]
            for row in rows
            for column in columns
        ]

        if any(not options for options in cell_options):
            return False

        ordered = sorted(cell_options, key=len)
        used = set()

        def assign(index):
            if index == 9:
                return True

            for player_id in ordered[index] - used:
                used.add(player_id)

                if assign(index + 1):
                    return True

                used.remove(player_id)

            return False

        return assign(0)

    def generate_board():
        players = Player.query.all()
        candidates = candidate_categories(players)

        if len(candidates) < 6:
            return None

        for _ in range(2500):
            picked = RNG.sample(candidates, 6)

            if len({
                (
                    item[0]['type'],
                    item[0].get(
                        'field',
                        item[0]['value']
                    )
                )
                for item in picked
            }) < 6:
                continue

            if len({
                item[0]['type']
                for item in picked
            }) < 3:
                continue

            if not solvable(picked):
                continue

            return {
                'rows': [
                    item[0] for item in picked[:3]
                ],
                'columns': [
                    item[0] for item in picked[3:]
                ],
                'cells': [None] * 9,
                'mistakes': 0,
                'max_mistakes': MAX_MISTAKES,
                'finished': False,
                'won': False
            }

        # Fallback to team x position grid.
        team_categories = [
            item for item in candidates
            if item[0]['type'] == 'team'
        ]

        position_categories = [
            item for item in candidates
            if item[0]['type'] == 'position'
        ]

        RNG.shuffle(team_categories)
        RNG.shuffle(position_categories)

        for teams in combinations(team_categories, 3):
            for selected_positions in combinations(
                position_categories, 3
            ):
                picked = (
                    list(selected_positions) + list(teams)
                )

                if solvable(picked):
                    return {
                        'rows': [
                            item[0]
                            for item in selected_positions
                        ],
                        'columns': [
                            item[0] for item in teams
                        ],
                        'cells': [None] * 9,
                        'mistakes': 0,
                        'max_mistakes': MAX_MISTAKES,
                        'finished': False,
                        'won': False
                    }

        return None

    def axes(board):
        if 'rows' in board and 'columns' in board:
            return board['rows'], board['columns']

        return (
            [
                {
                    'type': 'position',
                    'value': position,
                    'label': position
                }
                for position in board.get('positions', [])
            ],
            [
                {
                    'type': 'team',
                    'value': team['id'],
                    'label': team['name']
                }
                for team in board.get('teams', [])
            ]
        )

    # ==========================================
    # NATIONALITY FLAGS
    # ==========================================

    def flag_code(country):
        aliases = {
            'usa': 'US',
            'united states': 'US',
            'american': 'US',
            'uk': 'GB',
            'united kingdom': 'GB',
            'british': 'GB',
            'greece': 'GR',
            'greek': 'GR',
            'serbia': 'RS',
            'serbian': 'RS',
            'france': 'FR',
            'french': 'FR',
            'spain': 'ES',
            'spanish': 'ES',
            'turkey': 'TR',
            'türkiye': 'TR',
            'turkiye': 'TR',
            'turkish': 'TR',
            'germany': 'DE',
            'german': 'DE',
            'italy': 'IT',
            'italian': 'IT',
            'lithuania': 'LT',
            'lithuanian': 'LT',
            'latvia': 'LV',
            'latvian': 'LV',
            'croatia': 'HR',
            'croatian': 'HR',
            'slovenia': 'SI',
            'slovenian': 'SI',
            'montenegro': 'ME',
            'montenegrin': 'ME',
            'bosnia and herzegovina': 'BA',
            'bosnian': 'BA',
            'north macedonia': 'MK',
            'macedonian': 'MK',
            'romania': 'RO',
            'romanian': 'RO',
            'israel': 'IL',
            'israeli': 'IL',
            'canada': 'CA',
            'canadian': 'CA',
            'australia': 'AU',
            'australian': 'AU',
            'brazil': 'BR',
            'brazilian': 'BR',
            'argentina': 'AR',
            'argentinian': 'AR',
            'georgia': 'GE',
            'georgian': 'GE',
            'ukraine': 'UA',
            'ukrainian': 'UA',
            'russia': 'RU',
            'russian': 'RU',
            'poland': 'PL',
            'polish': 'PL',
            'czech republic': 'CZ',
            'czechia': 'CZ',
            'czech': 'CZ',
            'finland': 'FI',
            'finnish': 'FI',
            'sweden': 'SE',
            'swedish': 'SE',
            'belgium': 'BE',
            'belgian': 'BE',
            'netherlands': 'NL',
            'dutch': 'NL',
            'senegal': 'SN',
            'senegalese': 'SN',
            'nigeria': 'NG',
            'nigerian': 'NG',
            'cameroon': 'CM',
            'cameroonian': 'CM',
            'angola': 'AO',
            'angolan': 'AO',
            'new zealand': 'NZ',
            'ivory coast': 'CI',
            'cote d ivoire': 'CI',
            'congo': 'CG',
            'dr congo': 'CD',
            'dominican republic': 'DO',
            'puerto rico': 'PR',
            'puerto rican': 'PR',
            'japan': 'JP',
            'japanese': 'JP',
            'china': 'CN',
            'chinese': 'CN',
            'estonia': 'EE',
            'estonian': 'EE',
            'bulgaria': 'BG',
            'bulgarian': 'BG',
            'hungary': 'HU',
            'hungarian': 'HU',
            'cyprus': 'CY',
            'cypriot': 'CY',
            'albania': 'AL',
            'albanian': 'AL',
            'kosovo': 'XK',
            'kosovar': 'XK',
            'switzerland': 'CH',
            'swiss': 'CH',
        }

        return aliases.get(
            str(country).strip().casefold()
        )

    # ==========================================
    # IMAGE URL HANDLING
    # ==========================================

    def resolve_image_url(value):
        """
        Convert a database image path into a browser URL.

        Example:
        teams_logos/Anadolu_Efes_SK_logo.svg

        Result:
        /static/teams_logos/Anadolu_Efes_SK_logo.svg
        """
        if not value:
            return None

        value = str(value).strip()

        if not value:
            return None

        if value.startswith((
            'http://',
            'https://',
            '/',
            'data:'
        )):
            return value

        return url_for(
            'static',
            filename=value.lstrip('/')
        )

    # ==========================================
    # FIXED TEAM LOGO LOOKUP
    # ==========================================

    def get_team_logo(team_id):
        """
        Find a player belonging to the requested team,
        then retrieve image_url from the related Team.

        This uses your existing Player.team relationship.
        """
        if team_id is None:
            return None

        try:
            team_id = int(team_id)
        except (TypeError, ValueError):
            return None

        player = Player.query.filter_by(
            team_id=team_id
        ).first()

        if player is None or player.team is None:
            return None

        image_url = getattr(
            player.team,
            'image_url',
            None
        )

        return resolve_image_url(image_url)

    # ==========================================
    # PREPARE CATEGORIES FOR FRONTEND
    # ==========================================

    def decorate_category(category):
        item = dict(category)

        if item.get('type') == 'team':
            item['image_url'] = get_team_logo(
                item.get('value')
            )

        elif item.get('type') == 'nationality':
            item['flag_code'] = flag_code(
                item['value']
            )

        return item

    def player_cell_image(cell):
        if not cell:
            return cell

        result = dict(cell)

        if 'picture_url' not in result:
            player = db.session.get(
                Player,
                result.get('id')
            )

            result['picture_url'] = (
                resolve_image_url(
                    getattr(player, 'picture_url', None)
                )
                if player else None
            )

        return result

    # ==========================================
    # PUBLIC BOARD RESPONSE
    # ==========================================

    def public_board(board):
        rows, columns = axes(board)

        return {
            'rows': [
                decorate_category(category)
                for category in rows
            ],
            'columns': [
                decorate_category(category)
                for category in columns
            ],
            'cells': [
                player_cell_image(cell)
                for cell in board.get('cells', [])
            ],
            'mistakes': board.get('mistakes', 0),
            'max_mistakes': board.get(
                'max_mistakes',
                MAX_MISTAKES
            ),
            'finished': board.get('finished', False),
            'won': board.get('won', False),
            'gave_up': board.get('gave_up', False),
        }

    # ==========================================
    # FLASK ROUTES
    # ==========================================

    @app.get('/games/basketball-grid')
    @login_required
    def basketball_grid_page():
        return render_template(
            'basketball_grid.html'
        )

    @app.post('/api/games/basketball-grid/start')
    @login_required
    def basketball_grid_start():
        row = record()
        existing = load_board(row)

        if existing and not existing.get('finished'):
            return jsonify({
                'error': (
                    'Finish your current grid before '
                    'starting a new one.'
                )
            }), 409

        board = generate_board()

        if board is None:
            return jsonify({
                'error': (
                    'Not enough compatible player data '
                    'to create a solvable grid.'
                )
            }), 400

        row.board_json = json.dumps(board)
        db.session.commit()

        return jsonify({
            'board': public_board(board),
            'stats': stats(row)
        })

    @app.get('/api/games/basketball-grid/state')
    @login_required
    def basketball_grid_state():
        row = record()
        board = load_board(row)

        result = {
            'board': public_board(board) if board else None,
            'stats': stats(row)
        }

        db.session.commit()
        return jsonify(result)

    @app.get('/api/games/basketball-grid/players')
    @login_required
    def basketball_grid_players():
        query = (
            request.args.get('q') or ''
        ).strip()

        if len(query) < 2:
            return jsonify({'players': []})

        players = (
            Player.query
            .filter(Player.name.ilike(f'%{query}%'))
            .order_by(Player.name)
            .limit(30)
            .all()
        )

        return jsonify({
            'players': [
                {
                    'id': player.id,
                    'name': player.name,
                    'team': (
                        player.team.name
                        if player.team else ''
                    ),
                    'position': player.position or ''
                }
                for player in players
            ]
        })

    @app.post('/api/games/basketball-grid/guess')
    @login_required
    def basketball_grid_guess():
        row = record()
        board = load_board(row)

        if not board or board.get('finished'):
            return jsonify({
                'error': 'Start a new grid first.'
            }), 409

        payload = request.get_json(silent=True) or {}

        try:
            index = int(payload.get('index'))
            player_id = int(payload.get('player_id'))
        except (ValueError, TypeError):
            return jsonify({
                'error': 'Select a cell and a player.'
            }), 400

        if (
            not 0 <= index < 9
            or board['cells'][index] is not None
        ):
            return jsonify({
                'error': 'That cell is not available.'
            }), 400

        player = db.session.get(
            Player,
            player_id
        )

        if player is None:
            return jsonify({
                'error': 'Player not found.'
            }), 404

        if any(
            cell and cell['id'] == player_id
            for cell in board['cells']
        ):
            return jsonify({
                'error': (
                    'You cannot use the same player twice.'
                )
            }), 400

        rows, columns = axes(board)

        correct = (
            matches(player, rows[index // 3])
            and matches(player, columns[index % 3])
        )

        if correct:
            board['cells'][index] = {
                'id': player.id,
                'name': player.name,
                'picture_url': resolve_image_url(
                    getattr(player, 'picture_url', None)
                )
            }
        else:
            board['mistakes'] += 1

        filled = sum(
            cell is not None
            for cell in board['cells']
        )

        if (
            filled == 9
            or board['mistakes'] >= MAX_MISTAKES
        ):
            board['finished'] = True
            board['won'] = filled == 9

            row.games += 1
            row.wins += int(board['won'])
            row.losses += int(not board['won'])
            row.best_correct = max(
                row.best_correct,
                filled
            )

        row.board_json = json.dumps(board)
        db.session.commit()

        return jsonify({
            'correct': correct,
            'board': public_board(board),
            'stats': stats(row)
        })

    @app.post('/api/games/basketball-grid/give-up')
    @login_required
    def basketball_grid_give_up():
        row = record()
        board = load_board(row)

        if not board or board.get('finished'):
            return jsonify({
                'error': (
                    'There is no active grid to give up.'
                )
            }), 409

        board['finished'] = True
        board['won'] = False
        board['gave_up'] = True

        row.games += 1
        row.losses += 1
        row.best_correct = max(
            row.best_correct,
            sum(
                cell is not None
                for cell in board['cells']
            )
        )

        row.board_json = json.dumps(board)
        db.session.commit()

        return jsonify({
            'board': public_board(board),
            'stats': stats(row)
        })

    @app.get('/api/games/basketball-grid/my-stats')
    @login_required
    def basketball_grid_my_stats():
        row = record()
        result = stats(row)

        db.session.commit()

        return jsonify({'stats': result})

    return BasketballGridGame
