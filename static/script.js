document.addEventListener('DOMContentLoaded', () => {
    const cards = document.querySelectorAll('.card');

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

    // Initialize each card with precomputed heights
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
                card.classList.remove('flipped');
                card.querySelector('.card-back').classList.remove('show-quotes');
                card.style.height = '60px';
            } else if (state === 1) {
                // Expanded (front)
                card.classList.remove('stacked', 'flipped');
                card.classList.add('expanded');
                card.style.height = `${card.dataset.frontHeight}px`;
            } else if (state === 2) {
                // Flipped (back without quotes)
                card.classList.remove('stacked');
                card.classList.add('flipped', 'expanded');
                card.querySelector('.card-back').classList.remove('show-quotes');
                card.style.height = `${card.dataset.backHeight}px`;
            } else if (state === 3) {
                // Unfolded (back with quotes)
                card.classList.add('flipped', 'expanded');
                card.querySelector('.card-back').classList.add('show-quotes');
                card.style.height = `${card.dataset.backWithQuotesHeight}px`;
            }
        });
    });
});