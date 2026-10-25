// ============================================================
// EUROLeague Schedule — API-driven frontend
// ============================================================

document.addEventListener("DOMContentLoaded", () => {

    const gamesContainer =
        document.getElementById("games-container");

    const weekTitle =
        document.getElementById("week-title");

    const weekSubtitle =
        document.getElementById("week-subtitle");

    const seasonName =
        document.getElementById("season-name");

    const seasonStatus =
        document.getElementById("season-status");

    const previousButton =
        document.getElementById("previous-week");

    const nextButton =
        document.getElementById("next-week");

    const weekSelector =
        document.getElementById("week-selector");

    const message =
        document.getElementById("schedule-message");

    let currentWeek = 1;
    let totalWeeks = 38;

    // Prevent older requests from overwriting newer ones
    let requestNumber = 0;


    // --------------------------------------------------------
    // Create week dropdown
    // --------------------------------------------------------

    function populateWeekSelector() {

        weekSelector.innerHTML = "";

        for (let i = 1; i <= totalWeeks; i++) {

            const option = document.createElement("option");

            option.value = i;
            option.textContent = `Round ${i}`;

            weekSelector.appendChild(option);
        }
    }


    // --------------------------------------------------------
    // Escape HTML to safely display database values
    // --------------------------------------------------------

    function escapeHTML(value) {

        return String(value ?? "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }


    // --------------------------------------------------------
    // Team logo
    // --------------------------------------------------------

function createTeamLogo(team) {

    const name = escapeHTML(team.name);

    if (team.image_url) {

        let logoPath = team.image_url.replace(/\\/g, "/");

        // Support paths such as:
        // static/images/teams/real_madrid.png
        // /static/images/teams/real_madrid.png
        // images/teams/real_madrid.png

        if (logoPath.startsWith("/static/")) {
            // Already a valid Flask static URL
        }
        else if (logoPath.startsWith("static/")) {
            logoPath = "/" + logoPath;
        }
        else if (!logoPath.startsWith("http")) {
            logoPath = "/static/" + logoPath.replace(/^\/+/, "");
        }

        return `
            <img
                class="team-logo"
                src="${escapeHTML(logoPath)}"
                alt="${name} logo"
                loading="lazy"
                onerror="this.style.display='none'"
            >
        `;
    }

    const initials = team.name
        .split(/\s+/)
        .slice(0, 2)
        .map(word => word[0])
        .join("")
        .toUpperCase();

    return `
        <div class="team-placeholder">
            ${escapeHTML(initials)}
        </div>
    `;
}

    // --------------------------------------------------------
    // Render individual game
    // --------------------------------------------------------

    function createGameCard(game, index) {

        const finished =
            game.status === "finished" ||
            game.status === "finalized";

        const hasScore =
            game.home_score !== null &&
            game.away_score !== null;

        const displayScore = finished && hasScore;

        const centerContent = displayScore
            ? `
                <span class="game-score">
                    ${escapeHTML(game.home_score)}
                    -
                    ${escapeHTML(game.away_score)}
                </span>
              `
            : `<span class="vs-label">VS</span>`;

        return `
            <article class="game-card">

                <div class="game-top">

                    <span class="game-number">
                        GAME ${index + 1}
                    </span>

                    <span class="game-status">
                        ${escapeHTML(game.status)}
                    </span>

                </div>

                <div class="game-matchup">

                    <div class="game-team home">

                        ${createTeamLogo(game.home_team)}

                        <span class="team-name">
                            ${escapeHTML(game.home_team.name)}
                        </span>

                    </div>

                    <div class="game-center">
                        ${centerContent}
                    </div>

                    <div class="game-team away">

                        ${createTeamLogo(game.away_team)}

                        <span class="team-name">
                            ${escapeHTML(game.away_team.name)}
                        </span>

                    </div>

                </div>

            </article>
        `;
    }


    // --------------------------------------------------------
    // Navigation state
    // --------------------------------------------------------

    function updateNavigation() {

        previousButton.disabled = currentWeek <= 1;
        nextButton.disabled = currentWeek >= totalWeeks;

        weekSelector.value = String(currentWeek);
    }


    // --------------------------------------------------------
    // Fetch games from Flask API
    // --------------------------------------------------------

    async function loadWeek(weekNumber) {

        if (weekNumber < 1 || weekNumber > totalWeeks) {
            return;
        }

        const thisRequest = ++requestNumber;

        message.classList.remove("error");
        message.textContent = "Loading fixtures...";

        gamesContainer.innerHTML = "";

        previousButton.disabled = true;
        nextButton.disabled = true;
        weekSelector.disabled = true;

        try {

            const response = await fetch(
                `/api/schedule/${weekNumber}`
            );

            if (!response.ok) {
                throw new Error(
                    `Could not load round ${weekNumber}.`
                );
            }

            const data = await response.json();

            if (thisRequest !== requestNumber) {
                return;
            }

            currentWeek = data.week;
            totalWeeks = data.total_weeks;

            seasonName.textContent = data.season.name;
            seasonStatus.textContent =
                data.status.toUpperCase();

            weekTitle.textContent =
                `ROUND ${currentWeek}`;

            weekSubtitle.textContent =
                `${data.games.length} games • Week ${currentWeek} of ${totalWeeks}`;

            populateWeekSelector();

            gamesContainer.innerHTML = data.games
                .map((game, index) =>
                    createGameCard(game, index)
                )
                .join("");

            message.textContent = "";

        } catch (error) {

            if (thisRequest !== requestNumber) {
                return;
            }

            message.textContent = error.message;
            message.classList.add("error");

        } finally {

            if (thisRequest === requestNumber) {
                weekSelector.disabled = false;
                updateNavigation();
            }
        }
    }


    // --------------------------------------------------------
    // Buttons
    // --------------------------------------------------------

    previousButton.addEventListener("click", () => {
        loadWeek(currentWeek - 1);
    });

    nextButton.addEventListener("click", () => {
        loadWeek(currentWeek + 1);
    });

    weekSelector.addEventListener("change", event => {
        loadWeek(Number(event.target.value));
    });


    // --------------------------------------------------------
    // Initial load
    // --------------------------------------------------------

    populateWeekSelector();
    loadWeek(1);

});