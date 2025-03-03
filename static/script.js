document.addEventListener('DOMContentLoaded', () => {
    // Define DOM elements and constants
    const deck = document.querySelector('.deck');
    const cards = document.querySelectorAll('.card');
    const totalCards = cards.length;
    const card3ds = document.querySelectorAll('.card-3d');
    const deckHeight = deck.clientHeight;
    const cardSpacing = 50; // Base spacing between cards, adjust as needed

    // Set spacer height to ensure scrollable area covers all cards
    const deckSpacer = document.querySelector('#deckSpacer');
    if (deckSpacer) {
        const viewCenter = deckHeight / 2;
        deckSpacer.style.height = `${(totalCards - 1) * cardSpacing + viewCenter}px`;
    }

    // Measure card heights for dynamic sizing
    function measureHeights(card) {
        const clone = card.cloneNode(true);
        clone.style.position = 'absolute';
        clone.style.visibility = 'hidden';
        clone.style.width = `${deck.offsetWidth}px`;
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

    // Initialize card heights
    cards.forEach(card => {
        const heights = measureHeights(card);
        card.dataset.titleHeight = heights.title;
        card.dataset.frontHeight = heights.front;
        card.dataset.backHeight = heights.back;
        card.dataset.backWithQuotesHeight = heights.backWithQuotes;
    });

    // Update card state and appearance
    function setCardState(card, state) {
        card.dataset.state = state;
        if (state === 0) {
            card.classList.add('stacked');
            card.classList.remove('expanded', 'flipped');
            card.querySelector('.card-back').classList.remove('show-quotes');
            card.style.height = `${card.dataset.titleHeight}px`;
        } else if (state === 1) {
            card.classList.remove('stacked', 'flipped');
            card.classList.add('expanded');
            card.querySelector('.card-back').classList.remove('show-quotes');
            card.style.height = `${card.dataset.frontHeight}px`;
        } else if (state === 2) {
            card.classList.remove('stacked');
            card.classList.add('expanded', 'flipped');
            card.querySelector('.card-back').classList.remove('show-quotes');
            card.style.height = `${card.dataset.backHeight}px`;
        } else if (state === 3) {
            card.classList.remove('stacked');
            card.classList.add('expanded', 'flipped');
            card.querySelector('.card-back').classList.add('show-quotes');
            card.style.height = `${card.dataset.backWithQuotesHeight}px`;
        }
        updateCardTransforms();
    }

    // Apply Rolodex effect based on scroll position
    function updateCardTransforms() {
        const scrollTop = deck.scrollTop;
        const viewCenter = scrollTop + (deckHeight / 2);
        const maxScale = 1; // Maximum scale at center
        const minScale = 0.8; // Minimum scale at edges

        card3ds.forEach((card3d, index) => {
            const card = card3d.querySelector('.card');
            const state = parseInt(card.dataset.state);

            if (state === 0) { // Stacked state with Rolodex effect
                const basePosition = index * cardSpacing;
                const adjustedPosition = basePosition - scrollTop;
                const distanceFromCenter = adjustedPosition - (deckHeight / 2);
                const distanceRatio = Math.min(Math.abs(distanceFromCenter) / (deckHeight / 2), 1);

                const scale = maxScale - (distanceRatio * (maxScale - minScale));
                const zTranslate = 50 * (1 - distanceRatio);
                const rotationX = (distanceFromCenter / deckHeight) * 60;

                card3d.style.top = `${basePosition}px`;
                card3d.style.transform = `translateY(-50%) scale(${scale}) translateZ(${zTranslate}px) rotateX(${rotationX}deg)`;
                card3d.style.zIndex = Math.round(100 - distanceRatio * 100);
            } else { // Expanded or flipped state, no Rolodex effect
                card3d.style.top = `${index * cardSpacing}px`;
                card3d.style.transform = `translateY(-50%) scale(1) translateZ(0px) rotateX(0deg)`;
                card3d.style.zIndex = 101;
            }
        });
    }

    // Set initial card states
    cards.forEach((card, index) => {
        if (index === totalCards - 1) {
            setCardState(card, 0); // Last card expanded
        } else {
            setCardState(card, 0); // Others stacked
        }
    });

    // Calculate initial scroll position to focus on the last card
    const lastCardIndex = totalCards - 1;
    const basePositionLast = lastCardIndex * cardSpacing;
    const viewCenter = deckHeight / 2;
    const scrollTopInitial = basePositionLast - viewCenter;

    // Ensure scrollTopInitial is not negative or exceeds max scroll
    const maxScrollTop = deck.scrollHeight - deckHeight;
    deck.scrollTop = Math.max(0, Math.min(scrollTopInitial, maxScrollTop));

    // Add scroll listener for Rolodex effect
    deck.addEventListener('scroll', updateCardTransforms);

    // Reset all cards to initial state
    function resetToOriginalState() {
        cards.forEach(card => setCardState(card, 0));
        const frontCard = cards[totalCards - 1];
        setCardState(frontCard, 1);
    }

    // Reset on click outside deck
    document.addEventListener('click', (event) => {
        if (!deck.contains(event.target)) {
            resetToOriginalState();
        }
    });

    // Handle card clicks to toggle states
    cards.forEach(card => {
        card.addEventListener('click', () => {
            const currentState = parseInt(card.dataset.state);
            if (currentState === 0) {
                cards.forEach(c => setCardState(c, 0)); // Collapse all
                setCardState(card, 1); // Expand clicked card
            } else {
                const nextState = (currentState % 3) + 1; // Cycle through states 1, 2, 3
                setCardState(card, nextState);
            }
        });
    });

    // Apply initial transforms
    updateCardTransforms();
});