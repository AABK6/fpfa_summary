document.addEventListener('DOMContentLoaded', () => {
    const cards = document.querySelectorAll('.card');
    const totalCards = cards.length;

    // Assign --depth to each card (bottom card has --depth: 0, top has highest)
    cards.forEach((card, index) => {
        const depth = totalCards - 1 - index; // Bottom card: 0, top card: totalCards - 1
        card.style.setProperty('--depth', depth);
    });

    // Function to measure heights offscreen
    function measureHeights(card) {
        const clone = card.cloneNode(true);
        clone.style.position = 'absolute';
        clone.style.visibility = 'hidden';
        clone.style.height = 'auto';
        clone.classList.remove('stacked');
        document.body.appendChild(clone);

        const frontHeight = clone.querySelector('.card-front').offsetHeight;
        clone.classList.add('flipped');
        const backHeight = clone.querySelector('.card-back').offsetHeight;
        clone.querySelector('.card-back').classList.add('show-quotes');
        const backWithQuotesHeight = clone.querySelector('.card-back').offsetHeight;

        document.body.removeChild(clone);
        return { front: frontHeight, back: backHeight, backWithQuotes: backWithQuotesHeight };
    }

    // Initialize each card with precomputed heights and stacked state
    cards.forEach(card => {
        const heights = measureHeights(card);
        card.dataset.frontHeight = heights.front;
        card.dataset.backHeight = heights.back;
        card.dataset.backWithQuotesHeight = heights.backWithQuotes;
        card.classList.add('stacked');
    });

    // Click event to cycle through states
    cards.forEach(card => {
        let state = 0; // 0: stacked, 1: expanded front, 2: flipped back, 3: flipped back with quotes
        card.addEventListener('click', () => {
            state = (state + 1) % 4;
            if (state === 0) {
                // Stacked
                card.classList.add('stacked');
                card.classList.remove('expanded', 'flipped');
                card.querySelector('.card-back').classList.remove('show-quotes');
                card.style.height = '60px';
            } else if (state === 1) {
                // Expanded (front)
                card.classList.remove('stacked');
                card.classList.add('expanded');
                card.classList.remove('flipped');
                card.style.height = `${card.dataset.frontHeight}px`;
            } else if (state === 2) {
                // Flipped (back without quotes)
                card.classList.remove('stacked');
                card.classList.add('expanded', 'flipped');
                card.querySelector('.card-back').classList.remove('show-quotes');
                card.style.height = `${card.dataset.backHeight}px`;
            } else if (state === 3) {
                // Flipped (back with quotes)
                card.classList.add('expanded', 'flipped');
                card.querySelector('.card-back').classList.add('show-quotes');
                card.style.height = `${card.dataset.backWithQuotesHeight}px`;
            }
        });
    });
});