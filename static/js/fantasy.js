// ============================================================
// FANTASY MODE - SQUAD BUILDER
// ============================================================

const selectedPlayers = new Set(initialSelectedIds);

const positions = ["PG", "SG", "SF", "PF", "C"];

const marketElement = document.getElementById("player-market");
const squadElement = document.getElementById("squad-list");

const searchInput = document.getElementById("player-search");
const positionFilter = document.getElementById("position-filter");
const teamFilter = document.getElementById("team-filter");

const budgetDisplay = document.getElementById("budget-display");
const playersDisplay = document.getElementById("players-display");

const saveButton = document.getElementById("save-squad-button");
const selectedInput = document.getElementById("selected-player-ids");
const warningElement = document.getElementById("squad-warning");


// ============================================================
// HELPERS
// ============================================================

function formatPrice(price) {
    return (price / 100).toFixed(2) + "M";
}


function getSelectedPlayers() {
    return fantasyPlayers.filter(player =>
        selectedPlayers.has(player.id)
    );
}


function getTotalCost() {
    return getSelectedPlayers().reduce(
        (total, player) => total + player.price,
        0
    );
}


function getPositionCount(position) {
    return getSelectedPlayers().filter(
        player => player.position === position
    ).length;
}


function getTeamCount(teamId) {
    return getSelectedPlayers().filter(
        player => player.team_id === teamId
    ).length;
}


function createElement(tag, className, text) {
    const element = document.createElement(tag);

    if (className) {
        element.className = className;
    }

    if (text !== undefined) {
        element.textContent = text;
    }

    return element;
}


// ============================================================
// PLAYER SELECTION
// ============================================================

function togglePlayer(playerId) {

    if (!fantasyEditable) {
        return;
    }

    const player = fantasyPlayers.find(
        item => item.id === playerId
    );

    if (!player) {
        return;
    }

    warningElement.textContent = "";

    if (selectedPlayers.has(playerId)) {

        selectedPlayers.delete(playerId);

    } else {

        if (selectedPlayers.size >= 10) {
            warningElement.textContent =
                "You can only select 10 players.";
            return;
        }

        if (getPositionCount(player.position) >= 2) {
            warningElement.textContent =
                `You already have 2 ${player.position} players.`;
            return;
        }

        if (getTeamCount(player.team_id) >= 4) {
            warningElement.textContent =
                "Maximum 4 players from the same team.";
            return;
        }

        if (getTotalCost() + player.price > fantasyBudget) {
            warningElement.textContent =
                "Not enough budget for this player.";
            return;
        }

        selectedPlayers.add(playerId);
    }

    renderEverything();
}


// ============================================================
// PLAYER MARKET
// ============================================================

function assetUrl(path) {
    if (!path) return "";
    const value = String(path).trim();
    if (value.startsWith("http://") || value.startsWith("https://") || value.startsWith("//") || value.startsWith("/")) return value;
    return "/static/" + value.replace("static/", "");
}

function ratingTier(value) {
    const n = Number(value) || 0;
    return n >= 95 ? "mythic" : n >= 90 ? "legendary" :
           n >= 85 ? "epic" : n >= 80 ? "rare" :
           n >= 75 ? "uncommon" : n >= 70 ? "common" : "basic";
}

function renderMarket() {
    marketElement.replaceChildren();
    const search = searchInput.value.toLowerCase().trim();
    const position = positionFilter.value;
    const teamId = teamFilter.value;
    const filtered = fantasyPlayers.filter(player =>
        player.name.toLowerCase().includes(search) &&
        (!position || player.position === position) &&
        (!teamId || String(player.team_id) === teamId)
    );

    const count = document.getElementById("market-count");
    if (count) count.textContent = `${filtered.length} PLAYERS AVAILABLE`;

    for (const player of filtered) {
        const chosen = selectedPlayers.has(player.id);
        const card = createElement("article",
            `market-player rarity-${ratingTier(player.rating)}${chosen ? " selected" : ""}`);
        const photo = createElement("div", "market-player-photo");
        const photoUrl = assetUrl(player.picture_url);
        if (photoUrl) {
            const image = createElement("img");
            image.src = photoUrl;
            image.alt = player.name;
            image.loading = "lazy";
            image.onerror = () => { image.remove(); photo.textContent = "🏀"; };
            photo.append(image);
        } else {
            photo.textContent = "🏀";
        }

        const content = createElement("div", "market-player-info");
        const top = createElement("div", "market-player-top");
        top.append(
            createElement("span", "market-rating", String(player.rating ?? "—")),
            createElement("span", "market-position", player.position || "—")
        );
        content.append(
            top,
            createElement("strong", "player-name", player.name),
            createElement("span", "player-details", player.team || "EuroLeague"),
            createElement("span", "market-average",
                `${Number(player.points_per_game || 0).toFixed(1)} PPG · ${Number(player.rebounds_per_game || 0).toFixed(1)} RPG · ${Number(player.assists_per_game || 0).toFixed(1)} APG`)
        );

        const actions = createElement("div", "market-player-actions");
        actions.append(createElement("strong", "player-price", formatPrice(player.price)));
        const button = createElement("button", "select-player-button", chosen ? "✓ SELECTED" : "+ ADD PLAYER");
        button.type = "button";
        button.disabled = !fantasyEditable;
        button.setAttribute("aria-label", `${chosen ? "Remove" : "Add"} ${player.name}`);
        button.addEventListener("click", () => togglePlayer(player.id));
        actions.append(button);
        card.append(photo, content, actions);
        marketElement.append(card);
    }

    if (!filtered.length) {
        marketElement.append(createElement("p", "empty-market", "No players match your filters."));
    }
}

// ============================================================
// MY SQUAD
// ============================================================

function renderSquad() {

    squadElement.replaceChildren();

    const players = getSelectedPlayers();

    for (const position of positions) {

        const group = createElement("div", "position-group");

        const positionPlayers = players.filter(
            player => player.position === position
        );

        const heading = createElement(
            "h3",
            "position-heading",
            `${position} (${positionPlayers.length}/2)`
        );

        group.appendChild(heading);

        for (const player of positionPlayers) {

            const row = createElement("div", "squad-player");

            const info = createElement(
                "span",
                "",
                `${player.name} · ${formatPrice(player.price)}`
            );

            row.appendChild(info);

            if (fantasyEditable) {

                const removeButton = createElement(
                    "button",
                    "remove-player-button",
                    "×"
                );

                removeButton.type = "button";

                removeButton.addEventListener("click", () => {
                    togglePlayer(player.id);
                });

                row.appendChild(removeButton);
            }

            group.appendChild(row);
        }

        for (let i = positionPlayers.length; i < 2; i++) {

            group.appendChild(
                createElement(
                    "div",
                    "empty-position",
                    "Empty player slot"
                )
            );
        }

        squadElement.appendChild(group);
    }
}


// ============================================================
// BUDGET AND VALIDATION
// ============================================================

function updateSummary() {

    const totalCost = getTotalCost();
    const remaining = fantasyBudget - totalCost;

    budgetDisplay.textContent = formatPrice(remaining);
    playersDisplay.textContent = `${selectedPlayers.size} / 10`;
    const progress = document.getElementById("fantasy-progress-fill");
    if (progress) progress.style.width = `${selectedPlayers.size * 10}%`;
    const budgetProgress = document.getElementById("fantasy-budget-fill");
    if (budgetProgress) budgetProgress.style.width =
        `${Math.max(0, Math.min(100, totalCost / fantasyBudget * 100))}%`;

    const validPositions = positions.every(
        position => getPositionCount(position) === 2
    );

    const validSquad =
        selectedPlayers.size === 10 &&
        validPositions &&
        remaining >= 0;

    if (saveButton) {
        saveButton.disabled = !validSquad;
    }

    if (selectedInput) {
        selectedInput.value = Array.from(selectedPlayers).join(",");
    }
}


// ============================================================
// RENDER EVERYTHING
// ============================================================

function renderEverything() {
    renderMarket();
    renderSquad();
    updateSummary();
}


// ============================================================
// FILTER EVENTS
// ============================================================

searchInput.addEventListener("input", renderMarket);
positionFilter.addEventListener("change", renderMarket);
teamFilter.addEventListener("change", renderMarket);


// ============================================================
// INITIAL RENDER
// ============================================================

renderEverything();