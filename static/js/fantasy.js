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

function renderMarket() {

    marketElement.replaceChildren();

    const search = searchInput.value.toLowerCase().trim();
    const position = positionFilter.value;
    const teamId = teamFilter.value;

    const filteredPlayers = fantasyPlayers.filter(player => {

        const matchesSearch =
            player.name.toLowerCase().includes(search);

        const matchesPosition =
            !position || player.position === position;

        const matchesTeam =
            !teamId || String(player.team_id) === teamId;

        return matchesSearch && matchesPosition && matchesTeam;
    });

    for (const player of filteredPlayers) {

        const isSelected = selectedPlayers.has(player.id);

        const card = createElement(
            "div",
            "market-player" + (isSelected ? " selected" : "")
        );

        const info = createElement("div", "market-player-info");

        const name = createElement(
            "strong",
            "player-name",
            player.name
        );

        const details = createElement(
            "span",
            "player-details",
            `${player.position} · ${player.team} · OVR ${player.rating}`
        );

        info.append(name, details);

        const right = createElement("div", "market-player-actions");

        const price = createElement(
            "strong",
            "player-price",
            formatPrice(player.price)
        );

        const button = createElement(
            "button",
            "select-player-button",
            isSelected ? "Remove" : "Add"
        );

        button.type = "button";
        button.disabled = !fantasyEditable;

        button.addEventListener("click", () => {
            togglePlayer(player.id);
        });

        right.append(price, button);
        card.append(info, right);

        marketElement.appendChild(card);
    }

    if (filteredPlayers.length === 0) {
        marketElement.appendChild(
            createElement(
                "p",
                "empty-market",
                "No players match your filters."
            )
        );
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