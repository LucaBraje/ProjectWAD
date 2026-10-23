
'use strict';

// These keys must match the achievements defined in app.py.
const DRAFT_ACHIEVEMENTS = [
    {
        key: 'first_draft',
        name: 'First Draft',
        description: 'Complete your first draft simulation.',
        icon: '🏀'
    },
    {
        key: 'first_playoffs',
        name: 'Playoff Bound',
        description: 'Reach the playoffs.',
        icon: '🎯'
    },
    {
        key: 'first_final_four',
        name: 'Final Four',
        description: 'Reach the Final Four.',
        icon: '⭐'
    },
    {
        key: 'first_championship',
        name: 'EuroLeague Champion',
        description: 'Win a EuroLeague championship.',
        icon: '🏆'
    },
    {
        key: 'five_championships',
        name: 'Dynasty',
        description: 'Win five championships.',
        icon: '👑'
    },
    {
        key: 'elite_draft',
        name: 'Elite Draft',
        description: 'Build a team with a score of at least 180.',
        icon: '💎'
    },
    {
        key: 'perfect_positions',
        name: 'Perfect Fit',
        description: 'Use five players in their natural positions.',
        icon: '🧩'
    },
    {
        key: 'draft_veteran',
        name: 'Draft Veteran',
        description: 'Complete enough draft simulations to earn the veteran achievement.',
        icon: '🎖️'
    }
];

// Helper functions
const byId = id => document.getElementById(id);

const number = value => Number(value || 0);

const formatted = value =>
    number(value).toLocaleString(undefined, {
        maximumFractionDigits: 1
    });


// --------------------------------------
// CREATE A STATISTICS CARD
// --------------------------------------

function makeStat(label, value) {
    const card = document.createElement('div');
    card.className = 'stat-card';

    const amount = document.createElement('div');
    amount.className = 'stat-value';
    amount.textContent = value;

    const name = document.createElement('div');
    name.className = 'stat-label';
    name.textContent = label;

    card.append(amount, name);

    return card;
}


// --------------------------------------
// GET UNLOCKED ACHIEVEMENT KEYS
// --------------------------------------

function unlockedKeys(achievements) {
    const keys = new Set();

    if (!Array.isArray(achievements)) {
        return keys;
    }

    for (const item of achievements) {
        if (typeof item === 'string') {
            keys.add(item);
        } else if (item && typeof item === 'object') {
            const key = item.key ?? item.achievement_key;

            if (key && item.unlocked !== false) {
                keys.add(key);
            }
        }
    }

    return keys;
}


// --------------------------------------
// DISPLAY ACHIEVEMENTS
// --------------------------------------

function showAchievements(data) {
    const unlocked = unlockedKeys(data.achievements);

    const container = byId('draft-achievements');
    container.replaceChildren();

    for (const achievement of DRAFT_ACHIEVEMENTS) {
        const active = unlocked.has(achievement.key);

        const card = document.createElement('article');

        card.className =
            `achievement-card ${active ? 'unlocked' : 'locked'}`;

        const symbol = document.createElement('div');
        symbol.className = 'achievement-symbol';

        symbol.textContent = active
            ? achievement.icon
            : '🔒';

        const title = document.createElement('h4');
        title.textContent = achievement.name;

        const desc = document.createElement('p');
        desc.textContent = achievement.description;

        const status = document.createElement('div');
        status.className = 'achievement-state';

        status.textContent = active
            ? 'Unlocked'
            : 'Locked';

        card.append(symbol, title, desc, status);
        container.append(card);
    }

    const unlockedCount = DRAFT_ACHIEVEMENTS.filter(
        achievement => unlocked.has(achievement.key)
    ).length;

    byId('achievement-progress').textContent =
        `${unlockedCount} / ${DRAFT_ACHIEVEMENTS.length} Draft achievements unlocked`;
}


// --------------------------------------
// DISPLAY DRAFT MODE STATISTICS
// --------------------------------------

function showStats(data) {
    const stats = byId('draft-stats');

    stats.replaceChildren(
        makeStat('Drafts completed', formatted(data.total_drafts)),
        makeStat('Best team score', formatted(data.best_score)),
        makeStat('Average team score', formatted(data.average_score)),
        makeStat('Championships', formatted(data.championships)),
        makeStat('Playoff appearances', formatted(data.playoff_appearances)),
        makeStat('Final Four appearances', formatted(data.final_four_appearances))
    );

    stats.hidden = false;

    const status = byId('stats-status');

    if (number(data.total_drafts) === 0) {
        status.textContent =
            'No completed drafts yet. Play Draft Mode and simulate a season to start tracking your career.';

        status.hidden = false;
    } else {
        status.hidden = true;
    }

    
}


// --------------------------------------
// DISPLAY EQUIPPED TITLE
// --------------------------------------

function showTitle(data) {
    const title = data.equipped_title;

    if (typeof title === 'string' && title.trim()) {
        byId('profile-title').textContent =
            title.replaceAll('_', ' ');
    } else if (title && typeof title === 'object') {
        byId('profile-title').textContent =
            title.name ??
            title.title ??
            title.title_key ??
            'No title equipped';
    } else {
        byId('profile-title').textContent =
            'No title equipped';
    }
}


// --------------------------------------
// FETCH DATA FROM FLASK API
// --------------------------------------

async function loadProfile() {
    try {
        const response = await fetch('/api/draft/my-stats', {
            credentials: 'same-origin'
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();

        showStats(data);
        showAchievements(data);

    } catch (error) {
        console.error(
            'Could not load profile statistics:',
            error
        );

        byId('stats-status').textContent =
            'Unable to load your statistics. Please refresh the page.';

        byId('stats-status').hidden = false;

        byId('achievement-progress').textContent =
            'Unable to load achievements.';
    }
}


// --------------------------------------
// PROFILE TAB NAVIGATION
// --------------------------------------

document.addEventListener('DOMContentLoaded', () => {
    const tabs = document.querySelectorAll('.profile-tab');

    for (const tab of tabs) {
        tab.addEventListener('click', () => {
            const selected = tab.dataset.tab;

            for (const button of tabs) {
                const active = button === tab;

                button.classList.toggle('active', active);

                button.setAttribute(
                    'aria-selected',
                    String(active)
                );
            }

            byId('stats-panel').hidden =
                selected !== 'stats';

            byId('achievements-panel').hidden =
                selected !== 'achievements';
        });
    }

    // Load the user's real statistics on page load
    loadProfile();
});

// ==========================================
// PROFILE CUSTOMIZATION
// Favorite team and equipped titles
// ==========================================

function setProfileMessage(elementId, message, isError = false) {
    const element = document.getElementById(elementId);

    if (!element) return;

    element.textContent = message;
    element.style.color = isError ? '#ff7777' : '#FA5500';
}


// ------------------------------------------
// FAVORITE TEAM
// ------------------------------------------



// Convert database image paths into browser URLs.
function resolveTeamLogo(url) {
    if (!url) return '';

    const value = String(url).trim();

    // Full external URL or embedded image
    if (/^(https?:\/\/|data:image\/)/i.test(value)) {
        return value;
    }

    // Already starts with /static/
    if (value.startsWith('/')) {
        return value;
    }

    // Stored as static/images/...
    if (value.startsWith('static/')) {
        return '/' + value;
    }

    // Stored as images/... or just a filename
    return '/static/' + value;
}


function displayFavoriteTeam(team) {
    const name = document.getElementById('favorite-team-name');
    const logo = document.getElementById('favorite-team-logo');

    if (!name || !logo) return;

    name.textContent = team
        ? team.name
        : 'Choose your favorite team';

    logo.hidden = true;
    logo.removeAttribute('src');

    if (!team || !team.image_url) return;

    logo.onload = () => {
        logo.hidden = false;
    };

    logo.onerror = () => {
        console.warn(
            'Could not load team logo:',
            team.name,
            team.image_url
        );
        logo.hidden = true;
    };

    logo.src = resolveTeamLogo(team.image_url);
}


async function loadFavoriteTeams() {
    const select = document.getElementById('favorite-team-select');

    if (!select) return;

    try {
        const response = await fetch('/api/profile/favorite-team');

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();

        select.replaceChildren();

        const empty = new Option('No favorite team', '');
        select.add(empty);

        for (const team of data.teams) {
            const option = new Option(team.name, String(team.id));
            select.add(option);
        }

        select.value = data.favorite_team_id == null
            ? ''
            : String(data.favorite_team_id);

        const selectedTeam = data.teams.find(
            team => team.id === data.favorite_team_id
        );

        displayFavoriteTeam(selectedTeam || null);

    } catch (error) {
        console.error('Failed to load favorite teams:', error);

        setProfileMessage(
            'favorite-team-message',
            'Could not load teams.',
            true
        );
    }
}


async function saveFavoriteTeam() {
    const select = document.getElementById('favorite-team-select');
    const button = document.getElementById('save-favorite-team');

    if (!select || !button) return;

    button.disabled = true;

    try {
        const teamId = select.value
            ? Number(select.value)
            : null;

        const response = await fetch('/api/profile/favorite-team', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'same-origin',
            body: JSON.stringify({
                team_id: teamId
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Unable to save favorite team.');
        }

        setProfileMessage(
            'favorite-team-message',
            'Favorite team saved successfully!'
        );

        await loadFavoriteTeams();

    } catch (error) {
        setProfileMessage(
            'favorite-team-message',
            error.message,
            true
        );
    } finally {
        button.disabled = false;
    }
}


// ------------------------------------------
// PLAYER TITLES
// ------------------------------------------


function displayEquippedTitle(titleName) {
    const headerTitle = document.getElementById('profile-title');

    if (headerTitle) {
        headerTitle.textContent = titleName || 'Choose a title';
    }
}


async function loadProfileTitles() {
    const select = document.getElementById('title-select');

    if (!select) return;

    try {
        const response = await fetch('/api/profile/titles');

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();

        select.replaceChildren();
        select.add(new Option('No title equipped', ''));

        for (const title of data.titles) {
            const option = new Option(
                title.unlocked
                    ? title.name
                    : `🔒 ${title.name} (Locked)`,
                title.key
            );

            option.disabled = !title.unlocked;

            select.add(option);
        }

        select.value = data.equipped_title || '';

        const currentTitle = data.titles.find(
            title => title.key === data.equipped_title
        );

        displayEquippedTitle(currentTitle?.name || null);

    } catch (error) {
        console.error('Failed to load titles:', error);

        setProfileMessage(
            'title-message',
            'Could not load titles.',
            true
        );
    }
}


async function equipProfileTitle() {
    const select = document.getElementById('title-select');
    const button = document.getElementById('equip-title-button');

    if (!select || !button) return;

    button.disabled = true;

    try {
        const titleKey = select.value || null;

        const response = await fetch('/api/profile/titles/equip', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'same-origin',
            body: JSON.stringify({
                title_key: titleKey
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Unable to equip title.');
        }

        displayEquippedTitle(data.title_name);

        setProfileMessage(
            'title-message',
            titleKey
                ? 'Title equipped successfully!'
                : 'Title unequipped.'
        );

        await loadProfileTitles();

    } catch (error) {
        setProfileMessage(
            'title-message',
            error.message,
            true
        );
    } finally {
        button.disabled = false;
    }
}


// ------------------------------------------
// INITIALIZE PROFILE CUSTOMIZATION
// ------------------------------------------

document.addEventListener('DOMContentLoaded', () => {
    loadFavoriteTeams();
    loadProfileTitles();

    document.getElementById('save-favorite-team')
        ?.addEventListener('click', saveFavoriteTeam);

    document.getElementById('equip-title-button')
        ?.addEventListener('click', equipProfileTitle);
});

document.addEventListener('DOMContentLoaded', () => {

    const favoriteButton =
        document.getElementById('favorite-team-button');

    const titleButton =
        document.getElementById('profile-title-button');

    const favoriteEditor =
        document.getElementById('favorite-team-editor');

    const titleEditor =
        document.getElementById('title-editor');

    favoriteButton?.addEventListener('click', () => {
        favoriteEditor.hidden = !favoriteEditor.hidden;
        titleEditor.hidden = true;
    });

    titleButton?.addEventListener('click', () => {
        titleEditor.hidden = !titleEditor.hidden;
        favoriteEditor.hidden = true;
    });

    document.getElementById('save-favorite-team')
        ?.addEventListener('click', () => {
            favoriteEditor.hidden = true;
        });

    document.getElementById('equip-title-button')
        ?.addEventListener('click', () => {
            titleEditor.hidden = true;
        });

});
