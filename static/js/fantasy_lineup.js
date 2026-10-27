// ============================================================
// DRAFT EUROLEAGUE — FANTASY LINEUP
// Starting five, bench substitutions and captain selection
// ============================================================

const starters = new Set(initialStarters);
let captainId = initialCaptain;

const positions = ["PG", "SG", "SF", "PF", "C"];

const startersContainer = document.getElementById("starters-container");
const benchContainer = document.getElementById("bench-container");
const lineupForm = document.getElementById("lineup-form");
const errorElement = document.getElementById("lineup-error");

function createElement(tag, className = "", text) {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (text !== undefined) element.textContent = text;
    return element;
}

function getPlayer(playerId) {
    return lineupPlayers.find(player => player.id === playerId);
}

function getPositionPlayers(position) {
    return lineupPlayers.filter(player => player.position === position);
}

function getStarter(position) {
    return getPositionPlayers(position).find(player => starters.has(player.id));
}

function getBench(position) {
    return getPositionPlayers(position).find(player => !starters.has(player.id));
}

// ============================================================
// SUBSTITUTIONS
// ============================================================

function changeStarter(playerId) {
    if (!lineupEditable) return;

    const player = getPlayer(playerId);
    if (!player) return;

    const isStarter = starters.has(playerId);

    if (isStarter) {
        // Clicking a starter promotes the bench player at that position.
        const replacement = getBench(player.position);

        if (!replacement) return;

        starters.delete(playerId);
        starters.add(replacement.id);

        // Captaincy follows the position if the captain is substituted.
        if (captainId === playerId) {
            captainId = replacement.id;
        }
    } else {
        // Clicking a bench player replaces the current starter.
        const currentStarter = getStarter(player.position);

        if (currentStarter) {
            starters.delete(currentStarter.id);

            if (captainId === currentStarter.id) {
                captainId = playerId;
            }
        }

        starters.add(playerId);
    }

    renderLineup();
}

// ============================================================
// CAPTAIN SELECTION
// ============================================================

function changeCaptain(playerId) {
    if (!lineupEditable || !starters.has(playerId)) return;

    captainId = playerId;
    renderLineup();
}

// ============================================================
// PLAYER CARD
// ============================================================

function createPlayerCard(player) {
    const isStarter = starters.has(player.id);
    const isCaptain = captainId === player.id;

    const card = createElement(
        "div",
        "lineup-player" +
        (isStarter ? " is-starter" : "") +
        (isCaptain ? " is-captain" : "")
    );

    // Player image
    const photo = createElement("div", "lineup-photo");

    if (player.picture_url) {
        const image = document.createElement("img");

        image.src = /^(https?:\/\/|\/)/i.test(player.picture_url)
            ? player.picture_url
            : "/static/" + player.picture_url.replace(/^static\//, "");

        image.alt = player.name;
        image.loading = "lazy";
        image.onerror = () => image.remove();

        photo.appendChild(image);
    }

    // Player information
    const info = createElement("div", "lineup-player-info");

    info.appendChild(
        createElement("strong", "", player.name)
    );

    info.appendChild(
        createElement("small", "", player.team)
    );

    // Overall rating
    const rating = createElement("div", "lineup-rating");
    rating.appendChild(
        createElement("strong", "", String(player.rating))
    );
    rating.appendChild(
        createElement("small", "", "OVR")
    );

    // Actions
    const actions = createElement("div", "lineup-actions");

    if (lineupEditable) {
        const swapButton = createElement(
            "button",
            "lineup-swap-btn",
            "↔ SWAP"
        );

        swapButton.type = "button";
        swapButton.disabled = isStarter
            ? !getBench(player.position)
            : false;

        swapButton.addEventListener("click", () => {
            changeStarter(player.id);
        });

        actions.appendChild(swapButton);

        if (isStarter) {
            const captainButton = createElement(
                "button",
                "lineup-captain-btn" +
                (isCaptain ? " active" : ""),
                isCaptain ? "★ CAPTAIN" : "☆ MAKE CAPTAIN"
            );

            captainButton.type = "button";

            captainButton.addEventListener("click", () => {
                changeCaptain(player.id);
            });

            actions.appendChild(captainButton);
        }
    }

    card.append(photo, info, rating, actions);

    if (isCaptain) {
        card.appendChild(
            createElement("span", "captain-badge", "C ×2")
        );
    }

    // Preserve the existing Flask form field names.
    if (isStarter) {
        const starterInput = document.createElement("input");
        starterInput.type = "hidden";
        starterInput.name = "starters";
        starterInput.value = player.id;
        card.appendChild(starterInput);
    }

    if (isCaptain) {
        const captainInput = document.createElement("input");
        captainInput.type = "hidden";
        captainInput.name = "captain";
        captainInput.value = player.id;
        card.appendChild(captainInput);
    }

    return card;
}

// ============================================================
// RENDER STARTING FIVE AND BENCH
// ============================================================

function renderLineup() {
    startersContainer.replaceChildren();
    benchContainer.replaceChildren();

    for (const position of positions) {
        const starter = getStarter(position);
        const benchPlayers = getPositionPlayers(position).filter(
            player => !starters.has(player.id)
        );

        // Starting five
        const courtSlot = createElement(
            "div",
            "court-slot court-slot-" + position.toLowerCase()
        );

        courtSlot.appendChild(
            createElement("h3", "position-heading", position)
        );

        if (starter) {
            courtSlot.appendChild(createPlayerCard(starter));
        } else {
            courtSlot.appendChild(
                createElement(
                    "p",
                    "empty-position",
                    "NO " + position + " SELECTED"
                )
            );
        }

        startersContainer.appendChild(courtSlot);

        // Bench
        for (const benchPlayer of benchPlayers) {
            const benchSlot = createElement("div", "bench-slot");

            benchSlot.appendChild(
                createElement("h3", "position-heading", position)
            );

            benchSlot.appendChild(createPlayerCard(benchPlayer));

            benchContainer.appendChild(benchSlot);
        }
    }

    updateValidation();
}

// ============================================================
// VALIDATION
// ============================================================

function isLineupValid() {
    return starters.size === 5 &&
        positions.every(position => getStarter(position)) &&
        starters.has(captainId);
}

function updateValidation() {
    errorElement.textContent = isLineupValid()
        ? ""
        : "Select five starters and one captain.";
}

// ============================================================
// SAVE LINEUP
// ============================================================

lineupForm.addEventListener("submit", event => {
    if (!lineupEditable || !isLineupValid()) {
        event.preventDefault();

        errorElement.textContent =
            "You must select five starters and one captain.";
    }
});

// Initial render
renderLineup();