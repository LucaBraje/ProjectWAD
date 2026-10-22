
// ADMIN PLAYER SEARCH

const playerSearch = document.getElementById("playerSearch");
const playerRows = document.querySelectorAll("#adminPlayersTable tr");
const playerSearchCount = document.getElementById("playerSearchCount");

function filterAdminPlayers() {
    const searchTerm = playerSearch.value.trim().toLowerCase();

    let visiblePlayers = 0;

    playerRows.forEach(row => {
        const playerName = row.cells[1].textContent.toLowerCase();
        const teamName = row.cells[2].textContent.toLowerCase();

        const matchesSearch =
            playerName.includes(searchTerm) ||
            teamName.includes(searchTerm);

        row.style.display = matchesSearch ? "" : "none";

        if (matchesSearch) {
            visiblePlayers++;
        }
    });

    playerSearchCount.textContent =
        `${visiblePlayers} of ${playerRows.length} players shown`;
}

// Filter immediately as the user types
playerSearch.addEventListener("input", filterAdminPlayers);

// Show the initial player count
filterAdminPlayers();
