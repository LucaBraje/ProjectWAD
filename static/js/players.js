   const searchInput = document.getElementById("search");
        const teamFilter = document.getElementById("teamFilter");
        const positionFilter = document.getElementById("positionFilter");
        const sortFilter = document.getElementById("sortFilter");
        const tableBody = document.getElementById("playerTableBody");
        const resultCount = document.getElementById("resultCount");

        const playerModal = new bootstrap.Modal(
            document.getElementById("playerModal")
        );

        // Convert paths such as "teams_logos/example.webp"
        // into Flask static URLs. Full external URLs also work.
        function getImageUrl(path) {
            if (!path) return "";

            if (/^https?:\/\//i.test(path)) {
                return path;
            }

            return `/static/${path.replace(/^\/+/, "")}`;
        }

        function displayValue(value, decimals = 1) {
            if (value === null || value === undefined || value === "") {
                return "—";
            }

            const number = Number(value);

            if (!Number.isFinite(number)) {
                return "—";
            }

            return number.toFixed(decimals);
        }

        async function loadTeams() {
            try {
                const response = await fetch("/api/teams");

                if (!response.ok) {
                    throw new Error("Could not load teams.");
                }

                const teams = await response.json();

                teams.forEach(team => {
                    const option = document.createElement("option");
                    option.value = team.name;
                    option.textContent = team.name;
                    teamFilter.appendChild(option);
                });
            } catch (error) {
                console.error("Team loading error:", error);
            }
        }





        
        async function loadPlayers() {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="4" class="loading-message">
                        Loading players...
                    </td>
                </tr>
            `;

            const parameters = new URLSearchParams();

            parameters.set("search", searchInput.value.trim());
            parameters.set("team", teamFilter.value);
            parameters.set("position", positionFilter.value);

            try {
                const response = await fetch(
                    `/api/players?${parameters.toString()}`
                );

                if (!response.ok) {
                    throw new Error("Could not load players.");
                }

                const players = await response.json();

                // Sorting is performed in JavaScript after filtering.
                const sortOption = sortFilter.value;

                players.sort((a, b) => {
                    if (sortOption === "rating-desc") {
                        return Number(b.rating) - Number(a.rating);
                    }

                    if (sortOption === "rating-asc") {
                        return Number(a.rating) - Number(b.rating);
                    }

                    if (sortOption === "name-desc") {
                        return b.name.localeCompare(a.name);
                    }

                    return a.name.localeCompare(b.name);
                });

                tableBody.innerHTML = "";

                resultCount.textContent =
                    `${players.length} player${players.length === 1 ? "" : "s"} found`;

                if (players.length === 0) {
                    tableBody.innerHTML = `
                        <tr>
                            <td colspan="4" class="loading-message">
                                No players match your filters.
                            </td>
                        </tr>
                    `;
                    return;
                }

                players.forEach(player => {
                    const row = document.createElement("tr");

                    // Clicking anywhere on the row opens the popup.
                    row.addEventListener("click", () => {
                        showPlayerDetails(player);
                    });

                    // Player name
                    const nameCell = document.createElement("td");
                    const name = document.createElement("span");
                    name.className = "fw-semibold";
                    name.textContent = player.name;
                    nameCell.appendChild(name);

                    // Team logo and team name
                    const teamCell = document.createElement("td");
                    const teamContent = document.createElement("div");
                    teamContent.className = "team-cell";

                    if (player.team_image_url) {
                        const logo = document.createElement("img");
                        logo.className = "team-logo";
                        logo.src = getImageUrl(player.team_image_url);
                        logo.alt = `${player.team} logo`;
                        logo.onerror = () => logo.remove();
                        teamContent.appendChild(logo);
                    }

                    const teamName = document.createElement("span");
                    teamName.textContent = player.team || "Unknown";
                    teamContent.appendChild(teamName);
                    teamCell.appendChild(teamContent);

                    // Position
                    const positionCell = document.createElement("td");
                    positionCell.textContent = player.position || "—";

                    // Overall rating
                    const ratingCell = document.createElement("td");
                    const ratingBadge = document.createElement("span");
                    ratingBadge.className = "ovr-badge";
                    ratingBadge.textContent = player.rating ?? "—";
                    ratingCell.appendChild(ratingBadge);

                    row.append(
                        nameCell,
                        teamCell,
                        positionCell,
                        ratingCell
                    );

                    tableBody.appendChild(row);
                });
            } catch (error) {
                console.error("Player loading error:", error);

                tableBody.innerHTML = `
                    <tr>
                        <td colspan="4" class="loading-message text-danger">
                            Could not load players. Check that Flask is running.
                        </td>
                    </tr>
                `;

                resultCount.textContent = "Error loading players";
            }
        }

        function showPlayerDetails(player) {
            document.getElementById("modalPlayerName").textContent =
                player.name || "Unknown player";

            document.getElementById("modalTeamName").textContent =
                player.team || "Unknown team";

            document.getElementById("modalPosition").textContent =
                player.position || "Unknown position";

            document.getElementById("modalRating").textContent =
                player.rating ?? "—";

            document.getElementById("modalOffense").textContent =
                displayValue(player.offense, 0);

            document.getElementById("modalDefense").textContent =
                displayValue(player.defense, 0);

            document.getElementById("modalPoints").textContent =
                displayValue(player.points_per_game);

            document.getElementById("modalAssists").textContent =
                displayValue(player.assists_per_game);

            document.getElementById("modalRebounds").textContent =
                displayValue(player.rebounds_per_game);

            document.getElementById("modalBlocks").textContent =
                displayValue(player.blocks_per_game);

            document.getElementById("modalSteals").textContent =
                displayValue(player.steals_per_game);

            document.getElementById("modalFG").textContent =
                player.fg_percentage == null || player.fg_percentage === ""
                    ? "—"
                    : `${displayValue(player.fg_percentage)}%`;


const nationalityElement =
    document.getElementById("modalNationality");

nationalityElement.replaceChildren();

const flagUrl = getFlagUrl(player.nationality);
if (flagUrl) {
    const flag = document.createElement("img");
    flag.src = flagUrl;
    flag.alt = `${player.nationality} flag`;
    flag.width = 28;
    flag.style.marginRight = "8px";
    flag.onerror = () => flag.remove();

    nationalityElement.appendChild(flag);
}

nationalityElement.appendChild(
    document.createTextNode(player.nationality || "Unknown")
);


            // Player picture
            const picture = document.getElementById("modalPlayerPicture");
            const placeholder = document.getElementById("modalPicturePlaceholder");

            picture.hidden = true;
            picture.onerror = null;
            picture.removeAttribute("src");
            placeholder.hidden = false;

            if (player.picture_url) {
                picture.onerror = () => {
                    picture.hidden = true;
                    placeholder.hidden = false;
                };

                picture.onload = () => {
                    picture.hidden = false;
                    placeholder.hidden = true;
                };

                picture.src = getImageUrl(player.picture_url);
            }

            // Team logo
            const teamLogo = document.getElementById("modalTeamLogo");
            teamLogo.hidden = true;
            teamLogo.removeAttribute("src");

            if (player.team_image_url) {
                teamLogo.onerror = () => {
                    teamLogo.hidden = true;
                };

                teamLogo.onload = () => {
                    teamLogo.hidden = false;
                };

                teamLogo.src = getImageUrl(player.team_image_url);
            }

            playerModal.show();
        }

        // Search and filters reload the player list.
        searchInput.addEventListener("input", loadPlayers);
        teamFilter.addEventListener("change", loadPlayers);
        positionFilter.addEventListener("change", loadPlayers);

        // Sorting changes the displayed order without another API request.
        sortFilter.addEventListener("change", loadPlayers);

        async function initializePage() {
                await loadCountryCodes();
                await loadTeams();
                await loadPlayers();
        }

        initializePage();