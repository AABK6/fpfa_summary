document.addEventListener('DOMContentLoaded', () => {
    const cards = document.querySelectorAll('.card');
    const totalCards = cards.length;

    // Measure heights offscreen
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

    // Initialize cards with heights and states
    cards.forEach(card => {
        const heights = measureHeights(card);
        card.dataset.frontHeight = heights.front;
        card.dataset.backHeight = heights.back;
        card.dataset.backWithQuotesHeight = heights.backWithQuotes;
        card.dataset.state = '0'; // 0: stacked, 1: front, 2: back, 3: back with quotes
    });

    // Set last card (Card 1) as initially expanded
    const initialExpanded = cards[totalCards - 1];
    initialExpanded.classList.add('expanded');
    initialExpanded.style.height = initialExpanded.dataset.frontHeight + 'px';
    initialExpanded.dataset.state = '1';

    // Set other cards as stacked
    cards.forEach(card => {
        if (card !== initialExpanded) {
            card.classList.add('stacked');
            card.style.height = '60px';
            card.dataset.state = '0';
        }
    });

    // Click event handler
    cards.forEach(card => {
        card.addEventListener('click', () => {
            const currentState = parseInt(card.dataset.state);
            if (currentState === 0) {
                // Expand clicked card
                const currentExpanded = document.querySelector('.card.expanded');
                if (currentExpanded) {
                    currentExpanded.classList.remove('expanded');
                    currentExpanded.classList.add('stacked');
                    currentExpanded.style.height = '60px';
                    currentExpanded.dataset.state = '0';
                    currentExpanded.querySelector('.card-inner').classList.remove('flipped');
                    currentExpanded.querySelector('.card-back').classList.remove('show-quotes');
                }
                card.classList.remove('stacked');
                card.classList.add('expanded');
                card.style.height = card.dataset.frontHeight + 'px';
                card.dataset.state = '1';
            } else if (currentState === 1) {
                // Flip to back
                card.querySelector('.card-inner').classList.add('flipped');
                card.style.height = card.dataset.backHeight + 'px';
                card.dataset.state = '2';
            } else if (currentState === 2) {
                // Show quotes
                card.querySelector('.card-back').classList.add('show-quotes');
                card.style.height = card.dataset.backWithQuotesHeight + 'px';
                card.dataset.state = '3';
            } else if (currentState === 3) {
                // Flip back to front
                card.querySelector('.card-inner').classList.remove('flipped');
                card.querySelector('.card-back').classList.remove('show-quotes');
                card.style.height = card.dataset.frontHeight + 'px';
                card.dataset.state = '1';
            }
        });
    });
});