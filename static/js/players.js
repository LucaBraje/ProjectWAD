
/* ==========================================
   DRAFT EUROLEAGUE — PLAYER DIRECTORY
========================================== */

document.addEventListener("DOMContentLoaded", () => {

    // =====================================
    // 1. ELEMENTS AND STATE
    // =====================================

    const tableBody = document.getElementById("playerTableBody");
    const resultCount = document.getElementById("resultCount");
    const searchInput = document.getElementById("search");
    const teamFilter = document.getElementById("teamFilter");
    const positionFilter = document.getElementById("positionFilter");
    const sortFilter = document.getElementById("sortFilter");

    const modalElement = document.getElementById("playerModal");
    const playerModal = bootstrap.Modal.getOrCreateInstance(modalElement);

    let allPlayers = [];
    const playerById = new Map();


    // =====================================
    // 2. HELPER FUNCTIONS
    // =====================================

    function escapeHTML(value) {
        return String(value ?? "").replace(/[&<>"']/g, char => ({
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#39;"
        }[char]));
    }

    function number(value) {
        const parsed = Number(value);
        return Number.isFinite(parsed) ? parsed : 0;
    }

    function decimal(value) {
        return number(value).toFixed(1);
    }

    // Convert database image paths into usable URLs.
    function imagePath(path) {
        if (!path) return "";

        const value = String(path).trim();

        if (/^https?:\/\//i.test(value) || value.startsWith("/")) {
            return value;
        }

        return `/static/${value.replace(/^static\//, "")}`;
    }

    function setText(id, value) {
        const element = document.getElementById(id);

        if (element) {
            element.textContent = value ?? "";
        }
    }


    // =====================================
    // 3. NATIONALITY FLAGS
    // =====================================

    // Country names used in the database.
    const countryCodes = {
        "albania": "al",
        "algeria": "dz",
        "angola": "ao",
        "argentina": "ar",
        "armenia": "am",
        "australia": "au",
        "austria": "at",
        "bahamas": "bs",
        "belarus": "by",
        "belgium": "be",
        "bosnia and herzegovina": "ba",
        "bosnia": "ba",
        "brazil": "br",
        "bulgaria": "bg",
        "cameroon": "cm",
        "canada": "ca",
        "cape verde": "cv",
        "croatia": "hr",
        "cuba": "cu",
        "cyprus": "cy",
        "czech republic": "cz",
        "czechia": "cz",
        "denmark": "dk",
        "dominican republic": "do",
        "egypt": "eg",
        "estonia": "ee",
        "finland": "fi",
        "france": "fr",
        "georgia": "ge",
        "germany": "de",
        "ghana": "gh",
        "greece": "gr",
        "guinea": "gn",
        "hungary": "hu",
        "iceland": "is",
        "ireland": "ie",
        "israel": "il",
        "italy": "it",
        "ivory coast": "ci",
        "cote d'ivoire": "ci",
        "japan": "jp",
        "kosovo": "xk",
        "latvia": "lv",
        "lebanon": "lb",
        "lithuania": "lt",
        "luxembourg": "lu",
        "mali": "ml",
        "mexico": "mx",
        "montenegro": "me",
        "morocco": "ma",
        "netherlands": "nl",
        "new zealand": "nz",
        "nigeria": "ng",
        "north macedonia": "mk",
        "norway": "no",
        "poland": "pl",
        "portugal": "pt",
        "puerto rico": "pr",
        "romania": "ro",
        "russia": "ru",
        "senegal": "sn",
        "serbia": "rs",
        "slovakia": "sk",
        "slovenia": "si",
        "south africa": "za",
        "south sudan": "ss",
        "spain": "es",
        "sweden": "se",
        "switzerland": "ch",
        "tunisia": "tn",
        "turkey": "tr",
        "turkiye": "tr",
        "türkiye": "tr",
        "ukraine": "ua",
        "united arab emirates": "ae",
        "united kingdom": "gb",
        "great britain": "gb",
        "england": "gb",
        "united states": "us",
        "united states of america": "us",
        "usa": "us",
        "uruguay": "uy",
        "venezuela": "ve"
    };

    function getCountryCode(country) {
        const normalized = String(country || "")
            .trim()
            .toLowerCase()
            .normalize("NFD")
            .replace(/[\u0300-\u036f]/g, "");

        return countryCodes[normalized] || "";
    }

    function getFlagURL(country) {
        const code = getCountryCode(country);

        if (!code) return "";

        return `https://flagcdn.com/w40/${code}.png`;
    }

    function flagHTML(country) {
        const flag = getFlagURL(country);

        if (!flag) return "";

        return `
            <img
                class="player-country-flag"
                src="${escapeHTML(flag)}"
                alt="${escapeHTML(country)} flag"
                title="${escapeHTML(country)}"
                loading="lazy"
                onerror="this.hidden=true"
            >
        `;
    }


    // =====================================
    // 4. PLAYER PICTURES
    // =====================================

    function playerPictureHTML(player) {
        const picture = imagePath(player.picture_url);

        if (!picture) {
            return `
                <span class="roster-picture-placeholder">
                    EL
                </span>
            `;
        }

        return `
            <img
                class="roster-player-picture"
                src="${escapeHTML(picture)}"
                alt="${escapeHTML(player.name)}"
                loading="lazy"
                onerror="this.hidden=true;this.nextElementSibling.hidden=false"
            >
            <span class="roster-picture-placeholder" hidden>
                EL
            </span>
        `;
    }


    // =====================================
    // 5. CLUB LOGOS
    // =====================================

    function teamLogoHTML(player) {
        const logo = imagePath(player.team_image_url);

        if (!logo) {
            return `
                <span class="directory-team-fallback">
                    EL
                </span>
            `;
        }

        return `
            <img
                class="directory-team-logo"
                src="${escapeHTML(logo)}"
                alt="${escapeHTML(player.team || "Club")} logo"
                loading="lazy"
                onerror="this.hidden=true;this.nextElementSibling.hidden=false"
            >
            <span class="directory-team-fallback" hidden>
                EL
            </span>
        `;
    }


    // =====================================
    // 6. BUILD PLAYER TABLE ROW
    // =====================================

    function renderPlayerRow(player) {
        return `
            <tr
                data-player-id="${escapeHTML(player.id)}"
                tabindex="0"
                aria-label="View ${escapeHTML(player.name)} statistics"
            >

                <!-- PLAYER: PHOTO + NAME + FLAG -->
                <td>
                    <div class="roster-player">

                        ${playerPictureHTML(player)}

                        <span class="roster-player-name">
                            ${escapeHTML(player.name)}
                        </span>

                        ${flagHTML(player.nationality)}

                    </div>
                </td>

                <!-- TEAM: LOGO + NAME -->
                <td>
                    <div class="directory-team-cell">

                        ${teamLogoHTML(player)}

                        <span class="directory-team-name">
                            ${escapeHTML(player.team || "Free Agent")}
                        </span>

                    </div>
                </td>

                <!-- POSITION -->
                <td>
                    <span class="position-tag">
                        ${escapeHTML(player.position)}
                    </span>
                </td>

                <!-- OVERALL RATING -->
                <td>
                    <span class="rating-badge">
                        ${number(player.rating)}
                    </span>
                </td>

                <!-- ATTRIBUTES -->
                <td>${number(player.offense)}</td>
                <td>${number(player.defense)}</td>

                <!-- PER-GAME STATISTICS -->
                <td>${decimal(player.points_per_game)}</td>
                <td>${decimal(player.assists_per_game)}</td>
                <td>${decimal(player.rebounds_per_game)}</td>
                <td>${decimal(player.blocks_per_game)}</td>
                <td>${decimal(player.steals_per_game)}</td>
                <td>${decimal(player.fg_percentage)}%</td>
                <!-- ADDITIONAL SEASON STATISTICS -->

                <td>${number(player.games_played)}</td>
                <td>${number(player.total_points)}</td>
                <td>${number(player.total_assists)}</td>
                <td>${number(player.total_rebounds)}</td>
                <td>${number(player.total_blocks)}</td>
                <td>${number(player.total_steals)}</td>
                <td>${number(player.total_turnovers)}</td>
                <td>${number(player.total_fgm)}</td>
                <td>${number(player.total_fga)}</td>
            </tr>
        `;
    }


    // =====================================
    // 7. FILTER AND SORT PLAYERS
    // =====================================

    function renderPlayers() {
        const search = searchInput.value.trim().toLowerCase();
        const team = teamFilter.value;
        const position = positionFilter.value;
        const sort = sortFilter.value;

        const filteredPlayers = allPlayers.filter(player => {
            const playerName = String(player.name || "").toLowerCase();

            return (
                playerName.includes(search) &&
                (!team || player.team === team) &&
                (!position || player.position === position)
            );
        });

        
        // =====================================
        // SORT PLAYERS BY SELECTED ATTRIBUTE
        // =====================================

        filteredPlayers.sort((a, b) => {

            // Alphabetical sorting
            const textFields = ["name", "team", "position"];

            const separator = sort.lastIndexOf("-");
            const field = sort.substring(0, separator);
            const direction = sort.substring(separator + 1);

            const multiplier = direction === "asc" ? 1 : -1;

            // Sort names, teams and positions alphabetically
            if (textFields.includes(field)) {

                const valueA = String(a[field] || "");
                const valueB = String(b[field] || "");

                return (
                    valueA.localeCompare(valueB) * multiplier ||
                    a.name.localeCompare(b.name)
                );
            }

            // Sort numerical attributes and statistics
            const valueA = number(a[field]);
            const valueB = number(b[field]);

            return (
                (valueA - valueB) * multiplier ||
                a.name.localeCompare(b.name)
            );

        });


        resultCount.textContent =
            `${filteredPlayers.length} PLAYERS FOUND`;

        if (filteredPlayers.length === 0) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="21" class="loading-message">
                        No players found.
                    </td>
                </tr>
            `;
            return;
        }

        tableBody.innerHTML =
            filteredPlayers.map(renderPlayerRow).join("");
    }


    // =====================================
    // 8. PLAYER PROFILE MODAL
    // =====================================

    function openPlayerModal(player) {
        // Identity
        setText("modalPlayerName", player.name);
        setText("modalTeamName", player.team);
        setText("modalPosition", player.position);
        setText("modalRating", player.rating);

        // Attributes
        setText("modalOffense", player.offense);
        setText("modalDefense", player.defense);

        // Statistics
// Statistics
setText("modalGamesPlayed", number(player.games_played));

setText("modalPoints", decimal(player.points_per_game));
setText("modalAssists", decimal(player.assists_per_game));
setText("modalRebounds", decimal(player.rebounds_per_game));
setText("modalBlocks", decimal(player.blocks_per_game));
setText("modalSteals", decimal(player.steals_per_game));
setText("modalFG", `${decimal(player.fg_percentage)}%`);

        // Nationality and flag
        const nationality = document.getElementById("modalNationality");
        const country = player.nationality || "Unknown";
        const flag = getFlagURL(country);

        nationality.textContent = "";

        if (flag) {
            const flagImage = document.createElement("img");

            flagImage.src = flag;
            flagImage.alt = `${country} flag`;
            flagImage.width = 26;
            flagImage.height = 18;
            flagImage.style.marginRight = "8px";
            flagImage.style.borderRadius = "3px";

            flagImage.onerror = () => flagImage.remove();

            nationality.appendChild(flagImage);
        }

        nationality.appendChild(
            document.createTextNode(country)
        );

        // Player photo
        const picture = document.getElementById("modalPlayerPicture");
        const placeholder = document.getElementById("modalPicturePlaceholder");

        picture.hidden = true;
        placeholder.hidden = false;

        picture.onload = () => {
            picture.hidden = false;
            placeholder.hidden = true;
        };

        picture.onerror = () => {
            picture.hidden = true;
            placeholder.hidden = false;
        };

        if (player.picture_url) {
            picture.src = imagePath(player.picture_url);
        } else {
            picture.removeAttribute("src");
        }

        // Club logo
        const logo = document.getElementById("modalTeamLogo");

        logo.hidden = true;

        logo.onload = () => {
            logo.hidden = false;
        };

        logo.onerror = () => {
            logo.hidden = true;
        };

        if (player.team_image_url) {
            logo.src = imagePath(player.team_image_url);
        } else {
            logo.removeAttribute("src");
        }

        playerModal.show();
    }


    // =====================================
    // 9. CLICKABLE PLAYER ROWS
    // =====================================

    function selectPlayerFromRow(row) {
        if (!row) return;

        const player = playerById.get(row.dataset.playerId);

        if (player) {
            openPlayerModal(player);
        }
    }

    // Mouse click
    tableBody.addEventListener("click", event => {
        const row = event.target.closest("tr[data-player-id]");
        selectPlayerFromRow(row);
    });

    // Keyboard support
    tableBody.addEventListener("keydown", event => {
        if (event.key !== "Enter" && event.key !== " ") {
            return;
        }

        const row = event.target.closest("tr[data-player-id]");

        if (row) {
            event.preventDefault();
            selectPlayerFromRow(row);
        }
    });


    // =====================================
    // 10. SEARCH AND FILTER EVENTS
    // =====================================

    searchInput.addEventListener("input", renderPlayers);
    teamFilter.addEventListener("change", renderPlayers);
    positionFilter.addEventListener("change", renderPlayers);
    sortFilter.addEventListener("change", renderPlayers);

    
    // =====================================
    // CLICKABLE TABLE HEADER SORTING
    // =====================================

    const tableHeaders = document.querySelectorAll(
        "#playerTable thead th[data-sort]"
    );

const numericFields = new Set([
    "rating",
    "offense",
    "defense",
    "points_per_game",
    "assists_per_game",
    "rebounds_per_game",
    "blocks_per_game",
    "steals_per_game",
    "fg_percentage",

    // Additional season statistics
    "games_played",
    "total_points",
    "total_assists",
    "total_rebounds",
    "total_blocks",
    "total_steals",
    "total_turnovers",
    "total_fgm",
    "total_fga"
]);

    function updateSortIndicators() {
        const selectedSort = sortFilter.value;
        const separator = selectedSort.lastIndexOf("-");
        const activeField = selectedSort.substring(0, separator);
        const direction = selectedSort.substring(separator + 1);

        tableHeaders.forEach(header => {
            const isActive = header.dataset.sort === activeField;

            header.classList.toggle(
                "sort-asc",
                isActive && direction === "asc"
            );

            header.classList.toggle(
                "sort-desc",
                isActive && direction === "desc"
            );

            header.setAttribute(
                "aria-sort",
                isActive
                    ? (direction === "asc" ? "ascending" : "descending")
                    : "none"
            );
        });
    }

    function sortByHeader(header) {
        const field = header.dataset.sort;
        const currentSort = sortFilter.value;
        const separator = currentSort.lastIndexOf("-");

        const currentField = currentSort.substring(0, separator);
        const currentDirection = currentSort.substring(separator + 1);

        let direction;

        if (currentField === field) {
            // Clicking the same header reverses sorting.
            direction = currentDirection === "desc" ? "asc" : "desc";
        } else {
            // Numerical fields default to highest first.
            // Text fields default to alphabetical A-Z.
            direction = numericFields.has(field) ? "desc" : "asc";
        }

        sortFilter.value = `${field}-${direction}`;

        renderPlayers();
        updateSortIndicators();
    }

    tableHeaders.forEach(header => {
        // Mouse click
        header.addEventListener("click", () => {
            sortByHeader(header);
        });

        // Keyboard support
        header.addEventListener("keydown", event => {
            if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                sortByHeader(header);
            }
        });
    });

    // Keep header arrows synchronized with the dropdown.
    sortFilter.addEventListener("change", updateSortIndicators);

    // Display the initial active sorting column.
    updateSortIndicators();


    // =====================================
    // 11. LOAD PLAYERS FROM FLASK API
    // =====================================

    async function loadPlayers() {
        try {
            const response = await fetch("/api/players");

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            allPlayers = await response.json();

            playerById.clear();

            allPlayers.forEach(player => {
                playerById.set(String(player.id), player);
            });

            // Build team filter from available clubs.
            const teams = [
                ...new Set(
                    allPlayers
                        .map(player => player.team)
                        .filter(Boolean)
                )
            ].sort((a, b) => a.localeCompare(b));

            teamFilter.innerHTML =
                '<option value="">All teams</option>' +
                teams.map(team => `
                    <option value="${escapeHTML(team)}">
                        ${escapeHTML(team)}
                    </option>
                `).join("");

            renderPlayers();

        } catch (error) {
            console.error("Unable to load players:", error);

            resultCount.textContent = "Unable to load players";

            tableBody.innerHTML = `
                <tr>
                    <td colspan="21" class="loading-message">
                        Unable to load players.
                        Please refresh the page.
                    </td>
                </tr>
            `;
        }
    }


    // =====================================
    // 12. INITIALIZE DIRECTORY
    // =====================================

    loadPlayers();

});
