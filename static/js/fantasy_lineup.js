// ============================================================
// FANTASY MODE - STARTING FIVE AND CAPTAIN
// ============================================================

const starters = new Set(initialStarters);
let captainId = initialCaptain;

const positions = ["PG", "SG", "SF", "PF", "C"];

const startersContainer = document.getElementById("starters-container");
const benchContainer = document.getElementById("bench-container");
const lineupForm = document.getElementById("lineup-form");
const errorElement = document.getElementById("lineup-error");


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


function changeStarter(playerId) {
    if (!lineupEditable) return;

    const player = lineupPlayers.find(p => p.id === playerId);
    if (!player) return;

    if (starters.has(playerId)) {
        starters.delete(playerId);

        if (captainId === playerId) {
            captainId = null;
        }
    } else {
        // Replace the existing starter at this position.
        const current = lineupPlayers.find(
            p => starters.has(p.id) && p.position === player.position
        );

        if (current) {
            starters.delete(current.id);

            if (captainId === current.id) {
                captainId = null;
            }
        }

        starters.add(playerId);
    }

    renderLineup();
}


function changeCaptain(playerId) {
    if (!lineupEditable || !starters.has(playerId)) return;

    captainId = playerId;
    renderLineup();
}


function createPlayerCard(player) {
    const isStarter = starters.has(player.id);
    const isCaptain = captainId === player.id;

    const card = createElement(
        "div",
        "lineup-player" +
        (isStarter ? " is-starter" : "") +
        (isCaptain ? " is-captain" : "")
    );

    const photo = createElement("div", "lineup-photo");
    if (player.picture_url) {
        const image = document.createElement("img");
        image.src = /^(https?:\/\/|\/)/i.test(player.picture_url) ? player.picture_url : "/static/" + player.picture_url.replace(/^static\//, "");
        image.alt = player.name;
        image.loading = "lazy";
        image.onerror = () => image.remove();
        photo.appendChild(image);
    }
    const info = createElement("div", "lineup-player-info");

    info.appendChild(
        createElement("strong", "", player.name)
    );

    info.appendChild(
        createElement(
            "small",
            "",
            `${player.position} · ${player.team} · OVR ${player.rating}`
        )
    );

    const actions = createElement("div", "lineup-actions");

    const starterLabel = createElement("label");
    const starterCheckbox = document.createElement("input");

    starterCheckbox.type = "checkbox";
    starterCheckbox.name = "starters";
    starterCheckbox.value = player.id;
    starterCheckbox.checked = isStarter;
    starterCheckbox.disabled = !lineupEditable;

    starterCheckbox.addEventListener("change", () => {
        changeStarter(player.id);
    });

    starterLabel.append(
        starterCheckbox,
        document.createTextNode("Starter")
    );

    actions.appendChild(starterLabel);

    if (isStarter) {
        const captainLabel = createElement("label");
        const captainRadio = document.createElement("input");

        captainRadio.type = "radio";
        captainRadio.name = "captain";
        captainRadio.value = player.id;
        captainRadio.checked = isCaptain;
        captainRadio.disabled = !lineupEditable;

        captainRadio.addEventListener("change", () => {
            changeCaptain(player.id);
        });

        captainLabel.append(
            captainRadio,
            document.createTextNode("Captain")
        );

        actions.appendChild(captainLabel);
    }

    const badge = createElement("span", "lineup-ovr", String(player.rating));
    card.append(photo, badge, info, actions);
    if (isCaptain) card.append(createElement("span", "captain-badge", "C ×2"));

    return card;
}


function renderLineup() {
    startersContainer.replaceChildren();
    benchContainer.replaceChildren();

    for (const position of positions) {
        const positionPlayers = lineupPlayers.filter(
            player => player.position === position
        );

        const starter = positionPlayers.find(
            player => starters.has(player.id)
        );

        const bench = positionPlayers.find(
            player => !starters.has(player.id)
        );

        const starterHeading = createElement(
            "h3",
            "position-heading",
            position
        );

        const benchHeading = createElement(
            "h3",
            "position-heading",
            position
        );

        const courtSlot = createElement("div", "court-slot court-slot-" + position.toLowerCase());
        courtSlot.appendChild(starterHeading);
        if (starter) {
            courtSlot.appendChild(createPlayerCard(starter));
        } else {
            courtSlot.appendChild(createElement("p", "empty-position", "Choose a " + position));
        }
        startersContainer.appendChild(courtSlot);

        const benchSlot = createElement("div", "bench-slot");
        benchSlot.appendChild(benchHeading);
        if (bench) benchSlot.appendChild(createPlayerCard(bench));
        benchContainer.appendChild(benchSlot);
    }

    const valid = starters.size === 5 &&
        positions.every(position =>
            lineupPlayers.some(
                player => player.position === position &&
                          starters.has(player.id)
            )
        ) &&
        starters.has(captainId);

    errorElement.textContent = valid
        ? ""
        : "Select one starter per position and choose a captain.";
}


lineupForm.addEventListener("submit", event => {
    const valid = starters.size === 5 &&
        positions.every(position =>
            lineupPlayers.some(
                player => player.position === position &&
                          starters.has(player.id)
            )
        ) &&
        starters.has(captainId);

    if (!valid) {
        event.preventDefault();
        errorElement.textContent =
            "You must select five starters and one captain.";
    }
});


renderLineup();