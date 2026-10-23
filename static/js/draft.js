
'use strict';

// Each entry represents a draft stage.
// We can add a coach stage later without rewriting the draft flow.

let STAGES = [];

function buildStages(includeLegends) {
    STAGES = [
        {type: 'club'},
        ...(includeLegends ? [{type: 'legend'}] : []),
        ...Array.from(
            {length: includeLegends ? 4 : 5},
            () => ({type: 'player'})
        )
    ];
}

const POSITIONS = ['PG', 'SG', 'SF', 'PF', 'C'];

const POSITION_VALUES = {
    PG: 1,
    SG: 2,
    SF: 3,
    PF: 4,
    C: 5
};

function getSimulationTeamLogo(teamName, teamId = null) {
    const normalized = value =>
        String(value || '').trim().toLowerCase();

    // The drafted team uses the logo selected during the club spin.
    if (String(teamId) === 'drafted-team') {
        return asset(state.club?.image_url);
    }

    const team = state.teams.find(t =>
        (teamId != null && String(t.id) === String(teamId)) ||
        normalized(t.name) === normalized(teamName)
    );

    return asset(team?.image_url);
}

function simulationLogo(teamName, teamId = null) {
    const wrapper = node('span', 'sim-team-logo');
    const url = getSimulationTeamLogo(teamName, teamId);

    if (url) {
        const image = document.createElement('img');
        image.src = url;
        image.alt = `${teamName} logo`;
        image.loading = 'lazy';

        image.onerror = () => {
            image.remove();
            wrapper.append(node('span', '', '🏀'));
        };

        wrapper.append(image);
    } else {
        wrapper.append(node('span', '', '🏀'));
    }

    return wrapper;
}

function simulationTeamLabel(name, id = null) {
    const label = node('span', 'sim-team-label');

    label.append(
        simulationLogo(name, id),
        node('span', 'sim-team-name', name)
    );

    return label;
}

const $ = id => document.getElementById(id);

function setDraftLayout(mode) {
    document.body.classList.toggle(
        'draft-full-preview',
        mode === 'preview'
    );

    document.body.classList.toggle(
        'draft-simulation-active',
        mode === 'simulation'
    );
}

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
// Create a small nationality flag using countries.js.
function createCountryFlag(countryName) {
    if (!countryName || typeof getFlagUrl !== 'function') {
        return null;
    }

    const flagUrl = getFlagUrl(countryName);

    if (!flagUrl) return null;

    const flag = document.createElement('img');

    flag.src = flagUrl;
    flag.alt = `${countryName} flag`;
    flag.className = 'draft-country-flag';
    flag.loading = 'lazy';

    flag.onerror = () => flag.remove();

    return flag;
}
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

        const row = node(
            'div',
            `roster-slot ${p ? rarityClass(p.rating) : ''}`
        );

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
    $('legendSetting').hidden = state.stage > 0;

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
    'rarity-mythic': 'MYTHIC',
    'rarity-legendary': 'LEGENDARY',
    'rarity-epic': 'EPIC',
    'rarity-rare': 'RARE',
    'rarity-uncommon': 'UNCOMMON',
    'rarity-common': 'COMMON',
    'rarity-basic': 'BASIC'
})[rarityClass(rating)];

// Display 10 randomly selected players.
function showOffers() {
    $('playersStage').hidden = false;

    const isLegendRound = STAGES[state.stage].type === 'legend';

    $('playersStage').classList.toggle(
        'legend-stage',
        isLegendRound
    );

    $('playersStage').querySelector('h2').textContent =
        isLegendRound
            ? 'CHOOSE YOUR LEGEND'
            : 'CHOOSE YOUR PLAYER';

    $('playersStage').querySelector('.stage-count').textContent =
        isLegendRound ? '5 LEGENDS' : '10 OPTIONS';

    $('offersDescription').textContent =
        isLegendRound
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
            : sample(
                state.players.filter(p => !taken.has(p.id)),
                10
            );
    }

    const grid = $('playerGrid');
    grid.replaceChildren();

    for (const p of state.offers) {
        const card = node(
            'button',
            `player-card ${rarityClass(p.rating)}${p.is_legend ? ' legend-card' : ''}`
        );

        if (p.is_legend) {
            card.append(
                node('span', 'legend-crown', '★ LEGEND')
            );
        }

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

        card.append(
            node('span', 'rarity-label', rarityName(p.rating))
        );

       // Overall rating and natural position on one line.

// Overall rating and natural position.
const ratingRow = node('div', 'draft-rating-row');

ratingRow.append(
    node('div', 'rating', p.rating ?? '—'),
    node('span', 'draft-player-position', p.position || '?')
);

// Player name with nationality flag.
const nameRow = node('div', 'draft-name-row');

nameRow.append(
    node('div', 'name', p.name)
);

const flag = createCountryFlag(p.nationality);

if (flag) {
    nameRow.append(flag);
}

// Club name with team logo.
const teamRow = node('div', 'meta draft-team-row');

// Find the player's team in the existing teams database.
const playerTeam = state.teams.find(team =>
    Number(team.id) === Number(p.team_id) ||
    team.name?.trim().toLowerCase() ===
        p.team_name?.trim().toLowerCase()
);

// Use the team's existing image_url.
if (playerTeam?.image_url) {
    const teamLogo = img(
        playerTeam.image_url,
        `${playerTeam.name} logo`
    );

    teamLogo.className = 'draft-team-logo';
    teamRow.append(teamLogo);
}

teamRow.append(
    node('span', 'draft-team-name', p.team_name || 'EuroLeague')
);

// Add everything to the player card.
card.append(
    ratingRow,
    nameRow,
    teamRow
);


        card.addEventListener('click', () => openPlayer(p));
        grid.append(card);
    }
}

// Open a popup showing detailed player information.
function openPlayer(p) {
    state.chosen = p;

    $('playerDialog').classList.toggle(
        'legend-dialog',
        Boolean(p.is_legend)
    );

    for (const cls of [
        'rarity-basic',
        'rarity-common',
        'rarity-uncommon',
        'rarity-rare',
        'rarity-epic',
        'rarity-legendary',
        'rarity-mythic'
    ]) {
        $('playerDialog').classList.remove(cls);
    }

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

// Nationality line containing the player's flag.
const nationalityRow = node('p', 'draft-detail-nationality');

const nationalityFlag = createCountryFlag(p.nationality);

if (nationalityFlag) {
    nationalityRow.append(nationalityFlag);
}

nationalityRow.append(
    node(
        'span',
        '',
        `${p.nationality || 'Nationality unknown'} · ${p.position || 'Position unknown'}`
    )
);
// Add team, player name and nationality to popup.
root.append(
    node('div', 'eyebrow', p.team_name || 'EUROLEAGUE'),
    node('h2', '', p.name),
    nationalityRow
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

    // Calculate total positional distance across the lineup.
    let positionDifference = 0;

    for (const [assignedPosition, player] of Object.entries(state.roster)) {
        if (!player) continue;

        // Supports positions such as "PG", "SG", or "PG/SG".
        const naturalPositions = String(player.position || '')
            .toUpperCase()
            .replace(/,/g, '/')
            .split('/')
            .map(position => position.trim())
            .filter(position => POSITION_VALUES[position] !== undefined);

        const assignedValue = POSITION_VALUES[assignedPosition];

        const distance = naturalPositions.length && assignedValue !== undefined
            ? Math.min(
                ...naturalPositions.map(position =>
                    Math.abs(POSITION_VALUES[position] - assignedValue)
                )
            )
            : 4;

        positionDifference += distance;
    }

    // Subtract 0.1 for every position of distance.
    const positionMultiplier = 2.0 - positionDifference * 0.1;

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

/* =====================================================
   PART 2 — COMPLETED DRAFT AND SIMULATION SETUP
   ===================================================== */

// Display the completed team and its statistics.
function showFinish() {
    setDraftLayout('preview');

    $('finishStage').hidden = false;

    const summary = $('summary');
    summary.replaceChildren();

    // Display the selected club.
    const clubHeading = node('div', 'draft-final-club');

    if (state.club?.image_url) {
        const logo = img(state.club.image_url, state.club.name);
        logo.className = 'draft-final-club-logo';
        clubHeading.append(logo);
    }

    clubHeading.append(
        node(
            'h2',
            'draft-final-heading',
            state.club?.name || 'YOUR TEAM'
        )
    );

    summary.append(clubHeading);

    // Display the five drafted players.
    const lineup = node('div', 'draft-final-lineup');

    for (const pos of POSITIONS) {
        const p = state.roster[pos];

        const playerRow = node(
            'div',
            `draft-final-player ${rarityClass(p.rating)}`
        );

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

        const playerPhoto = node('div', 'draft-final-player-photo');

        if (p.picture_url) {
            const photo = img(p.picture_url, p.name);
            playerPhoto.append(photo);
        } else {
            playerPhoto.append(node('span', '', '🏀'));
        }

        playerRow.append(positionLabel, playerPhoto, playerInfo);
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

    $('progressBar').style.width = '100%';
}

// Restart the draft.
function reset() {
    // Remove the previous simulation standings.
    document.querySelector('.season-sidebar-standings')?.remove();

    setDraftLayout('draft');

    // Stop any active season animation when restarting.
    activeSeasonAnimation?.cancel();
    activeSeasonAnimation = null;

    state.includeLegends = $('includeLegends').checked;

    if (state.includeLegends && state.legends.length < 5) {
        $('errorBox').hidden = false;
        $('errorBox').textContent =
            'You need at least 5 legends in the database.';
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
        // Load nationality codes before rendering player cards.
        if (typeof loadCountryCodes === 'function') {
            await loadCountryCodes();
        }

        const response = await fetch('/api/draft/pool');

        if (!response.ok) {
            throw Error(`HTTP ${response.status}`);
        }

        const data = await response.json();

        state.teams = data.teams || [];
        state.players = data.players || [];
        state.legends = (data.legends || []).map(p => ({
            ...p,
            is_legend: true
        }));

        $('includeLegends').disabled = state.legends.length < 5;

        if (state.legends.length < 5) {
            $('includeLegends').title =
                'At least five legends are required';
        }

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
    if (state.stage === 0 && !state.club) {
        buildStages($('includeLegends').checked);
    }
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

/* =====================================================
   EUROLEAGUE SEASON SIMULATION
   ===================================================== */

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

// Part 3 continues with:
// function addSimulationButton() {

/* =====================================================
   PART 3 — SIMULATION BUTTON, STANDINGS AND SCOREBOARD
   ===================================================== */

// Create the simulation button when the draft is complete.
function addSimulationButton() {
    const summary = $('summary');

    if (!summary || $('simulateSeasonBtn')) return;

    const button = node(
        'button',
        'simulate-season-btn',
        ' SIMULATE EUROLEAGUE SEASON'
    );

    button.id = 'simulateSeasonBtn';
    button.type = 'button';

    button.addEventListener('click', async () => {
        if (button.disabled) return;

        setDraftLayout('simulation');

        $('finishStage').querySelector('h2').textContent =
            'EUROLEAGUE SEASON SIMULATION';

        $('finishStage').querySelector(':scope > p').textContent =
            'Follow your team through the regular season and playoffs.';

        button.disabled = true;
        button.textContent = 'SIMULATING SEASON...';

        const lineup = {};

        for (const pos of POSITIONS) {
            const player = state.roster[pos];

            lineup[pos] = {
                type: player.is_legend ? 'legend' : 'player',
                id: player.id
            };
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

            // Use the authoritative Flask simulation result.
            await showSimulationResult(data.result);

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
                        'NEW ACHIEVEMENTS UNLOCKED!'
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
                'SIMULATE EUROLEAGUE SEASON';
        }
    });

    summary.append(button);
}

/* =====================================================
   ANIMATED EUROLEAGUE SEASON
   Uses actual results returned by Flask.
   ===================================================== */

let activeSeasonAnimation = null;

const seasonSleep = ms =>
    new Promise(resolve => setTimeout(resolve, ms));

function makeSeasonElement(tag, className, text) {
    return node(tag, className, text);
}

function makeSeasonButton(text, onClick) {
    const button = node(
        'button',
        'season-control-btn',
        text
    );

    button.type = 'button';
    button.addEventListener('click', onClick);

    return button;
}

/* =====================================================
   LIVE STANDINGS CALCULATIONS
   ===================================================== */

// Calculate league standings after a specified matchday.
//
// This function includes all teams, even if the user
// only sees their own games on the scoreboard.
//
// Postseason games are not included in league standings.

function buildSeasonStandings(matchdays, throughRound) {
    const teams = new Map();

    function ensureTeam(id, name) {
        const key = String(id);

        if (!teams.has(key)) {
            teams.set(key, {
                id: key,
                name,
                wins: 0,
                losses: 0,
                pointsFor: 0,
                pointsAgainst: 0
            });
        }

        return teams.get(key);
    }

    // Include all clubs before Matchday 1.
    for (const round of matchdays) {
        for (const match of round.matches) {
            ensureTeam(match.home_id, match.home);
            ensureTeam(match.away_id, match.away);
        }
    }

    // Process completed regular-season matchdays.
    for (const round of matchdays.slice(0, throughRound)) {
        for (const match of round.matches) {
            const home = ensureTeam(
                match.home_id,
                match.home
            );

            const away = ensureTeam(
                match.away_id,
                match.away
            );

            const homeScore = Number(match.home_score) || 0;
            const awayScore = Number(match.away_score) || 0;

            home.pointsFor += homeScore;
            home.pointsAgainst += awayScore;

            away.pointsFor += awayScore;
            away.pointsAgainst += homeScore;

            if (homeScore > awayScore) {
                home.wins++;
                away.losses++;
            } else {
                away.wins++;
                home.losses++;
            }
        }
    }

    return [...teams.values()].sort((a, b) =>
        b.wins - a.wins ||
        (b.pointsFor - b.pointsAgainst) -
        (a.pointsFor - a.pointsAgainst) ||
        a.name.localeCompare(b.name)
    );
}

/* =====================================================
   LIVE STANDINGS RENDERER
   ===================================================== */

// This table will be placed in the right sidebar,
// underneath the drafted Starting Five.
//
// It still updates automatically after every matchday.

function renderSeasonStandings(target, standings) {
    target.replaceChildren();

    const table = node('table', 'season-table');

    const head = node('thead');
    const heading = node('tr');

    for (const label of [
        '#',
        'CLUB',
        'W',
        'L',
        '+/-'
    ]) {
        heading.append(node('th', '', label));
    }

    head.append(heading);
    table.append(head);

    const body = node('tbody');

    standings.forEach((team, index) => {
        const isUser =
            String(team.id) === 'drafted-team';

        const row = node(
            'tr',
            isUser ? 'season-my-team' : ''
        );

        // EuroLeague qualification zones.
        if (index < 6) {
            row.classList.add('season-direct');
        } else if (index < 10) {
            row.classList.add('season-playin');
        }

        const differential =
            Number(team.pointsFor || 0) -
            Number(team.pointsAgainst || 0);

        row.append(
            node('td', '', index + 1)
        );

        const clubCell = node(
            'td',
            'season-club-cell'
        );

        clubCell.append(
            simulationTeamLabel(
                team.name,
                team.id
            )
        );

        row.append(clubCell);

        for (const value of [
            team.wins,
            team.losses,
            differential > 0
                ? `+${differential}`
                : differential
        ]) {
            row.append(node('td', '', value));
        }

        body.append(row);
    });

    table.append(body);
    target.append(table);
}

/* =====================================================
   FIXED SCOREBOARD
   ===================================================== */

// Determine whether a game involves the drafted team.
//
// Regular-season games normally contain home_id / away_id.
// Postseason games may only contain home / away names.
//
// Supporting both formats lets the same scoreboard display
// regular-season, play-in, quarterfinal and Final Four games.

function isUserSeasonMatch(match) {
    if (!match) return false;

    if (match.is_user_game === true) {
        return true;
    }

    if (
        String(match.home_id) === 'drafted-team' ||
        String(match.away_id) === 'drafted-team'
    ) {
        return true;
    }

    const myTeamName = String(
        state.club?.name || ''
    ).trim().toLowerCase();

    if (!myTeamName) return false;

    const homeName = String(
        match.home || ''
    ).trim().toLowerCase();

    const awayName = String(
        match.away || ''
    ).trim().toLowerCase();

    return (
        homeName === myTeamName ||
        awayName === myTeamName
    );
}

// Normalize a game from either regular-season or
// postseason data into a common scoreboard format.

function normalizeSeasonMatch(match) {
    if (!match) return null;

    const myTeamName = String(
        state.club?.name || ''
    ).trim().toLowerCase();

    const homeName = String(
        match.home || ''
    ).trim().toLowerCase();

    const awayName = String(
        match.away || ''
    ).trim().toLowerCase();

    const homeIsUser =
        String(match.home_id) === 'drafted-team' ||
        (
            myTeamName &&
            homeName === myTeamName
        );

    const awayIsUser =
        String(match.away_id) === 'drafted-team' ||
        (
            myTeamName &&
            awayName === myTeamName
        );

    return {
        home: match.home,
        away: match.away,

        home_id: homeIsUser
            ? 'drafted-team'
            : match.home_id ?? null,

        away_id: awayIsUser
            ? 'drafted-team'
            : match.away_id ?? null,

        home_score: Number(match.home_score),
        away_score: Number(match.away_score),

        overtime: Number(match.overtime) || 0,

        is_user_game: homeIsUser || awayIsUser,

        stage: match.stage || null,

        game: match.game || null
    };
}

// Display the user's game.
//
// roundNumber is used for regular-season matchdays.
//
// phaseLabel is optional and allows the scoreboard
// to display postseason labels such as:
//
// PLAY-IN · VICTORY
// QUARTERFINALS · GAME 3 · DEFEAT
// FINAL FOUR SEMIFINAL · VICTORY
// EUROLEAGUE FINAL · VICTORY

function renderSeasonScoreboard(
    target,
    match,
    roundNumber = null,
    phaseLabel = null
) {
    target.replaceChildren();

    if (!match) {
        target.append(
            node(
                'div',
                'season-scoreboard season-scoreboard-empty',
                'No game available.'
            )
        );

        return;
    }

    const game = normalizeSeasonMatch(match);

    if (!game) return;

    const homeScore = game.home_score;
    const awayScore = game.away_score;

    const hasScores =
        Number.isFinite(homeScore) &&
        Number.isFinite(awayScore);

    const isHome =
        String(game.home_id) === 'drafted-team';

    const isAway =
        String(game.away_id) === 'drafted-team';

    // The scoreboard must only display the user's games.
    if (!isHome && !isAway) {
        return;
    }

    const userScore = isHome
        ? homeScore
        : awayScore;

    const opponentScore = isHome
        ? awayScore
        : homeScore;

    const won = hasScores &&
        userScore > opponentScore;

    const lost = hasScores &&
        userScore < opponentScore;

    const resultLabel = !hasScores
        ? 'UPCOMING'
        : won
            ? 'VICTORY'
            : lost
                ? 'DEFEAT'
                : 'TIED';

    const card = node(
        'div',
        `season-scoreboard ${
            won
                ? 'season-win'
                : lost
                    ? 'season-loss'
                    : ''
        }`
    );

    let gameLabel;

    if (phaseLabel) {
        gameLabel = String(phaseLabel);
    } else if (roundNumber !== null) {
        gameLabel = `MATCHDAY ${roundNumber}`;
    } else if (game.stage) {
        gameLabel = String(game.stage).toUpperCase();
    } else {
        gameLabel = 'EUROLEAGUE GAME';
    }

    card.append(
        node(
            'div',
            'season-scoreboard-label',
            `${gameLabel} · ${resultLabel}`
        )
    );

    const teams = node(
        'div',
        'season-scoreboard-teams'
    );

    const sides = [
        {
            name: game.home,
            id: game.home_id,
            score: homeScore,
            isUser: isHome
        },
        {
            name: game.away,
            id: game.away_id,
            score: awayScore,
            isUser: isAway
        }
    ];

    for (const sideData of sides) {
        const side = node(
            'div',
            `season-score-side ${
                sideData.isUser
                    ? 'season-score-user'
                    : ''
            }`
        );

        side.append(
            simulationLogo(
                sideData.name,
                sideData.id
            ),
            node(
                'div',
                'season-score-name',
                sideData.name
            ),
            node(
                'div',
                'season-score-number',
                hasScores
                    ? sideData.score
                    : '—'
            )
        );

        teams.append(side);
    }

    card.append(teams);

    // Add a small result summary underneath the scores.
    const resultSummary = node(
        'div',
        'season-score-footer'
    );

    if (!hasScores) {
        resultSummary.textContent =
            'GAME NOT PLAYED';
    } else if (game.overtime > 0) {
        resultSummary.textContent =
            `${game.overtime} OVERTIME PERIOD(S)`;
    } else {
        resultSummary.textContent =
            'FULL TIME';
    }

    card.append(resultSummary);

    target.append(card);
}

/* =====================================================
   USER'S POSTSEASON GAME EXTRACTION
   ===================================================== */

// Extract only games involving the drafted team.
//
// The Flask backend returns three postseason structures:
//
// result.play_in
// result.playoffs
// result.final_four
//
// We convert them into a chronological sequence that
// the Stage 3 animation can display on the scoreboard.

function buildUserPostseasonGames(result) {
    const games = [];

    // 1. PLAY-IN TOURNAMENT
    for (const game of result.play_in || []) {
        if (!isUserSeasonMatch(game)) {
            continue;
        }

        games.push({
            match: game,
            label: String(
                game.stage || 'PLAY-IN TOURNAMENT'
            ).toUpperCase(),
            phase: 'play_in'
        });
    }

    // 2. PLAYOFF QUARTERFINALS
    for (const series of result.playoffs || []) {
        const myTeamName = String(
            state.club?.name || ''
        ).trim().toLowerCase();

        const teamA = String(
            series.team_a || ''
        ).trim().toLowerCase();

        const teamB = String(
            series.team_b || ''
        ).trim().toLowerCase();

        // Ignore series not involving our team.
        if (
            teamA !== myTeamName &&
            teamB !== myTeamName
        ) {
            continue;
        }

        const seriesGames = series.games || [];

        seriesGames.forEach((game, index) => {
            if (!isUserSeasonMatch(game)) {
                return;
            }

            const gameNumber =
                game.game || index + 1;

            games.push({
                match: game,
                label:
                    `PLAYOFF QUARTERFINALS · GAME ${gameNumber}`,
                phase: 'playoffs',
                gameNumber
            });
        });
    }

    // 3. FINAL FOUR
    for (const game of result.final_four || []) {
        if (!isUserSeasonMatch(game)) {
            continue;
        }

        const stage = String(
            game.stage || ''
        ).toLowerCase();

        let label;

        if (/semi/i.test(stage)) {
            label = 'FINAL FOUR SEMIFINAL';
        } else if (
            /third|3rd|bronze/i.test(stage)
        ) {
            label = 'THIRD-PLACE GAME';
        } else if (
            /final|championship|title/i.test(stage)
        ) {
            label = 'EUROLEAGUE FINAL';
        } else {
            label = String(
                game.stage || 'FINAL FOUR'
            ).toUpperCase();
        }

        games.push({
            match: game,
            label,
            phase: 'final_four'
        });
    }

    return games;
}

// Part 4 continues with:
// function renderSeasonPostseason(target, result) {

/* =====================================================
   PART 4 — PLAYOFF BRACKET AND COMPLETE SEASON ANIMATION
   ===================================================== */

function renderSeasonPostseason(target, result) {
    target.replaceChildren();

    const section = node('section', 'season-postseason');

    section.append(
        node(
            'h2',
            'season-section-heading',
            ' EUROLEAGUE PLAYOFFS'
        )
    );

    // Display a club with its logo and result.
    function teamLine(name, score, isWinner) {
        const line = node(
            'div',
            `pb-team ${isWinner ? 'pb-winner' : ''}`
        );

        line.append(
            simulationTeamLabel(name || 'TBD'),
            node('strong', 'pb-score', score ?? '—')
        );

        return line;
    }

    // Reusable matchup card.
    function matchCard(label, a, b, scoreA, scoreB, winner) {
        const card = node('div', 'pb-match');

        card.append(
            node('div', 'pb-match-label', label),
            teamLine(a, scoreA, winner === a),
            teamLine(b, scoreB, winner === b)
        );

        return card;
    }

    // Individual knockout game.
    function knockoutCard(game, label) {
        const winner = game.winner ||
            (
                game.home_score > game.away_score
                    ? game.home
                    : game.away
            );

        return matchCard(
            label,
            game.home,
            game.away,
            game.home_score,
            game.away_score,
            winner
        );
    }

    // PLAY-IN TOURNAMENT
    if (result.play_in?.length) {
        const playIn = node('div', 'pb-playin');

        playIn.append(
            node(
                'h3',
                'pb-heading',
                'PLAY-IN TOURNAMENT'
            )
        );

        const grid = node('div', 'pb-playin-grid');

        result.play_in.forEach((game, index) => {
            grid.append(
                knockoutCard(
                    game,
                    game.stage || `PLAY-IN ${index + 1}`
                )
            );
        });

        playIn.append(grid);
        section.append(playIn);
    }

    // PLAYOFF BRACKET
    if (
        result.playoffs?.length ||
        result.final_four?.length
    ) {
        const bracket = node('div', 'pb-bracket');

        const quarters = node(
            'div',
            'pb-round pb-quarters'
        );

        const semis = node(
            'div',
            'pb-round pb-semis'
        );

        const finals = node(
            'div',
            'pb-round pb-finals'
        );

        quarters.append(
            node('h3', 'pb-heading', 'QUARTERFINALS')
        );

        semis.append(
            node('h3', 'pb-heading', 'FINAL FOUR')
        );

        finals.append(
            node('h3', 'pb-heading', 'CHAMPIONSHIP')
        );

        const quarterGames = node(
            'div',
            'pb-round-games'
        );

        const semiGames = node(
            'div',
            'pb-round-games'
        );

        const finalGames = node(
            'div',
            'pb-round-games'
        );

        // Best-of-five quarterfinal series.
        (result.playoffs || []).forEach((series, index) => {
            const wrapper = node('div', 'pb-series');

            wrapper.append(
                matchCard(
                    `QF ${index + 1} · BEST OF FIVE`,
                    series.team_a,
                    series.team_b,
                    series.wins_a,
                    series.wins_b,
                    series.winner
                )
            );

            // Individual games remain available in
            // expandable series details.
            if (series.games?.length) {
                const details = document.createElement('details');
                details.className = 'pb-details';

                const summary = document.createElement('summary');
                summary.textContent = 'VIEW SERIES GAMES';

                details.append(summary);

                series.games.forEach((game, gameIndex) => {
                    details.append(
                        node(
                            'div',
                            'pb-detail-game',
                            `G${game.game || gameIndex + 1}: ` +
                            `${game.home} ${game.home_score} – ` +
                            `${game.away_score} ${game.away}`
                        )
                    );
                });

                wrapper.append(details);
            }

            quarterGames.append(wrapper);
        });

        // Identify Final Four games by stage.
        const finalFour = result.final_four || [];

        const isSemi = game =>
            /semi/i.test(String(game.stage || ''));

        const isThirdPlace = game =>
            /third|3rd|bronze/i.test(
                String(game.stage || '')
            );

        const isFinal = game =>
            /final|championship|title/i.test(
                String(game.stage || '')
            ) && !isSemi(game);

        let semifinals = finalFour.filter(isSemi);

        let championship = finalFour.find(
            game => isFinal(game) && !isThirdPlace(game)
        );

        // Fallback for games without stage labels.
        if (!semifinals.length && finalFour.length >= 3) {
            semifinals = finalFour.slice(0, 2);
        }

        if (!championship && finalFour.length >= 3) {
            championship = finalFour[finalFour.length - 1];
        }

        semifinals.forEach((game, index) => {
            semiGames.append(
                knockoutCard(
                    game,
                    `SEMIFINAL ${index + 1}`
                )
            );
        });

        if (championship) {
            

            finalGames.append(
                knockoutCard(
                    championship,
                    'EUROLEAGUE FINAL'
                )
            );

            const champion = championship.winner ||
                (
                    championship.home_score >
                    championship.away_score
                        ? championship.home
                        : championship.away
                );

        

            
        }

        quarters.append(quarterGames);
        semis.append(semiGames);
        finals.append(finalGames);

        bracket.append(quarters, semis, finals);
        section.append(bracket);
    }

    if (
        !result.play_in?.length &&
        !result.playoffs?.length &&
        !result.final_four?.length
    ) {
        section.append(
            node(
                'p',
                'season-no-postseason',
                'No postseason games were included in this simulation result.'
            )
        );
    }

    target.append(section);
}

/* =====================================================
   STAGE 3 — COMPLETE SEASON ANIMATION
   ===================================================== */

async function showSimulationResult(result) {
    // Cancel any previous animation.
    activeSeasonAnimation?.cancel();

    // Remove standings left over from an earlier run.
    document.querySelector(
        '.season-sidebar-standings'
    )?.remove();

    let container = $('simulationResult');

    if (!container) {
        container = node('div', 'simulation-result');
        container.id = 'simulationResult';
        $('summary').append(container);
    }

    container.replaceChildren();
    container.classList.remove('simulation-champion');

    const matchdays = result.matchdays || [];

    // Support older results without matchday data.
    if (!matchdays.length) {
        container.append(
            node(
                'h2',
                'simulation-record',
                `${result.wins} – ${result.losses}`
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

        return;
    }

    // MAIN SIMULATION TITLE
    const title = node(
        'h2',
        'season-section-heading',
        'EUROLEAGUE SEASON SIMULATOR'
    );

    // Animation controls.
    const controls = node('div', 'season-controls');

    const roundLabel = node(
        'div',
        'season-round-label',
        `MATCHDAY 0 / ${matchdays.length}`
    );

    // Progress bar.
    const progressTrack = node(
        'div',
        'season-progress'
    );

    const progressFill = node(
        'div',
        'season-progress-fill'
    );

    progressTrack.append(progressFill);

    // Only the user's game appears in this scoreboard.
    const scoreboard = node('div');

    /* =================================================
       LIVE STANDINGS — RIGHT SIDEBAR
       ================================================= */

    const standingsPanel = node(
        'div',
        'season-panel season-sidebar-standings'
    );

    standingsPanel.append(
        node(
            'h3',
            'season-panel-title',
            'LIVE STANDINGS'
        )
    );

    const standingsBody = node(
        'div',
        'season-standings-scroll'
    );

    standingsPanel.append(standingsBody);

    // Move standings underneath Starting Five.
    const rosterPanel = document.querySelector(
        '.roster-panel'
    );

    if (rosterPanel) {
        rosterPanel.append(standingsPanel);
    }

    // Apply sidebar sizing directly, without requiring
    // changes to draft.css.
    standingsPanel.style.marginTop = '24px';
    standingsPanel.style.minWidth = '0';
    standingsPanel.style.maxWidth = '100%';
    standingsPanel.style.padding = '12px 4px';

    standingsBody.style.width = '100%';
    standingsBody.style.maxWidth = '100%';
    standingsBody.style.overflowX = 'auto';

    // Postseason bracket and final season report.
    const postseason = node('div');

    const finalResult = node(
        'div',
        'season-final-result'
    );
    
    // Select the final report banner based on the outcome.
    const outcomeText = String(result.outcome || '')
        .toLowerCase();

    let outcomeClass = 'outcome-missed';

    if (
        outcomeText.includes('champion') ||
        outcomeText.includes('winner')
    ) {
        outcomeClass = 'outcome-champion';

    } else if (
        outcomeText.includes('runner') ||
        outcomeText.includes('final loss') ||
        outcomeText.includes('lost final')
    ) {
        outcomeClass = 'outcome-runnerup';

    } else if (
        outcomeText.includes('final four') ||
        outcomeText.includes('semifinal') ||
        outcomeText.includes('semi-final')
    ) {
        outcomeClass = 'outcome-finalfour';

    } else if (
        outcomeText.includes('quarter') ||
        outcomeText.includes('playoff')
    ) {
        outcomeClass = 'outcome-quarterfinal';

    } else if (
        outcomeText.includes('play-in') ||
        outcomeText.includes('play in')
    ) {
        outcomeClass = 'outcome-playin';
    }

    finalResult.classList.add(outcomeClass);

    // No MATCHDAY RESULTS panel.
    // No standings panel in the main column.
    container.append(
        title,
        controls,
        roundLabel,
        progressTrack,
        scoreboard,
        postseason,
        finalResult
    );

    /* =================================================
       ANIMATION STATE
       ================================================= */

    const animation = {
        cancelled: false,
        paused: false,
        skipped: false,
        speed: 180,

        cancel() {
            this.cancelled = true;
            this.skipped = true;
        }
    };

    activeSeasonAnimation = animation;

    const pauseButton = makeSeasonButton(
        '⏸ PAUSE',
        () => {
            animation.paused = !animation.paused;

            pauseButton.textContent = animation.paused
                ? '▶ RESUME'
                : '⏸ PAUSE';
        }
    );

    const speedSelect = node(
        'select',
        'season-speed-select'
    );

    for (const [label, value] of [
        ['SLOW', '600'],
        ['NORMAL', '180'],
        ['FAST', '40']
    ]) {
        const option = node('option', '', label);

        option.value = value;
        option.selected = value === '180';

        speedSelect.append(option);
    }

    speedSelect.addEventListener('change', () => {
        animation.speed = Number(speedSelect.value);
    });

    const skipButton = makeSeasonButton(
        '⏭ SKIP TO END',
        () => {
            animation.skipped = true;
            animation.paused = false;
        }
    );

    controls.append(
        pauseButton,
        speedSelect,
        skipButton
    );

    /* =================================================
       REGULAR SEASON — 38 MATCHDAYS
       ================================================= */

    const showRound = index => {
        const round = matchdays[index];
        const number = index + 1;

        roundLabel.textContent =
            `MATCHDAY ${number} / ${matchdays.length}`;

        progressFill.style.width =
            `${(number / matchdays.length) * 100}%`;

        // Only find the user's match.
        const userMatch = (round.matches || []).find(
            match => isUserSeasonMatch(match)
        );

        renderSeasonScoreboard(
            scoreboard,
            userMatch,
            number
        );

        // Update standings using every regular-season game.
        const liveStandings = buildSeasonStandings(
            matchdays,
            number
        );

        renderSeasonStandings(
            standingsBody,
            liveStandings
        );
    };

    // Initially show the standings before Matchday 1.
    renderSeasonStandings(
        standingsBody,
        buildSeasonStandings(matchdays, 0)
    );

    container.scrollIntoView({
        behavior: 'smooth',
        block: 'start'
    });

    for (let i = 0; i < matchdays.length; i++) {
        if (animation.cancelled) return;

        if (animation.skipped) {
            showRound(matchdays.length - 1);
            break;
        }

        while (
            animation.paused &&
            !animation.skipped
        ) {
            if (animation.cancelled) return;

            await seasonSleep(80);
        }

        if (animation.cancelled) return;

        if (animation.skipped) {
            showRound(matchdays.length - 1);
            break;
        }

        showRound(i);

        await seasonSleep(animation.speed);
    }

    if (animation.cancelled) return;

    // Regular season finished.
    roundLabel.textContent = 'REGULAR SEASON COMPLETE';

    // Use official final standings returned by Flask.
    if (result.standings?.length) {
        renderSeasonStandings(
            standingsBody,
            result.standings.map(team => ({
                id: String(team.id),
                name: team.name,
                wins: team.wins,
                losses: team.losses,
                pointsFor:
                    Number(team.points_for ?? team.pointsFor ?? 0),
                pointsAgainst:
                    Number(team.points_against ?? team.pointsAgainst ?? 0)
            }))
        );
    }

    // These standings remain fixed throughout the playoffs.

    /* =================================================
       POSTSEASON — YOUR GAMES ONLY
       ================================================= */

    const userPostseasonGames =
        buildUserPostseasonGames(result);

    
    // Live playoff bracket: reveal results progressively.
    const liveBracket = node('div', 'pb-animation-content');

    const liveBracketHeading = node(
        'h3',
        'pb-animation-status',
        '🏆 POSTSEASON BRACKET'
    );

    postseason.append(liveBracketHeading, liveBracket);


    // Every postseason game is revealed in chronological order,
    // including games that do not involve the user's team.

    const revealedGames = new Set();

    const allPostseasonGames = [];

    // Play-in games
    for (const game of result.play_in || []) {
        allPostseasonGames.push({
            match: game,
            phase: 'play_in',
            round: 0
        });
    }

    // Quarterfinals: interleave games by game number,
    // rather than finishing one series before another.
    const playoffSeries = result.playoffs || [];

    const maxGames = Math.max(
        0,
        ...playoffSeries.map(series =>
            (series.games || []).length
        )
    );

    for (let round = 0; round < maxGames; round++) {
        for (const series of playoffSeries) {
            const game = (series.games || [])[round];

            if (game) {
                allPostseasonGames.push({
                    match: game,
                    phase: 'playoffs',
                    round: round + 1
                });
            }
        }
    }

    // Final Four games
    for (const game of result.final_four || []) {
        allPostseasonGames.push({
            match: game,
            phase: 'final_four',
            round: 0
        });
    }

    function updateLivePlayoffBracket() {
        const visiblePlayIn = (result.play_in || []).filter(
            game => revealedGames.has(game)
        );

        const visiblePlayoffs = (result.playoffs || []).map(
            series => {
                const playedGames = (series.games || []).filter(
                    game => revealedGames.has(game)
                );

                let winsA = 0;
                let winsB = 0;

                for (const game of playedGames) {
                    const winner = game.winner ||
                        (
                            Number(game.home_score) >
                            Number(game.away_score)
                                ? game.home
                                : game.away
                        );

                    if (winner === series.team_a) winsA++;
                    if (winner === series.team_b) winsB++;
                }

                const completed =
                    playedGames.length === (series.games || []).length;

                return {
                    ...series,
                    games: playedGames,
                    wins_a: winsA,
                    wins_b: winsB,
                    winner: completed ? series.winner : null
                };
            }
        );

        const visibleFinalFour = (result.final_four || []).filter(
            game => revealedGames.has(game)
        );

        renderSeasonPostseason(liveBracket, {
            ...result,
            play_in: visiblePlayIn,
            playoffs: visiblePlayoffs,
            final_four: visibleFinalFour
        });
    }

    // Initial bracket: no results revealed yet.
    updateLivePlayoffBracket();

    // Reset skip after regular season.
    animation.skipped = false;

   if (allPostseasonGames.length) {
        const postseasonControls = node(
            'div',
            'season-controls'
        );

        const postseasonPause = makeSeasonButton(
            '⏸ PAUSE',
            () => {
                animation.paused = !animation.paused;

                postseasonPause.textContent =
                    animation.paused
                        ? '▶ RESUME'
                        : '⏸ PAUSE';
            }
        );

        const skipPostseasonGames = makeSeasonButton(
            '⏭ SKIP POSTSEASON GAMES',
            () => {
                animation.skipped = true;
                animation.paused = false;
            }
        );

        postseasonControls.append(
            postseasonPause,
            speedSelect,
            skipPostseasonGames
        );

        controls.replaceChildren(postseasonControls);

        // Keep the same scoreboard used in the regular season.
       
        for (
            let i = 0;
            i < allPostseasonGames.length;
            i++
        ) {
            if (animation.cancelled) return;

            if (animation.skipped) {
                for (const entry of allPostseasonGames) {
                    revealedGames.add(entry.match);
                }

                updateLivePlayoffBracket();
                break;
            }

            while (
                animation.paused &&
                !animation.skipped
            ) {
                if (animation.cancelled) return;
                await seasonSleep(80);
            }

            if (animation.cancelled) return;

            if (animation.skipped) {
                for (const entry of allPostseasonGames) {
                    revealedGames.add(entry.match);
                }

                updateLivePlayoffBracket();
                break;
            }

            const entry = allPostseasonGames[i];

            // Reveal the current game in the bracket,
            // regardless of which teams are playing.
            revealedGames.add(entry.match);
            updateLivePlayoffBracket();

            const phaseName =
                entry.phase === 'play_in'
                    ? 'PLAY-IN TOURNAMENT'
                    : entry.phase === 'playoffs'
                        ? `QUARTERFINALS · GAME ${entry.round}`
                        : String(
                            entry.match.stage || 'FINAL FOUR'
                        ).toUpperCase();

            liveBracketHeading.textContent =
                `🏆 ${phaseName}`;

            // Only update the main scoreboard when
            // the current game involves your team.
            if (isUserSeasonMatch(entry.match)) {
                roundLabel.textContent = phaseName;

                renderSeasonScoreboard(
                    scoreboard,
                    entry.match,
                    null,
                    phaseName
                );
            }

            // Scroll to bracket at the beginning.
            if (i === 0) {
                liveBracket.scrollIntoView({
                    behavior: 'smooth',
                    block: 'nearest'
                });
            }

            await seasonSleep(animation.speed * 0.3);
        }


        controls.replaceChildren();
    } else {
        controls.replaceChildren();
    }

    if (animation.cancelled) return;

    /* =================================================
       PLAYOFF BRACKET ANIMATION
       ================================================= */


    // Finalize the live bracket after all games finish.
    if (animation.cancelled) return;

    revealedGames.clear();

    for (const game of result.play_in || []) {
        revealedGames.add(game);
    }

    for (const series of result.playoffs || []) {
        for (const game of series.games || []) {
            revealedGames.add(game);
        }
    }

    for (const game of result.final_four || []) {
        revealedGames.add(game);
    }

    updateLivePlayoffBracket();

    liveBracketHeading.textContent =
        '🏆 EUROLEAGUE SEASON COMPLETE';

    /* =================================================
       FINAL SEASON REPORT
       ================================================= */

    const champion =
        result.outcome === 'EUROLEAGUE CHAMPIONS';

    if (champion) {
        container.classList.add(
            'simulation-champion'
        );
    }

    finalResult.append(
        node(
            'div',
            'simulation-eyebrow',
            'FINAL SEASON REPORT'
        ),
        node(
            'h2',
            'simulation-record',
            `${result.wins} – ${result.losses}`
        ),
        node(
            'p',
            'simulation-seed',
            `Regular season: #${result.seed} of ${result.totalTeams}`
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
    
    // The season is finished.
    // Replace the top matchday scoreboard with
    // the Final Season Report.

    scoreboard.replaceChildren(finalResult);

    roundLabel.textContent = 'SEASON COMPLETE';
    progressFill.style.width = '100%';

    // The report now occupies the scoreboard's position,
    // directly above the playoff bracket.
    finalResult.style.marginTop = '0';
    finalResult.style.marginBottom = '28px';



    activeSeasonAnimation = null;
}

/* =====================================================
   ATTACH SIMULATION BUTTON TO DRAFT COMPLETION
   ===================================================== */

const originalShowFinish = showFinish;

showFinish = function () {
    originalShowFinish();

    // Remove any previous simulation results.
    $('simulationResult')?.remove();
    $('simulateSeasonBtn')?.remove();

    // Clear the old standings sidebar.
    document.querySelector(
        '.season-sidebar-standings'
    )?.remove();

    addSimulationButton();
};


