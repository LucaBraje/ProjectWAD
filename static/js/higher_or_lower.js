
/* =====================================================
   DRAFT EUROLEAGUE — HIGHER OR LOWER
   Classic Endless Mode
===================================================== */

document.addEventListener("DOMContentLoaded", () => {

    // =================================================
    // ELEMENTS
    // =================================================

    const byId = (id) => document.getElementById(id);

    const setup = byId("hl-setup");
    const game = byId("hl-game");
    const gameOver = byId("hl-game-over");
    const errorElement = byId("hl-error");

    const startButton = byId("hl-start-button");
    const restartButton = byId("hl-restart-button");

    const higherButton = byId("hl-higher-button");
    const lowerButton = byId("hl-lower-button");

    const streakElement = byId("hl-streak");
    const bestElement = byId("hl-best");

    const feedbackElement = byId("hl-feedback");

    const statButtons = document.querySelectorAll(
        ".hl-stat-option"
    );

    // =================================================
    // GAME STATE
    // =================================================

    let selectedStat = "random";
    let currentStreak = 0;
    let sessionBest = 0;
    let isProcessing = false;

    // =================================================
    // HELPERS
    // =================================================

    function show(element) {
        element.classList.remove("hidden");
    }

    function hide(element) {
        element.classList.add("hidden");
    }

    function showError(message) {
        errorElement.textContent = message;
        show(errorElement);
    }

    function clearError() {
        errorElement.textContent = "";
        hide(errorElement);
    }

    function updateScoreboard() {
        streakElement.textContent = currentStreak;
        bestElement.textContent = sessionBest;
    }

    function setGuessButtonsDisabled(disabled) {
        higherButton.disabled = disabled;
        lowerButton.disabled = disabled;
    }

    function setFeedback(message, type = "") {
        feedbackElement.textContent = message;
        feedbackElement.className = "hl-feedback";

        if (type) {
            feedbackElement.classList.add(type);
        }
    }

    function wait(milliseconds) {
        return new Promise((resolve) => {
            setTimeout(resolve, milliseconds);
        });
    }

    async function requestApi(url, options = {}) {

        const response = await fetch(url, {
            credentials: "same-origin",
            ...options,
            headers: {
                "Content-Type": "application/json",
                ...(options.headers || {})
            }
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(
                data.error || "Something went wrong."
            );
        }

        return data;
    }

    // =================================================
    // PLAYER DISPLAY
    // =================================================

    function displayPlayer(number, player) {

        byId(`hl-player-${number}-name`).textContent =
            player.name || "Unknown Player";

        byId(`hl-player-${number}-team`).textContent =
            player.team || "EuroLeague";

        const imageElement = byId(
            `hl-player-${number}-image`
        );

        imageElement.alt = player.name || "Player";

        imageElement.onerror = () => {
            imageElement.removeAttribute("src");
        };

        if (player.picture_url) {
            imageElement.src = player.picture_url;
        } else {
            imageElement.removeAttribute("src");
        }
    }

    function displayRound(roundData) {

        displayPlayer("one", roundData.player_one);
        displayPlayer("two", roundData.player_two);

        byId("hl-stat-title").textContent =
            roundData.stat_label;

        byId("hl-stat-label-one").textContent =
            roundData.stat_label.toUpperCase();

        byId("hl-stat-label-two").textContent =
            roundData.stat_label.toUpperCase();

        byId("hl-player-one-value").textContent =
            roundData.player_one.value_display;

        byId("hl-player-two-value").textContent = "?";

        byId("hl-round").textContent =
            roundData.round;

        byId("hl-question").textContent =
            `Does ${roundData.player_two.name} have a ` +
            `higher or lower ${roundData.stat_label.toLowerCase()} ` +
            `than ${roundData.player_one.name}?`;

        setFeedback("");
        setGuessButtonsDisabled(false);

        currentStreak = roundData.streak;
        sessionBest = Math.max(
            sessionBest,
            roundData.best || 0,
            currentStreak
        );

        updateScoreboard();
        document.querySelectorAll('.hl-player-card')
    .forEach(card => {
        card.classList.remove('hl-correct', 'hl-wrong');
    });

document.querySelectorAll('.hl-stat-display')
    .forEach(display => {
        display.classList.remove('hl-revealed');
    });

animatePlayerCards();
    }


// =================================================
// VISUAL EFFECTS
// =================================================

function animatePlayerCards() {

    document.querySelectorAll('.hl-player-card')
        .forEach(card => {

            card.classList.remove('hl-enter');

            // Restart the animation.
            void card.offsetWidth;

            card.classList.add('hl-enter');
        });
}


function animateAnswer(correct) {

    const cards = document.querySelectorAll(
        '.hl-player-card'
    );

    const secondCard = cards[1];

    if (!secondCard) return;

    secondCard.classList.remove(
        'hl-enter',
        'hl-correct',
        'hl-wrong'
    );

    void secondCard.offsetWidth;

    secondCard.classList.add(
        correct ? 'hl-correct' : 'hl-wrong'
    );

    const statDisplay = secondCard.querySelector(
        '.hl-stat-display'
    );

    if (statDisplay) {
        statDisplay.classList.remove('hl-revealed');
        void statDisplay.offsetWidth;
        statDisplay.classList.add('hl-revealed');
    }

    if (correct) {

        streakElement.classList.remove('hl-score-pop');
        void streakElement.offsetWidth;
        streakElement.classList.add('hl-score-pop');
    }
}


function showAchievementNotifications(achievements) {

    if (!Array.isArray(achievements)) return;

    achievements.forEach((achievement, index) => {

        const toast = document.createElement('div');

        toast.className = 'hl-achievement-toast';
        toast.setAttribute('role', 'status');

        const icon = document.createElement('div');
        icon.className = 'hl-toast-icon';
        icon.textContent = '🏆';

        const content = document.createElement('div');

        const label = document.createElement('strong');
        label.textContent = 'ACHIEVEMENT UNLOCKED';

        const name = document.createElement('span');
        name.textContent = achievement.name;

        content.append(label, name);
        toast.append(icon, content);

        toast.style.bottom = `${25 + index * 90}px`;

        document.body.append(toast);

        setTimeout(() => toast.remove(), 4500);
    });
}


    // =================================================
    // STAT SELECTION
    // =================================================

    statButtons.forEach((button) => {

        button.addEventListener("click", () => {

            if (isProcessing) {
                return;
            }

            statButtons.forEach((item) => {
                item.classList.remove("active");
            });

            button.classList.add("active");

            selectedStat = button.dataset.stat;
        });
    });

    // =================================================
    // START GAME
    // =================================================

    async function startGame() {

        if (isProcessing) {
            return;
        }

        isProcessing = true;
        startButton.disabled = true;
        restartButton.disabled = true;

        clearError();

        try {

            const data = await requestApi(
                "/api/games/higher-or-lower/start",
                {
                    method: "POST",
                    body: JSON.stringify({
                        stat: selectedStat
                    })
                }
            );

            currentStreak = 0;
            sessionBest = Math.max(
                sessionBest,
                data.best || 0
            );

            hide(setup);
            hide(gameOver);
            show(game);

            displayRound(data);

        } catch (error) {

            showError(error.message);

        } finally {

            isProcessing = false;
            startButton.disabled = false;
            restartButton.disabled = false;
        }
    }

    // =================================================
    // SUBMIT GUESS
    // =================================================

    async function submitGuess(guess) {

        if (isProcessing) {
            return;
        }

        isProcessing = true;
        setGuessButtonsDisabled(true);
        clearError();

        try {

            const data = await requestApi(
                "/api/games/higher-or-lower/guess",
                {
                    method: "POST",
                    body: JSON.stringify({
                        guess: guess
                    })
                }
            );

            // Reveal the second player's statistic.
            byId("hl-player-two-value").textContent =
                data.revealed_value;
                animateAnswer(data.correct);

showAchievementNotifications(
    data.new_achievements || []
);
            if (data.correct) {

                currentStreak = data.streak;

                sessionBest = Math.max(
                    sessionBest,
                    data.best || 0,
                    currentStreak
                );

                updateScoreboard();

                setFeedback(
                    "CORRECT! +1 STREAK",
                    "correct"
                );

                await wait(1100);

                displayRound(data.next_round);

            } else {

                currentStreak = data.streak;

                sessionBest = Math.max(
                    sessionBest,
                    data.best || 0
                );

                updateScoreboard();

                setFeedback(
                    "WRONG ANSWER!",
                    "wrong"
                );

                await wait(1000);

                endGame(data);
            }

        } catch (error) {

            showError(error.message);
            setGuessButtonsDisabled(false);

        } finally {

            isProcessing = false;
        }
    }

    // =================================================
    // GAME OVER
    // =================================================

    function endGame(data) {

        byId("hl-final-score").textContent =
            data.streak;

        let message = "Ready for another attempt?";

        if (data.streak === 0) {
            message = "Tough start. Give it another shot!";
        } else if (data.streak >= 20) {
            message = "Incredible run! EuroLeague expert!";
        } else if (data.streak >= 10) {
            message = "Excellent basketball knowledge!";
        } else if (data.streak >= 5) {
            message = "Nice streak! Can you beat it?";
        }

        byId("hl-result-message").textContent = message;

        show(gameOver);

        gameOver.scrollIntoView({
            behavior: "smooth",
            block: "center"
        });
    }

    // =================================================
    // RESTART
    // =================================================

    function restartGame() {

        if (isProcessing) {
            return;
        }

        hide(game);
        hide(gameOver);

        show(setup);

        currentStreak = 0;
        updateScoreboard();

        clearError();
        setFeedback("");

        setup.scrollIntoView({
            behavior: "smooth",
            block: "start"
        });
    }

    // =================================================
    // EVENTS
    // =================================================

    startButton.addEventListener(
        "click",
        startGame
    );

    restartButton.addEventListener(
        "click",
        restartGame
    );

    higherButton.addEventListener("click", () => {
        submitGuess("higher");
    });

    lowerButton.addEventListener("click", () => {
        submitGuess("lower");
    });

    // =================================================
    // INITIAL DISPLAY
    // =================================================

    updateScoreboard();

});
