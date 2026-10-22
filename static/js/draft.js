
'use strict';
// Each entry represents a draft stage.
// We can add a coach stage later without rewriting the draft flow.
let STAGES = [];
function buildStages(includeLegends) {
    STAGES = [
        {type: 'club'},
        ...(includeLegends ? [{type: 'legend'}] : []),
        ...Array.from({length: includeLegends ? 4 : 5}, () => ({type: 'player'}))
    ];
}
const POSITIONS = ['PG', 'SG', 'SF', 'PF', 'C'];
const $ = id => document.getElementById(id);
const state = {
    teams: [],
    players: [],
    legends: [],
    includeLegends: false,
    stage: 0,
    club: null,
    roster: {},
    offers: [],
    chosen: null,
    spinning: false,
    runToken: null
};
// Convert stored image paths into usable URLs.
const asset = path => {
    if (!path) return '';
    if (/^https?:\/\//i.test(path) || path.startsWith('/')) {
        return path;
    }
    return '/static/' + path.replace(/^static\//, '');
};
// Helper for creating HTML elements.
const node = (tag, cls, text) => {
    const el = document.createElement(tag);
    if (cls) el.className = cls;
    if (text !== undefined) {
        el.textContent = String(text);
    }
    return el;
};
// Helper for creating images.
const img = (path, alt) => {
    const el = node('img');
    el.src = asset(path);
    el.alt = alt;
    el.loading = 'lazy';
    el.onerror = () => el.remove();
    return el;
};
// Shuffle an array randomly.
const shuffle = items => {
    const a = [...items];
    for (let i = a.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [a[i], a[j]] = [a[j], a[i]];
    }
    return a;
};
// Select random entries without duplicates.
const sample = (items, count) => {
    return shuffle(items).slice(0, count);
};
// Update the lineup displayed on screen.
function updateRoster() {
    const club = $('rosterClub');
    club.replaceChildren();
    if (state.club) {
        if (state.club.image_url) {
            club.append(img(state.club.image_url, state.club.name));
        }
        club.append(node('span', '', state.club.name));
    } else {
        club.textContent = 'Club not selected';
    }
    const slots = $('rosterSlots');
    slots.replaceChildren();
    for (const pos of POSITIONS) {
        const p = state.roster[pos];
        const row = node('div', `roster-slot ${p ? rarityClass(p.rating) : ''}`);
        row.append(node('span', 'roster-pos', pos));
        const info = node('div');
        info.append(
            node(
                'div',
                p ? 'roster-name' : 'roster-muted',
                p ? p.name : 'EMPTY SLOT'
            )
        );
        if (p) {
            info.append(
                node(
                    'div',
                    'roster-muted',
                    `${p.is_legend ? "★ LEGEND · " : ""}${p.position} · ${p.rating} OVR`
                )
            );
        }
        row.append(info);
        slots.append(row);
    }
}
// Display the current draft round.
function showStage() {
    for (const id of [
        'clubStage',
        'playersStage',
        'positionStage',
        'finishStage'
    ]) {
        $(id).hidden = true;
    }
    $('progressBar').style.width =
        `${(state.stage / STAGES.length) * 100}%`;
    $('roundLabel').textContent =
        state.stage >= STAGES.length
            ? 'DRAFT COMPLETE'
            : `ROUND ${state.stage + 1} OF ${STAGES.length}`;
    if (state.stage >= STAGES.length) {
        showFinish();
        return;
    }
    if (STAGES[state.stage].type === 'club') {
        $('clubStage').hidden = false;
        return;
    }
    showOffers();
}
// Display the selected club logo.
function renderClub() {
    const target = $('clubImage');
    target.replaceChildren();
    if (state.club?.image_url) {
        target.append(
            img(state.club.image_url, state.club.name)
        );
    } else {
        target.append(
            node('span', '', state.club ? '🏀' : '?')
        );
    }
    $('clubName').textContent =
        state.club?.name || 'MYSTERY CLUB';
}
// Animate the random club selection.
async function spinClub() {
    if (state.spinning) return;
    state.spinning = true;
    $('spinClubBtn').disabled = true;
    const options = sample(
        state.teams,
        Math.min(12, state.teams.length)
    );
    for (const team of options) {
        state.club = team;
        renderClub();
        await new Promise(resolve => setTimeout(resolve, 90));
    }
    state.club = sample(state.teams, 1)[0];
    renderClub();
    state.spinning = false;
    $('spinClubBtn').hidden = true;
    $('confirmClubBtn').hidden = false;
}
// Seven OVR tiers, shared by ordinary players and EuroLeague legends.
function rarityClass(rating) {
    const ovr = Number(rating);
    if (!Number.isFinite(ovr)) return 'rarity-basic';
    if (ovr >= 95) return 'rarity-mythic';
    if (ovr >= 90) return 'rarity-legendary';
    if (ovr >= 85) return 'rarity-epic';
    if (ovr >= 80) return 'rarity-rare';
    if (ovr >= 75) return 'rarity-uncommon';
    if (ovr >= 70) return 'rarity-common';
    return 'rarity-basic';
}
const rarityName = rating => ({
    'rarity-mythic': 'MYTHIC', 'rarity-legendary': 'LEGENDARY',
    'rarity-epic': 'EPIC', 'rarity-rare': 'RARE',
    'rarity-uncommon': 'UNCOMMON', 'rarity-common': 'COMMON',
    'rarity-basic': 'BASIC'
})[rarityClass(rating)];

// Display 10 randomly selected players.
function showOffers() {
    $('playersStage').hidden = false;
    const isLegendRound = STAGES[state.stage].type === 'legend';
    $('playersStage').classList.toggle('legend-stage', isLegendRound);
    $('playersStage').querySelector('h2').textContent = isLegendRound ? 'CHOOSE YOUR LEGEND' : 'CHOOSE YOUR PLAYER';
    $('playersStage').querySelector('.stage-count').textContent = isLegendRound ? '5 LEGENDS' : '10 OPTIONS';
    $('offersDescription').textContent = isLegendRound
        ? 'Five icons of EuroLeague history. Choose one legend for your starting five.'
        : 'Inspect any player, then choose one to add to your starting five.';

    $('playerRoundEyebrow').textContent =
        `ROUND ${state.stage + 1} / ${STAGES.length}`;
    if (!state.offers.length) {
        const taken = new Set(
            Object.values(state.roster).map(p => p.id)
        );
        state.offers = isLegendRound
            ? sample(state.legends, 5)
            : sample(state.players.filter(p => !taken.has(p.id)), 10);
    }
    const grid = $('playerGrid');
    grid.replaceChildren();
    for (const p of state.offers) {
        const card = node('button', `player-card ${rarityClass(p.rating)}${p.is_legend ? ' legend-card' : ''}`);
        if (p.is_legend) card.append(node('span', 'legend-crown', '★ LEGEND'));
        card.type = 'button';
        const photo = node('div', 'player-photo');
        if (p.picture_url) {
            photo.append(img(p.picture_url, p.name));
        } else {
            photo.append(
                node('span', 'placeholder', '♟')
            );
        }
        card.append(photo);
        card.append(node('span', 'rarity-label', rarityName(p.rating)));
        card.append(
            node('div', 'rating', p.rating ?? '—'),
            node('div', 'name', p.name),
            node(
                'div',
                'meta',
                `${p.position || '?'} · ${p.team_name || 'EuroLeague'}`
            )
        );
        card.addEventListener('click', () => openPlayer(p));
        grid.append(card);
    }
}
// Open a popup showing detailed player information.
function openPlayer(p) {
    state.chosen = p;
    $('playerDialog').classList.toggle('legend-dialog', Boolean(p.is_legend));
    for (const cls of ['rarity-basic','rarity-common','rarity-uncommon','rarity-rare','rarity-epic','rarity-legendary','rarity-mythic']) $('playerDialog').classList.remove(cls);
    $('playerDialog').classList.add(rarityClass(p.rating));
    const root = $('playerDetails');
    root.replaceChildren();
    if (p.picture_url) {
        root.append(img(p.picture_url, p.name));
    }
    const photo = root.querySelector('img');
    if (photo) {
        photo.className = 'detail-photo';
    }
    root.append(
        node('div', 'eyebrow', p.team_name || 'EUROLEAGUE'),
        node('h2', '', p.name),
        node(
            'p',
            '',
            `${p.nationality || 'Nationality unknown'} · ${p.position || 'Position unknown'}`
        )
    );
    const stats = node('div', 'detail-stats');
    for (const [label, value] of [
        ['OVR', p.rating],
        ['OFF', p.offense],
        ['DEF', p.defense],
        ['PPG', p.points_per_game],
        ['APG', p.assists_per_game],
        ['RPG', p.rebounds_per_game],
        ['BPG', p.blocks_per_game],
        ['SPG', p.steals_per_game]
    ]) {
        const cell = node('div');
        cell.append(
            node('strong', '', value ?? '—'),
            node('small', '', label)
        );
        stats.append(cell);
    }
    root.append(stats);
    $('playerDialog').showModal();
}
// Confirm a player and proceed to position selection.
function choosePlayer() {
    if (!state.chosen) return;
    $('playerDialog').close();
    $('playersStage').hidden = true;
    $('positionStage').hidden = false;
    $('chosenPlayer').textContent =
        `${state.chosen.name} · ${state.chosen.position || '?'} · ${state.chosen.rating ?? '—'} OVR`;
    const options = $('positionOptions');
    options.replaceChildren();
    for (const pos of POSITIONS) {
        const button = node('button', '', pos);
        button.type = 'button';
        button.disabled = Boolean(state.roster[pos]);
        button.title = button.disabled
            ? 'Already occupied'
            : `Assign ${state.chosen.name} to ${pos}`;
        button.addEventListener(
            'click',
            () => assignPosition(pos)
        );
        options.append(button);
    }
}
// Assign the drafted player to an available position.
function assignPosition(pos) {
    if (!state.chosen || state.roster[pos]) return;
    state.roster[pos] = state.chosen;
    state.chosen = null;
    state.offers = [];
    state.stage++;
    updateRoster();
    showStage();
}
function calculateTeamStats() {
    const players = POSITIONS.map(pos => state.roster[pos]);
    // Safely convert database values into numbers.
    const number = value => Number(value) || 0;
    // Sum a particular statistic across all five players.
    const total = stat => {
        return players.reduce(
            (sum, player) => sum + number(player[stat]),
            0
        );
    };
    // Calculate the average rating of the five players.
    const average = stat => {
        return total(stat) / players.length;
    };
    return {
        ppg: total('points_per_game'),
        apg: total('assists_per_game'),
        rpg: total('rebounds_per_game'),
        bpg: total('blocks_per_game'),
        spg: total('steals_per_game'),
        ovr: average('rating'),
        offense: average('offense'),
        defense: average('defense')
    };
}
function calculateTeamRating() {
    const stats = calculateTeamStats();
    // Keep each category between 0 and 100.
    const clamp = value => {
        return Math.max(0, Math.min(100, value));
    };
    // Convert a statistic into a score out of 100.
    const normalize = (value, target) => {
        return clamp((value / target) * 100);
    };
    // 1. Overall player quality (15%)
    const overallScore = clamp(stats.ovr);
    // 2. Offensive quality (25%)
    const offenseScore = clamp(stats.offense);
    // 3. Defensive quality (25%)
    const defenseScore = clamp(stats.defense);
    // 4. Scoring production (20%)
    const scoringScore = normalize(stats.ppg, 70);
    // 5. All-around statistics (15%)
    const assistsScore = normalize(stats.apg, 18);
    const reboundsScore = normalize(stats.rpg, 28);
    const stealsScore = normalize(stats.spg, 7);
    const blocksScore = normalize(stats.bpg, 4.5);
    const allAroundScore = (
        assistsScore * 0.35 +
        reboundsScore * 0.35 +
        stealsScore * 0.15 +
        blocksScore * 0.15
    );
    // Weighted base team score.
    const baseScore = (
        overallScore * 0.15 +
        offenseScore * 0.25 +
        defenseScore * 0.25 +
        scoringScore * 0.20 +
        allAroundScore * 0.15
    );
    // Calculate positional chemistry.
    let outOfPosition = 0;
    for (const pos of POSITIONS) {
        const player = state.roster[pos];
        // First version: exact position match only.
        const naturalPosition = (
            player.position || ''
        ).trim().toUpperCase();
        if (naturalPosition !== pos) {
            outOfPosition++;
        }
    }
    // Your multiplier system.
    const positionMultiplier = 2.0 - outOfPosition * 0.3;
    // Final team points.
    const totalPoints = baseScore * positionMultiplier;
    return {
        overallScore,
        offenseScore,
        defenseScore,
        scoringScore,
        allAroundScore,
        baseScore,
        outOfPosition,
        positionMultiplier,
        totalPoints
    };
}
// Display the completed team and its statistics.
function showFinish() {
    $('finishStage').hidden = false;
    const summary = $('summary');
    summary.replaceChildren();
    // Display the selected club.
    const clubHeading = node(
        'h2',
        'draft-final-heading',
        state.club ? state.club.name : 'YOUR TEAM'
    );
    summary.append(clubHeading);
    // Display the five drafted players.
    const lineup = node('div', 'draft-final-lineup');
    for (const pos of POSITIONS) {
        const p = state.roster[pos];
        const playerRow = node('div', `draft-final-player ${rarityClass(p.rating)}`);
        const positionLabel = node(
            'span',
            'draft-final-position',
            pos
        );
        const playerInfo = node('div', 'draft-final-player-info');
        playerInfo.append(
            node('strong', '', p.name),
            node(
                'small',
                '',
                `${p.is_legend ? "★ LEGEND | " : ""}Natural position: ${p.position} | ${p.rating} OVR`
            )
        );
        playerRow.append(positionLabel, playerInfo);
        lineup.append(playerRow);
    }
    summary.append(lineup);
    // Calculate the team statistics.
    const stats = calculateTeamStats();
    const statsHeading = node(
        'h2',
        'draft-stats-heading',
        'TEAM STATISTICS'
    );
    summary.append(statsHeading);
    const statsGrid = node('div', 'draft-stats-grid');
    const statistics = [
        ['POINTS / GAME', stats.ppg.toFixed(1)],
        ['ASSISTS / GAME', stats.apg.toFixed(1)],
        ['REBOUNDS / GAME', stats.rpg.toFixed(1)],
        ['BLOCKS / GAME', stats.bpg.toFixed(1)],
        ['STEALS / GAME', stats.spg.toFixed(1)],
        ['AVERAGE OVR', stats.ovr.toFixed(1)],
        ['AVERAGE OFFENSE', stats.offense.toFixed(1)],
        ['AVERAGE DEFENSE', stats.defense.toFixed(1)]
    ];
    for (const [label, value] of statistics) {
        const card = node('div', 'draft-stat-card');
        card.append(
            node('strong', 'draft-stat-value', value),
            node('span', 'draft-stat-label', label)
        );
        statsGrid.append(card);
    }
    summary.append(statsGrid);
    // Calculate the final team rating.
    const rating = calculateTeamRating();
    const ratingSection = node(
        'div',
        'draft-rating-section'
    );
    ratingSection.append(
        node('h2', 'draft-stats-heading', 'TEAM RATING')
    );
    // Show the five scoring categories.
    const categories = node(
        'div',
        'draft-rating-categories'
    );
    const categoryData = [
        ['OVERALL QUALITY', rating.overallScore, '15%'],
        ['OFFENSE', rating.offenseScore, '25%'],
        ['DEFENSE', rating.defenseScore, '25%'],
        ['SCORING', rating.scoringScore, '20%'],
        ['ALL-AROUND', rating.allAroundScore, '15%']
    ];
    for (const [label, score, weight] of categoryData) {
        const card = node(
            'div',
            'draft-rating-category'
        );
        card.append(
            node('span', '', label),
            node('strong', '', score.toFixed(1)),
            node('small', '', `Weight: ${weight}`)
        );
        categories.append(card);
    }
    ratingSection.append(categories);
    // Display base score and chemistry multiplier.
    const calculation = node(
        'div',
        'draft-rating-calculation'
    );
    calculation.append(
        node(
            'p',
            '',
            `Base team score: ${rating.baseScore.toFixed(1)} / 100`
        ),
        node(
            'p',
            '',
            `Out-of-position players: ${rating.outOfPosition} / 5`
        ),
        node(
            'p',
            '',
            `Position multiplier: x${rating.positionMultiplier.toFixed(1)}`
        )
    );
    ratingSection.append(calculation);
    // Final points display.
    const total = node(
        'div',
        'draft-rating-total'
    );
    total.append(
        node('span', '', 'FINAL TEAM POINTS'),
        node(
            'strong',
            '',
            rating.totalPoints.toFixed(1)
        ),
        node(
            'small',
            '',
            'Maximum possible: 200 points'
        )
    );
    ratingSection.append(total);
    summary.append(ratingSection);
    $('progressBar').style.width = '100%';
}
// Restart the draft.
function reset() {
    state.includeLegends = $('includeLegends').checked;
    if (state.includeLegends && state.legends.length < 5) {
        $('errorBox').hidden = false;
        $('errorBox').textContent = 'You need at least 5 legends in the database.';
        return;
    }
    buildStages(state.includeLegends);
    $('errorBox').hidden = true;
    state.stage = 0;
    state.club = null;
    state.roster = {};
    state.offers = [];
    state.chosen = null;
    state.spinning = false;
    state.runToken = crypto.randomUUID();
    $('includeLegends').disabled = state.legends.length < 5;
    $('spinClubBtn').hidden = false;
    $('spinClubBtn').disabled = false;
    $('confirmClubBtn').hidden = true;
    renderClub();
    updateRoster();
    showStage();
}
// Fetch the draft player and team pools from Flask.
async function init() {
    try {
        const response = await fetch('/api/draft/pool');
        if (!response.ok) {
            throw Error(`HTTP ${response.status}`);
        }
        const data = await response.json();
        state.teams = data.teams || [];
        state.players = data.players || [];
        state.legends = (data.legends || []).map(p => ({...p, is_legend: true}));
        $('includeLegends').disabled = state.legends.length < 5;
        if (state.legends.length < 5) $('includeLegends').title = 'At least five legends are required';
        if (!state.teams.length || state.players.length < 14) {
            throw Error(
                'Draft needs at least one team and 14 players to provide 10 options in every round.'
            );
        }
        reset();
    } catch (err) {
        $('errorBox').hidden = false;
        $('errorBox').textContent =
            `Unable to start draft: ${err.message}`;
        $('roundLabel').textContent = 'DRAFT UNAVAILABLE';
    }
}
// Button event listeners.
$('spinClubBtn').addEventListener('click', spinClub);
$('includeLegends').addEventListener('change', () => {
    if (state.stage === 0 && !state.club) buildStages($('includeLegends').checked);
});

$('confirmClubBtn').addEventListener('click', () => {
    if (!state.club) return;
    $('includeLegends').disabled = true;
    state.stage++;
    showStage();
});
$('closeDialogBtn').addEventListener(
    'click',
    () => $('playerDialog').close()
);
$('selectPlayerBtn').addEventListener(
    'click',
    choosePlayer
);
$('backToPlayersBtn').addEventListener('click', () => {
    $('positionStage').hidden = true;
    $('playersStage').hidden = false;
});
$('restartBtn').addEventListener('click', () => {
    if (confirm('Restart your draft and lose the current lineup?')) {
        reset();
    }
});
$('playAgainBtn').addEventListener('click', reset);
// Start the game.
init();
// =====================================================
// EUROLEAGUE SEASON SIMULATION
// =====================================================
const SIM_POSITIONS = ['PG', 'SG', 'SF', 'PF', 'C'];
// Estimate the strength of an existing EuroLeague club
// from its best five players.
function calculateOpponentStrength(team) {
    const teamPlayers = state.players
        .filter(p => Number(p.team_id) === Number(team.id));
    if (!teamPlayers.length) {
        return 120;
    }
    // Prefer a balanced starting five.
    const available = [...teamPlayers];
    const starters = [];
    for (const position of SIM_POSITIONS) {
        const candidates = available
            .filter(p => String(p.position || '')
                .toUpperCase()
                .split(/[\/,]/)
                .map(x => x.trim())
                .includes(position));
        const pool = candidates.length ? candidates : available;
        if (!pool.length) break;
        pool.sort((a, b) =>
            Number(b.rating || 0) - Number(a.rating || 0)
        );
        const chosen = pool[0];
        starters.push(chosen);
        available.splice(available.indexOf(chosen), 1);
    }
    if (!starters.length) return 120;
    const average = field =>
        starters.reduce(
            (sum, p) => sum + Number(p[field] || 0),
            0
        ) / starters.length;
    const avgOVR = average('rating');
    const avgOFF = average('offense');
    const avgDEF = average('defense');
    // Map existing clubs onto approximately the same
    // 0-200 scale as the drafted team's rating.
    // These are balancing estimates, not real results.
    return Math.max(
        60,
        Math.min(
            190,
            (avgOVR * 0.20 +
             avgOFF * 0.40 +
             avgDEF * 0.40) * 1.65
        )
    );
}
// Simulate one game with randomness and home advantage.
function simulateGame(teamA, teamB, homeAdvantage = 0) {
    const difference =
        teamA.strength - teamB.strength + homeAdvantage;
    // Stronger teams are more likely to win,
    // but upsets remain possible.
    const probabilityA =
        1 / (1 + Math.exp(-difference / 22));
    return Math.random() < probabilityA ? teamA : teamB;
}
// Simulate a best-of-five playoff series.
function simulateSeries(teamA, teamB) {
    let winsA = 0;
    let winsB = 0;
    // Higher seed has home-court advantage:
    // games 1, 2 and 5.
    const homePattern = [1, 1, -1, -1, 1];
    let game = 0;
    while (winsA < 3 && winsB < 3) {
        const homeAdvantage = homePattern[game] * 4;
        const winner = simulateGame(
            teamA,
            teamB,
            homeAdvantage
        );
        if (winner === teamA) {
            winsA++;
        } else {
            winsB++;
        }
        game++;
    }
    return {
        winner: winsA === 3 ? teamA : teamB,
        score: `${winsA}-${winsB}`
    };
}
// Simulate the play-in tournament.
function simulatePlayIn(standings) {
    const seventh = standings[6];
    const eighth = standings[7];
    const ninth = standings[8];
    const tenth = standings[9];
    // Winner of 7 vs 8 becomes seed 7.
    const game78 = simulateGame(seventh, eighth, 4);
    const seventhSeed = game78;
    const loser78 =
        game78 === seventh ? eighth : seventh;
    // Loser of 9 vs 10 is eliminated.
    const game910 = simulateGame(ninth, tenth, 4);
    // Final play-in game determines seed 8.
    const eighthSeed = simulateGame(
        loser78,
        game910,
        4
    );
    return {
        seventhSeed,
        eighthSeed,
        eliminated: [
            game910 === ninth ? tenth : ninth,
            eighthSeed === loser78 ? game910 : loser78
        ]
    };
}
// Run the complete competition.
function simulateEuroLeague() {
    const rating = calculateTeamRating();
    const myTeam = {
        id: 'drafted-team',
        name: state.club?.name || 'My Draft Team',
        strength: rating.totalPoints,
        wins: 0,
        losses: 0,
        isUser: true
    };
    // Every existing EuroLeague club becomes an opponent.
    const opponents = state.teams.map(team => ({
        id: team.id,
        name: team.name,
        strength: calculateOpponentStrength(team),
        wins: 0,
        losses: 0,
        isUser: false
    }));
    const teams = [myTeam, ...opponents];
    // REGULAR SEASON
    // Each pair plays twice, once at each team's home.
    for (let i = 0; i < teams.length; i++) {
        for (let j = i + 1; j < teams.length; j++) {
            const a = teams[i];
            const b = teams[j];
            const first = simulateGame(a, b, 4);
            const second = simulateGame(a, b, -4);
            for (const winner of [first, second]) {
                const loser = winner === a ? b : a;
                winner.wins++;
                loser.losses++;
            }
        }
    }
    // Sort by wins, then strength as a simplified tiebreaker.
    const standings = [...teams].sort(
        (a, b) =>
            b.wins - a.wins ||
            b.strength - a.strength
    );
    const userSeed =
        standings.findIndex(t => t.isUser) + 1;
    const result = {
        wins: myTeam.wins,
        losses: myTeam.losses,
        seed: userSeed,
        totalTeams: teams.length,
        teamStrength: myTeam.strength,
        outcome: '',
        details: ''
    };
    // OUTSIDE TOP 10
    if (userSeed > 10) {
        result.outcome = 'OUT OF PLAYOFFS';
        result.details =
            'Your team failed to qualify for the postseason.';
        return result;
    }
    // PLAY-IN
    const playIn = simulatePlayIn(standings);
    if (userSeed >= 7 && userSeed <= 10) {
        const qualified =
            playIn.seventhSeed.isUser ||
            playIn.eighthSeed.isUser;
        if (!qualified) {
            result.outcome = 'PLAY-IN ELIMINATION';
            result.details =
                'Your team reached the play-in tournament but failed to qualify for the playoffs.';
            return result;
        }
    }
    // PLAYOFFS: Top six plus two play-in qualifiers.
    const playoffTeams = [
        ...standings.slice(0, 6),
        playIn.seventhSeed,
        playIn.eighthSeed
    ];
    // Quarterfinals: 1v8, 2v7, 3v6, 4v5.
    const matchups = [
        [playoffTeams[0], playoffTeams[7]],
        [playoffTeams[1], playoffTeams[6]],
        [playoffTeams[2], playoffTeams[5]],
        [playoffTeams[3], playoffTeams[4]]
    ];
    const quarterfinalWinners = [];
    for (const [a, b] of matchups) {
        const series = simulateSeries(a, b);
        quarterfinalWinners.push(series.winner);
    }
    if (!quarterfinalWinners.includes(myTeam)) {
        result.outcome = 'PLAYOFF ELIMINATION';
        result.details =
            'Your team qualified for the playoffs but lost its best-of-five quarterfinal series.';
        return result;
    }
    // FINAL FOUR
    // Reseed remaining teams based on regular-season rank.
    quarterfinalWinners.sort(
        (a, b) =>
            standings.indexOf(a) - standings.indexOf(b)
    );
    const semifinal1 = simulateGame(
        quarterfinalWinners[0],
        quarterfinalWinners[3]
    );
    const semifinal2 = simulateGame(
        quarterfinalWinners[1],
        quarterfinalWinners[2]
    );
    if (semifinal1 !== myTeam && semifinal2 !== myTeam) {
        result.outcome = 'FINAL FOUR';
        result.details =
            'Your team reached the Final Four but lost in the semifinals.';
        return result;
    }
    // CHAMPIONSHIP FINAL
    const champion = simulateGame(
        semifinal1,
        semifinal2
    );
    if (champion !== myTeam) {
        result.outcome = 'EUROLEAGUE FINALIST';
        result.details =
            'Your team reached the championship game but finished as runner-up.';
        return result;
    }
    result.outcome = 'EUROLEAGUE CHAMPIONS';
    result.details =
        'Congratulations! Your drafted starting five won the EuroLeague!';
    return result;
}
// =====================================================
// SIMULATION BUTTON AND RESULTS
// =====================================================
// Create the button when the completed draft is shown.
function addSimulationButton() {
    const summary = $('summary');
    if (!summary || $('simulateSeasonBtn')) return;
    const button = node(
        'button',
        'simulate-season-btn',
        '🏆 SIMULATE EUROLEAGUE SEASON'
    );
    button.id = 'simulateSeasonBtn';
    button.type = 'button';
    button.addEventListener('click', async () => {
        if (button.disabled) return;
        button.disabled = true;
        button.textContent = 'SIMULATING SEASON...';
        const lineup = {};
        for (const pos of POSITIONS) {
            const player = state.roster[pos];
            lineup[pos] = {type: player.is_legend ? 'legend' : 'player', id: player.id};
        }
        try {
            const response = await fetch('/api/draft/simulate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'same-origin',
                body: JSON.stringify({
                    club_id: state.club.id,
                    lineup: lineup,
                    run_token: state.runToken
                })
            });
            const data = await response.json();
            if (!response.ok) {
                throw new Error(
                    data.error || 'Simulation failed.'
                );
            }
            // Use the authoritative Flask result.
            showSimulationResult(data.result);
            // Display saving status.
            const container = $('simulationResult');
            if (data.saved) {
                container.append(
                    node(
                        'p',
                        'simulation-save-status',
                        '✓ Result saved to your profile'
                    )
                );
            } else {
                container.append(
                    node(
                        'p',
                        'simulation-save-status',
                        'Guest result — log in to save future drafts.'
                    )
                );
            }
            // Show any newly unlocked achievements.
            if (data.new_achievements?.length) {
                const achievements = node(
                    'div',
                    'simulation-achievements'
                );
                achievements.append(
                    node(
                        'h3',
                        '',
                        '🏆 NEW ACHIEVEMENTS UNLOCKED!'
                    )
                );
                for (const achievement of data.new_achievements) {
                    achievements.append(
                        node(
                            'p',
                            '',
                            achievement.name
                        )
                    );
                }
                container.append(achievements);
            }
            button.hidden = true;
        } catch (error) {
            alert(error.message);
            button.disabled = false;
            button.textContent =
                '🏆 SIMULATE EUROLEAGUE SEASON';
        }
    });
    summary.append(button);
}
// Display the final simulation result.
function showSimulationResult(result) {
    let container = $('simulationResult');
    if (!container) {
        container = node('div', 'simulation-result');
        container.id = 'simulationResult';
        $('summary').append(container);
    }
    container.replaceChildren();
    const champion =
        result.outcome === 'EUROLEAGUE CHAMPIONS';
    if (champion) {
        container.classList.add('simulation-champion');
    } else {
        container.classList.remove('simulation-champion');
    }
    container.append(
        node(
            'span',
            'simulation-eyebrow',
            'EUROLEAGUE SEASON RESULTS'
        ),
        node(
            'h2',
            'simulation-record',
            `${result.wins} - ${result.losses}`
        ),
        node(
            'p',
            'simulation-seed',
            `Regular Season: #${result.seed} of ${result.totalTeams} teams`
        ),
        node(
            'h3',
            'simulation-outcome',
            result.outcome
        ),
        node(
            'p',
            'simulation-details',
            result.details
        )
    );
    container.scrollIntoView({
        behavior: 'smooth',
        block: 'center'
    });
}
// Attach the simulation button to the completed draft.
const originalShowFinish = showFinish;
showFinish = function () {
    originalShowFinish();
    // Remove old simulation results when displaying
    // the completed team again.
    $('simulationResult')?.remove();
    $('simulateSeasonBtn')?.remove();
    addSimulationButton();
};
