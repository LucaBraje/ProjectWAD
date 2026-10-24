from pathlib import Path
p=Path('/mnt/data/grid_v3/basketball_grid_backend.py')
s=p.read_text()
s=s.replace('import random\n','import random\nimport unicodedata\n')
s=s.replace('    def public_board(board):','''    def flag_code(country):
        # Common English names and frequent alternative spellings.
        aliases = {
            'usa':'US', 'united states':'US', 'american':'US',
            'uk':'GB', 'united kingdom':'GB', 'british':'GB',
            'greece':'GR', 'greek':'GR', 'serbia':'RS', 'serbian':'RS',
            'france':'FR', 'french':'FR', 'spain':'ES', 'spanish':'ES',
            'turkey':'TR', 'türkiye':'TR', 'turkiye':'TR', 'turkish':'TR',
            'germany':'DE', 'german':'DE', 'italy':'IT', 'italian':'IT',
            'lithuania':'LT', 'lithuanian':'LT', 'latvia':'LV', 'latvian':'LV',
            'croatia':'HR', 'croatian':'HR', 'slovenia':'SI', 'slovenian':'SI',
            'montenegro':'ME', 'montenegrin':'ME', 'bosnia and herzegovina':'BA',
            'bosnian':'BA', 'north macedonia':'MK', 'macedonian':'MK',
            'romania':'RO', 'romanian':'RO', 'israel':'IL', 'israeli':'IL',
            'canada':'CA', 'canadian':'CA', 'australia':'AU', 'australian':'AU',
            'brazil':'BR', 'brazilian':'BR', 'argentina':'AR', 'argentinian':'AR',
            'georgia':'GE', 'georgian':'GE', 'ukraine':'UA', 'ukrainian':'UA',
            'russia':'RU', 'russian':'RU', 'poland':'PL', 'polish':'PL',
            'czech republic':'CZ', 'czechia':'CZ', 'czech':'CZ',
            'finland':'FI', 'finnish':'FI', 'sweden':'SE', 'swedish':'SE',
            'belgium':'BE', 'belgian':'BE', 'netherlands':'NL', 'dutch':'NL',
            'senegal':'SN', 'senegalese':'SN', 'nigeria':'NG', 'nigerian':'NG',
            'cameroon':'CM', 'cameroonian':'CM', 'angola':'AO', 'angolan':'AO',
            'new zealand':'NZ', 'ivory coast':'CI', 'cote d ivoire':'CI',
            'congo':'CG', 'dr congo':'CD', 'dominican republic':'DO',
            'puerto rico':'PR', 'puerto rican':'PR', 'japan':'JP', 'japanese':'JP',
            'china':'CN', 'chinese':'CN', 'estonia':'EE', 'estonian':'EE',
            'bulgaria':'BG', 'bulgarian':'BG', 'hungary':'HU', 'hungarian':'HU',
            'cyprus':'CY', 'cypriot':'CY', 'albania':'AL', 'albanian':'AL',
            'kosovo':'XK', 'kosovar':'XK', 'switzerland':'CH', 'swiss':'CH',
        }
        return aliases.get(str(country).strip().casefold())

    def decorate_category(category):
        item = dict(category)
        if item.get('type') == 'team':
            team = db.session.get(TeamModel, item['value']) if TeamModel else None
            item['image_url'] = getattr(team, 'image_url', None) if team else None
        elif item.get('type') == 'nationality':
            item['flag_code'] = flag_code(item['value'])
        return item

    TeamModel = Player.team.property.mapper.class_ if hasattr(Player, 'team') else None

    def player_cell_image(cell):
        if not cell:
            return cell
        result = dict(cell)
        if 'picture_url' not in result:
            player = db.session.get(Player, result.get('id'))
            result['picture_url'] = getattr(player, 'picture_url', None) if player else None
        return result

    def public_board(board):''')
s=s.replace("return {'rows': rows, 'columns': cols, 'cells': board.get('cells', []),", "return {'rows': [decorate_category(x) for x in rows],\n                'columns': [decorate_category(x) for x in cols],\n                'cells': [player_cell_image(x) for x in board.get('cells', [])],")
s=s.replace("board['cells'][index] = {'id': player.id, 'name': player.name}","board['cells'][index] = {'id': player.id, 'name': player.name,\n                                     'picture_url': getattr(player, 'picture_url', None)}")
needle="    @app.get('/api/games/basketball-grid/my-stats')"
insert='''    @app.post('/api/games/basketball-grid/give-up')
    @login_required
    def basketball_grid_give_up():
        row = record()
        board = load_board(row)
        if not board or board.get('finished'):
            return jsonify({'error': 'There is no active grid to give up.'}), 409
        board['finished'] = True
        board['won'] = False
        board['gave_up'] = True
        row.games += 1
        row.losses += 1
        row.best_correct = max(row.best_correct, sum(c is not None for c in board['cells']))
        row.board_json = json.dumps(board)
        db.session.commit()
        return jsonify({'board': public_board(board), 'stats': stats(row)})

'''
s=s.replace(needle,insert+needle)
p.write_text(s)
