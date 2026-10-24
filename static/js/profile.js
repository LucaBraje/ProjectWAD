
'use strict';

// =====================================================
// DRAFT EUROLEAGUE — PROFILE PAGE
// =====================================================

// Achievement keys must match the Flask backend.
const DRAFT_ACHIEVEMENTS = [
    {
        key: 'first_draft',
        name: 'Rookie GM',
        description: 'Complete your first Draft Mode simulation.',
        icon: '🏀'
    },
    {
        key: 'first_playoffs',
        name: 'Playoff Contender',
        description: 'Qualify for the EuroLeague playoffs.',
        icon: '🎯'
    },
    {
        key: 'first_final_four',
        name: 'Final Four Veteran',
        description: 'Reach the EuroLeague Final Four.',
        icon: '⭐'
    },
    {
        key: 'first_championship',
        name: 'EuroLeague Champion',
        description: 'Win your first EuroLeague championship.',
        icon: '🏆'
    },
    {
        key: 'five_championships',
        name: 'Dynasty Builder',
        description: 'Win five EuroLeague championships.',
        icon: '👑'
    },
    {
        key: 'elite_draft',
        name: 'Draft Master',
        description: 'Build a team worth at least 180 points.',
        icon: '💎'
    },
    {
        key: 'perfect_positions',
        name: 'Perfect Architect',
        description: 'Draft five players in their natural positions.',
        icon: '🧩'
    },
    {
        key: 'draft_veteran',
        name: 'Draft Veteran',
        description: 'Complete 50 drafts.',
        icon: '🎖️'
    }
];

// =====================================================
// HELPERS
// =====================================================

const byId = id => document.getElementById(id);

const number = value => Number(value || 0);

const formatted = value =>
    number(value).toLocaleString(undefined, {
        maximumFractionDigits: 1
    });

function setMessage(id, text, isError = false) {
    const element = byId(id);

    if (!element) return;

    element.textContent = text;
    element.classList.toggle('error', isError);
    element.style.color = isError ? '#ff7777' : '#FA5500';
}

async function readApiResponse(response) {
    const contentType = response.headers.get('content-type') || '';

    if (!contentType.includes('application/json')) {
        throw new Error(
            response.redirected
                ? 'Your session may have expired. Please log in again.'
                : `Server returned an unexpected response (HTTP ${response.status}).`
        );
    }

    const data = await response.json();

    if (!response.ok) {
        throw new Error(
            data.error ||
            data.message ||
            `Request failed (HTTP ${response.status}).`
        );
    }

    return data;
}

// =====================================================
// STATISTICS
// =====================================================

function makeStat(label, value) {
    const card = document.createElement('div');
    card.className = 'stat-card';

    const valueElement = document.createElement('div');
    valueElement.className = 'stat-value';
    valueElement.textContent = value;

    const labelElement = document.createElement('div');
    labelElement.className = 'stat-label';
    labelElement.textContent = label;

    card.append(valueElement, labelElement);

    return card;
}

function showStats(data) {
    const stats = byId('draft-stats');
    const status = byId('stats-status');

    if (stats) {
        stats.replaceChildren(
            makeStat('Drafts completed', formatted(data.total_drafts)),
            makeStat('Best team score', formatted(data.best_score)),
            makeStat('Average team score', formatted(data.average_score)),
            makeStat('Championships', formatted(data.championships)),
            makeStat('Playoff appearances', formatted(data.playoff_appearances)),
            makeStat('Final Four appearances', formatted(data.final_four_appearances))
        );

        stats.hidden = false;
    }

    if (status) {
        const noDrafts = number(data.total_drafts) === 0;

        status.hidden = !noDrafts;

        if (noDrafts) {
            status.textContent =
                'No completed drafts yet. Play Draft Mode and simulate a season to start tracking your career.';
        }
    }
}

// =====================================================
// ACHIEVEMENTS
// =====================================================

function unlockedKeys(achievements) {
    const keys = new Set();

    if (!Array.isArray(achievements)) {
        return keys;
    }

    for (const item of achievements) {
        if (typeof item === 'string') {
            keys.add(item);
            continue;
        }

        if (item && typeof item === 'object') {
            const key = item.key ?? item.achievement_key;

            if (key && item.unlocked !== false) {
                keys.add(key);
            }
        }
    }

    return keys;
}

function showAchievements(data) {
    const container = byId('draft-achievements');
    const progress = byId('achievement-progress');

    const unlocked = unlockedKeys(data.achievements);

    if (container) {
        container.replaceChildren();

        for (const achievement of DRAFT_ACHIEVEMENTS) {
            const isUnlocked = unlocked.has(achievement.key);

            const card = document.createElement('article');
            card.className =
                `achievement-card ${isUnlocked ? 'unlocked' : 'locked'}`;

            const symbol = document.createElement('div');
            symbol.className = 'achievement-symbol';
            symbol.textContent = isUnlocked
                ? achievement.icon
                : '🔒';

            const title = document.createElement('h4');
            title.textContent = achievement.name;

            const description = document.createElement('p');
            description.textContent = achievement.description;

            const status = document.createElement('div');
            status.className = 'achievement-state';
            status.textContent = isUnlocked
                ? 'Unlocked'
                : 'Locked';

            card.append(symbol, title, description, status);
            container.append(card);
        }
    }

    if (progress) {
        const count = DRAFT_ACHIEVEMENTS.filter(
            achievement => unlocked.has(achievement.key)
        ).length;

        progress.textContent =
            `${count} / ${DRAFT_ACHIEVEMENTS.length} Draft achievements unlocked`;
    }
}

// =====================================================
// LOAD DRAFT STATISTICS AND ACHIEVEMENTS
// =====================================================

// =====================================================
// HIGHER OR LOWER — PROFILE STATISTICS
// =====================================================

const HL_PROFILE_ACHIEVEMENTS = [
    {
        key: 'hl_first_game',
        name: 'First Comparison',
        description: 'Complete your first Higher or Lower game.',
        icon: '🏀'
    },
    {
        key: 'hl_streak_5',
        name: 'Getting Warm',
        description: 'Reach a streak of 5.',
        icon: '🔥'
    },
    {
        key: 'hl_streak_10',
        name: 'On Fire',
        description: 'Reach a streak of 10.',
        icon: '⚡'
    },
    {
        key: 'hl_streak_20',
        name: 'EuroLeague Expert',
        description: 'Reach a streak of 20.',
        icon: '🏆'
    },
    {
        key: 'hl_correct_50',
        name: 'Sharp Shooter',
        description: 'Make 50 correct guesses.',
        icon: '🎯'
    },
    {
        key: 'hl_games_25',
        name: 'Dedicated Analyst',
        description: 'Complete 25 games.',
        icon: '🎖️'
    }
];


async function loadHigherLowerProfile() {

    const statsContainer = byId('hl-profile-stats');
    const achievementsContainer = byId('hl-profile-achievements');
    const status = byId('hl-profile-status');
    const progress = byId('hl-achievement-progress');

    try {

        const response = await fetch(
            '/api/games/higher-or-lower/my-stats',
            { credentials: 'same-origin' }
        );

        const data = await readApiResponse(response);

        // ---------------------------------------------
        // STATISTICS
        // ---------------------------------------------

        if (statsContainer) {

            statsContainer.replaceChildren(
                makeStat('Best Streak', formatted(data.best_streak)),
                makeStat('Games Played', formatted(data.total_games)),
                makeStat('Correct Guesses', formatted(data.total_correct)),
                makeStat('Accuracy', `${formatted(data.accuracy)}%`)
            );

            statsContainer.hidden = false;
        }

        if (status) {
            status.hidden = data.total_games > 0
                || data.total_correct > 0;

            if (!status.hidden) {
                status.textContent =
                    'No completed games yet. Play Higher or Lower to start your record!';
            }
        }

        // ---------------------------------------------
        // ACHIEVEMENTS
        // ---------------------------------------------

        const unlocked = new Set(
            (data.achievements || [])
                .filter(item => item.unlocked)
                .map(item => item.key)
        );

        if (achievementsContainer) {

            achievementsContainer.replaceChildren();

            for (const achievement of HL_PROFILE_ACHIEVEMENTS) {

                const isUnlocked = unlocked.has(achievement.key);

                const card = document.createElement('article');

                card.className =
                    `achievement-card ${isUnlocked ? 'unlocked' : 'locked'}`;

                const symbol = document.createElement('div');
                symbol.className = 'achievement-symbol';
                symbol.textContent = isUnlocked
                    ? achievement.icon
                    : '🔒';

                const title = document.createElement('h4');
                title.textContent = achievement.name;

                const description = document.createElement('p');
                description.textContent = achievement.description;

                const state = document.createElement('div');
                state.className = 'achievement-state';
                state.textContent = isUnlocked
                    ? 'Unlocked'
                    : 'Locked';

                card.append(symbol, title, description, state);

                achievementsContainer.append(card);
            }
        }

        if (progress) {
            progress.textContent =
                `${unlocked.size} / ${HL_PROFILE_ACHIEVEMENTS.length} ` +
                'Higher or Lower achievements unlocked';
        }

    } catch (error) {

        console.error('Higher or Lower profile error:', error);

        if (status) {
            status.hidden = false;
            status.textContent =
                'Unable to load Higher or Lower statistics.';
        }

        if (progress) {
            progress.textContent =
                'Unable to load Higher or Lower achievements.';
        }
    }
}

async function loadProfile() {
    try {
        const response = await fetch('/api/draft/my-stats', {
            credentials: 'same-origin'
        });

        const data = await readApiResponse(response);

        showStats(data);
        showAchievements(data);

    } catch (error) {
        console.error('Profile statistics error:', error);

        const status = byId('stats-status');
        const progress = byId('achievement-progress');

        if (status) {
            status.hidden = false;
            status.textContent =
                'Unable to load statistics. Please refresh the page.';
        }

        if (progress) {
            progress.textContent =
                'Unable to load achievements.';
        }
    }
}

// =====================================================
// PROFILE TABS
// =====================================================

function initializeProfileTabs() {
    const tabs = document.querySelectorAll('.profile-tab');

    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const selected = tab.dataset.tab;

            tabs.forEach(button => {
                const active = button === tab;

                button.classList.toggle('active', active);
                button.setAttribute('aria-selected', String(active));
            });

            const statsPanel = byId('stats-panel');
            const achievementsPanel = byId('achievements-panel');

            if (statsPanel) {
                statsPanel.hidden = selected !== 'stats';
            }

            if (achievementsPanel) {
                achievementsPanel.hidden =
                    selected !== 'achievements';
            }
        });
    });
}

// =====================================================
// GAME MODES — CLOSED BY DEFAULT
// =====================================================

function initializeGameSections() {
    document.querySelectorAll('.game-section').forEach(section => {
        section.open = false;
    });
}

// =====================================================
// FAVORITE TEAM — LOGO
// =====================================================

function resolveTeamLogo(url) {
    if (!url) return '';

    const value = String(url).trim();

    if (/^(https?:\/\/|data:image\/)/i.test(value)) {
        return value;
    }

    if (value.startsWith('/')) {
        return value;
    }

    if (value.startsWith('static/')) {
        return '/' + value;
    }

    return '/static/' + value;
}

function displayFavoriteTeam(team) {
    const name = byId('favorite-team-name');
    const logo = byId('favorite-team-logo');

    if (name) {
        name.textContent = team
            ? team.name
            : 'Choose your favorite team';
    }

    if (!logo) return;

    logo.hidden = true;
    logo.removeAttribute('src');

    if (!team?.image_url) return;

    logo.onload = () => {
        logo.hidden = false;
    };

    logo.onerror = () => {
        logo.hidden = true;
    };

    logo.src = resolveTeamLogo(team.image_url);
}

// =====================================================
// FAVORITE TEAM — LOAD
// =====================================================

async function loadFavoriteTeams() {
    const select = byId('favorite-team-select');

    if (!select) return;

    try {
        const response = await fetch(
            '/api/profile/favorite-team',
            { credentials: 'same-origin' }
        );

        const data = await readApiResponse(response);

        const teams = Array.isArray(data.teams)
            ? data.teams
            : [];

        select.replaceChildren();
        select.add(new Option('No favorite team', ''));

        teams.forEach(team => {
            select.add(
                new Option(team.name, String(team.id))
            );
        });

        const selectedId = data.favorite_team_id;

        select.value = selectedId == null
            ? ''
            : String(selectedId);

        const selectedTeam = teams.find(
            team => String(team.id) === String(selectedId)
        );

        displayFavoriteTeam(selectedTeam || null);
        setMessage('favorite-team-message', '');

    } catch (error) {
        console.error('Favorite team loading error:', error);

        setMessage(
            'favorite-team-message',
            error.message,
            true
        );
    }
}

// =====================================================
// FAVORITE TEAM — SAVE
// =====================================================

async function saveFavoriteTeam() {
    const select = byId('favorite-team-select');
    const button = byId('save-favorite-team');

    if (!select || !button) return;

    button.disabled = true;

    setMessage(
        'favorite-team-message',
        'Saving favorite team...'
    );

    try {
        const teamId = select.value
            ? Number(select.value)
            : null;

        const response = await fetch(
            '/api/profile/favorite-team',
            {
                method: 'POST',
                credentials: 'same-origin',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    team_id: teamId
                })
            }
        );

        await readApiResponse(response);
        await loadFavoriteTeams();

        setMessage(
            'favorite-team-message',
            'Favorite team saved successfully!'
        );

    } catch (error) {
        console.error('Favorite team saving error:', error);

        setMessage(
            'favorite-team-message',
            error.message,
            true
        );

    } finally {
        button.disabled = false;
    }
}

// =====================================================
// PLAYER TITLES — DISPLAY
// =====================================================

function displayEquippedTitle(titleName) {
    const element = byId('profile-title');

    if (element) {
        element.textContent =
            titleName || 'No title equipped';
    }
}

// =====================================================
// PLAYER TITLES — LOAD
// =====================================================

async function loadProfileTitles() {
    const select = byId('title-select');

    if (!select) return;

    try {
        const response = await fetch(
            '/api/profile/titles',
            { credentials: 'same-origin' }
        );

        const data = await readApiResponse(response);

        const titles = Array.isArray(data.titles)
            ? data.titles
            : [];

        select.replaceChildren();
        select.add(new Option('No title equipped', ''));

        titles.forEach(title => {
            const option = new Option(
                title.unlocked
                    ? title.name
                    : `🔒 ${title.name} (Locked)`,
                title.key
            );

            option.disabled = !title.unlocked;
            select.add(option);
        });

        select.value = data.equipped_title || '';

        const equipped = titles.find(
            title => title.key === data.equipped_title
        );

        displayEquippedTitle(equipped?.name || null);
        setMessage('title-message', '');

    } catch (error) {
        console.error('Title loading error:', error);

        setMessage(
            'title-message',
            error.message,
            true
        );
    }
}

// =====================================================
// PLAYER TITLES — EQUIP
// =====================================================

async function equipProfileTitle() {
    const select = byId('title-select');
    const button = byId('equip-title-button');

    if (!select || !button) return;

    button.disabled = true;
    setMessage('title-message', 'Saving title...');

    try {
        const titleKey = select.value || null;

        const response = await fetch(
            '/api/profile/titles/equip',
            {
                method: 'POST',
                credentials: 'same-origin',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    title_key: titleKey
                })
            }
        );

        const data = await readApiResponse(response);

        displayEquippedTitle(data.title_name || null);
        await loadProfileTitles();

        setMessage(
            'title-message',
            titleKey
                ? 'Title equipped successfully!'
                : 'Title unequipped successfully!'
        );

    } catch (error) {
        console.error('Title saving error:', error);

        setMessage(
            'title-message',
            error.message,
            true
        );

    } finally {
        button.disabled = false;
    }
}

// =====================================================
// EDIT PROFILE — USERNAME AND EMAIL ONLY
// =====================================================

function initializeProfileSettings() {
    const settings = byId('profile-settings');
    const editButton = byId('edit-profile-button');
    const closeButton = byId('close-profile-settings');

    if (!settings || !editButton) {
        console.warn('Edit Profile panel is missing.');
        return;
    }

    function setSettingsOpen(open) {
        settings.hidden = !open;

        editButton.setAttribute(
            'aria-expanded',
            String(open)
        );

        if (open) {
            settings.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        } else {
            editButton.focus({ preventScroll: true });
        }
    }

    // Only the Edit Profile button opens account settings.
    editButton.addEventListener('click', () => {
        setSettingsOpen(settings.hidden);
    });

    closeButton?.addEventListener('click', () => {
        setSettingsOpen(false);
    });

    document.addEventListener('keydown', event => {
        if (event.key === 'Escape' && !settings.hidden) {
            setSettingsOpen(false);
        }
    });
}

// =====================================================
// FAVORITE TEAM AND TITLE — ORIGINAL SEPARATE EDITORS
// =====================================================

function initializeCustomizationEditors() {
    const favoriteButton = byId('favorite-team-button');
    const favoriteEditor = byId('favorite-team-editor');

    const titleButton = byId('profile-title-button');
    const titleEditor = byId('title-editor');

    // Keep the editors outside the Edit Profile panel.
    // In the current HTML, they already sit after that panel.
    // This also corrects their location if an older script
    // previously moved them into the settings container.

    const settings = byId('profile-settings');

    if (settings && favoriteEditor && settings.contains(favoriteEditor)) {
        settings.after(favoriteEditor);
    }

    if (settings && titleEditor && settings.contains(titleEditor)) {
        favoriteEditor
            ? favoriteEditor.after(titleEditor)
            : settings.after(titleEditor);
    }

    function setEditorOpen(editor, button, open) {
        if (!editor || !button) return;

        editor.hidden = !open;

        button.setAttribute(
            'aria-expanded',
            String(open)
        );

        if (open) {
            editor.scrollIntoView({
                behavior: 'smooth',
                block: 'nearest'
            });
        }
    }

    // Clicking the favorite team badge opens only its editor.
    favoriteButton?.addEventListener('click', () => {
        if (!favoriteEditor) return;

        const shouldOpen = favoriteEditor.hidden;

        setEditorOpen(favoriteEditor, favoriteButton, shouldOpen);

        // Close the title editor while selecting a team.
        if (shouldOpen) {
            setEditorOpen(titleEditor, titleButton, false);
        }
    });

    // Clicking the title badge opens only its editor.
    titleButton?.addEventListener('click', () => {
        if (!titleEditor) return;

        const shouldOpen = titleEditor.hidden;

        setEditorOpen(titleEditor, titleButton, shouldOpen);

        // Close the favorite team editor while selecting a title.
        if (shouldOpen) {
            setEditorOpen(favoriteEditor, favoriteButton, false);
        }
    });

    // Escape closes either editor.
    document.addEventListener('keydown', event => {
        if (event.key !== 'Escape') return;

        if (favoriteEditor && !favoriteEditor.hidden) {
            setEditorOpen(favoriteEditor, favoriteButton, false);
        }

        if (titleEditor && !titleEditor.hidden) {
            setEditorOpen(titleEditor, titleButton, false);
        }
    });
}

// =====================================================
// ACCOUNT SETTINGS — SAVE USERNAME AND EMAIL
// =====================================================

function initializeAccountSettings() {
    const form = byId('account-settings-form');
    const usernameInput = byId('edit-username');
    const emailInput = byId('edit-email');
    const button = byId('save-account-settings');

    if (!form || !usernameInput || !emailInput || !button) {
        console.warn('Account settings form elements are missing.');
        return;
    }

    form.addEventListener('submit', async event => {
        event.preventDefault();

        const username = usernameInput.value.trim();
        const email = emailInput.value.trim();

        // ---------------------------------------------
        // VALIDATION
        // ---------------------------------------------

        if (username.length < 3) {
            setMessage(
                'account-settings-message',
                'Username must contain at least 3 characters.',
                true
            );
            return;
        }

        if (username.length > 50) {
            setMessage(
                'account-settings-message',
                'Username cannot exceed 50 characters.',
                true
            );
            return;
        }

        if (!email || email.length > 120) {
            setMessage(
                'account-settings-message',
                'Email must contain between 1 and 120 characters.',
                true
            );
            return;
        }

        if (!emailInput.checkValidity()) {
            setMessage(
                'account-settings-message',
                'Please enter a valid email address.',
                true
            );
            return;
        }

        // ---------------------------------------------
        // SAVE ACCOUNT
        // ---------------------------------------------

        button.disabled = true;

        setMessage(
            'account-settings-message',
            'Saving account details...'
        );

        try {
            const response = await fetch(
                '/api/profile/account',
                {
                    method: 'POST',
                    credentials: 'same-origin',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        username: username,
                        email: email
                    })
                }
            );

            const data = await readApiResponse(response);

            const updatedUsername = data.username || username;
            const updatedEmail = data.email || email;

            // Update the visible profile header.
            const nameElement = document.querySelector(
                '.profile-name-row h1'
            );

            const emailElement = document.querySelector(
                '.profile-email'
            );

            const avatarElement = document.querySelector(
                '.profile-avatar'
            );

            if (nameElement) {
                nameElement.textContent = updatedUsername;
            }

            if (emailElement) {
                emailElement.textContent = updatedEmail;
            }

            if (avatarElement) {
                avatarElement.textContent =
                    updatedUsername.charAt(0).toUpperCase();
            }

            // Synchronize the form with saved values.
            usernameInput.value = updatedUsername;
            emailInput.value = updatedEmail;

            setMessage(
                'account-settings-message',
                'Account details updated successfully!'
            );

        } catch (error) {
            console.error('Account update error:', error);

            setMessage(
                'account-settings-message',
                error.message,
                true
            );

        } finally {
            button.disabled = false;
        }
    });
}

// =====================================================
// INITIALIZE PROFILE PAGE
// =====================================================

document.addEventListener('DOMContentLoaded', () => {

    // 1. Collapse all game mode sections.
    initializeGameSections();

    // 2. Initialize Statistics / Achievements tabs.
    initializeProfileTabs();

    // 3. Edit Profile controls only username and email.
    initializeProfileSettings();

    // 4. Favorite team and title use their own editors.
    initializeCustomizationEditors();

    // 5. Enable account settings form.
    initializeAccountSettings();

    // 6. Connect favorite team save button.
    byId('save-favorite-team')
        ?.addEventListener('click', saveFavoriteTeam);

    // 7. Connect equipped title save button.
    byId('equip-title-button')
        ?.addEventListener('click', equipProfileTitle);

    // 8. Load profile data from Flask.

loadProfile();
loadHigherLowerProfile();
loadFavoriteTeams();
loadProfileTitles();


    console.log(
        'Draft EuroLeague Profile initialized successfully.'
    );
});
