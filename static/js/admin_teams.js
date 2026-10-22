// ADMIN TEAM SEARCH

const teamSearch = document.getElementById("teamSearch");
const teamRows = document.querySelectorAll("#adminTeamsTable tr");
const teamSearchCount = document.getElementById("teamSearchCount");

function filterAdminTeams() {
    const searchTerm = teamSearch.value.trim().toLowerCase();

    let visibleTeams = 0;

    teamRows.forEach(row => {
        const teamName = row.cells[1].textContent.toLowerCase();
        const country = row.cells[2].textContent.toLowerCase();

        const matchesSearch =
            teamName.includes(searchTerm) ||
            country.includes(searchTerm);

        row.style.display = matchesSearch ? "" : "none";

        if (matchesSearch) {
            visibleTeams++;
        }
    });

    teamSearchCount.textContent =
        `${visibleTeams} of ${teamRows.length} teams shown`;
}

teamSearch.addEventListener("input", filterAdminTeams);

filterAdminTeams();