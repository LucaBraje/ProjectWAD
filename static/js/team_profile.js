
document.addEventListener("DOMContentLoaded", () => {

    const table = document.getElementById("rosterTable");
    const headers = table.querySelectorAll("thead th");
    const tbody = table.querySelector("tbody");

    let currentColumn = 2; // OVR
    let ascending = false;  // Highest first

    headers.forEach((header, columnIndex) => {

        header.addEventListener("click", () => {

            // Reverse order if the same column is clicked
            if (currentColumn === columnIndex) {
                ascending = !ascending;
            } else {
                currentColumn = columnIndex;

                // Text sorts A-Z, numbers highest first
                ascending = header.dataset.sort === "text";
            }

            const rows = Array.from(tbody.querySelectorAll("tr"));

            rows.sort((rowA, rowB) => {

                const valueA = rowA.cells[columnIndex].textContent.trim();
                const valueB = rowB.cells[columnIndex].textContent.trim();

                if (header.dataset.sort === "number") {
                    const numberA = parseFloat(valueA) || 0;
                    const numberB = parseFloat(valueB) || 0;

                    return ascending
                        ? numberA - numberB
                        : numberB - numberA;
                }

                return ascending
                    ? valueA.localeCompare(valueB)
                    : valueB.localeCompare(valueA);
            });

            // Put the rows back in sorted order
            rows.forEach(row => tbody.appendChild(row));

            // Update sorting arrows
            headers.forEach(th => {
                th.classList.remove("sort-asc", "sort-desc");
            });

            header.classList.add(
                ascending ? "sort-asc" : "sort-desc"
            );

        });
    });

    // Show that OVR is the default sorting column
    headers[2].classList.add("sort-desc");

});
// DISPLAY TEAM AND PLAYER NATIONAL FLAGS

document.querySelectorAll("[data-country]").forEach(flag => {
    const countryName = flag.dataset.country;
    const flagUrl = getFlagUrl(countryName);

    if (flagUrl) {
        flag.src = flagUrl;
    } else {
        flag.style.display = "none";
    }
});