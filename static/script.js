document.addEventListener('DOMContentLoaded', () => {
    const cards = document.querySelectorAll('.card');
    const totalCards = cards.length;
    const deck = document.querySelector('.deck');
    const deckWidth = deck.offsetWidth;

    // Assign --depth to each card (bottom card has --depth: 0, top has highest)
    cards.forEach((card, index) => {
        const depth = totalCards - 1 - index; // Bottom card: 0, top card: totalCards - 1
        card.style.setProperty('--depth', depth);
    });

    // Function to measure heights offscreen with correct width
    function measureHeights(card) {
        const clone = card.cloneNode(true);
        clone.style.position = 'absolute';
        clone.style.visibility = 'hidden';
        clone.style.width = `${deckWidth}px`; // Match actual card width
        clone.style.height = 'auto';
        clone.classList.remove('stacked');
        document.body.appendChild(clone);

        const titleHeight = clone.querySelector('.card-title-container').offsetHeight;
        const frontHeight = clone.querySelector('.card-front').offsetHeight;
        clone.classList.add('flipped');
        const backHeight = clone.querySelector('.card-back').offsetHeight;
        clone.querySelector('.card-back').classList.add('show-quotes');
        const backWithQuotesHeight = clone.querySelector('.card-back').offsetHeight;

        document.body.removeChild(clone);
        return { title: titleHeight, front: frontHeight, back: backHeight, backWithQuotes: backWithQuotesHeight };
    }

    // Initialize each card with precomputed heights
    cards.forEach(card => {
        const heights = measureHeights(card);
        card.dataset.titleHeight = heights.title;
        card.dataset.frontHeight = heights.front;
        card.dataset.backHeight = heights.back;
        card.dataset.backWithQuotesHeight = heights.backWithQuotes;
    });

    // Function to set card state with dynamic heights
    function setCardState(card, state) {
        card.dataset.state = state;
        if (state == 0) {
            card.classList.add('stacked');
            card.classList.remove('expanded', 'flipped');
            card.querySelector('.card-back').classList.remove('show-quotes');
            card.style.height = `${card.dataset.titleHeight}px`; // Fit title text
        } else if (state == 1) {
            card.classList.remove('stacked', 'flipped');
            card.classList.add('expanded');
            card.querySelector('.card-back').classList.remove('show-quotes');
            card.style.height = `${card.dataset.frontHeight}px`; // Fit front content
        } else if (state == 2) {
            card.classList.remove('stacked');
            card.classList.add('expanded', 'flipped');
            card.querySelector('.card-back').classList.remove('show-quotes');
            card.style.height = `${card.dataset.backHeight}px`; // Fit back content
        } else if (state == 3) {
            card.classList.remove('stacked');
            card.classList.add('expanded', 'flipped');
            card.querySelector('.card-back').classList.add('show-quotes');
            card.style.height = `${card.dataset.backWithQuotesHeight}px`; // Fit back with quotes
        }
    }

    // Initially, set the last card (front card) to state 1, others to state 0
    cards.forEach((card, index) => {
        if (index === totalCards - 1) {
            setCardState(card, 1); // Front card (Card 1) starts expanded, showing front
        } else {
            setCardState(card, 0); // Other cards start stacked
        }
    });

    // Click event
    cards.forEach(card => {
        card.addEventListener('click', () => {
            const currentState = parseInt(card.dataset.state);
            if (currentState === 0) {
                // Stack all cards
                cards.forEach(c => setCardState(c, 0));
                // Expand the clicked card to state 1
                setCardState(card, 1);
            } else {
                // Cycle to next state: 1 -> 2 -> 3 -> 1
                const nextState = (currentState % 3) + 1;
                setCardState(card, nextState);
            }
        });
    });
});