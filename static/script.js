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

    // Check URL parameters for article_id and state
    const urlParams = new URLSearchParams(window.location.search);
    const highlightId = urlParams.get('article_id');
    const highlightState = urlParams.get('state');

    // Initially set cards based on URL parameters or default state
    cards.forEach((card, index) => {
        if (highlightId && card.dataset.articleId === highlightId && highlightState) {
            // If URL has article_id and state, set that card to the specified state
            setCardState(card, parseInt(highlightState));
        } else if (highlightId) {
            // If we have a highlighted card, other cards should still be visible but stacked
            setCardState(card, 0);
        } else if (index === totalCards - 1 && !highlightId) {
            // If no URL parameters, front card (last in DOM) starts expanded
            setCardState(card, 1);
        } else if (!highlightId) {
            // Other cards start stacked if no URL parameters
            setCardState(card, 0);
        }
    });

    // Function to reset to original state
    function resetToOriginalState() {
        cards.forEach(card => setCardState(card, 0)); // Stack all cards
        const frontCard = cards[totalCards - 1];      // Front card is the last in DOM
        setCardState(frontCard, 1);                   // Expand front card
    }

    // Detect clicks outside the deck
    document.addEventListener('click', (event) => {
        if (!deck.contains(event.target)) {
            resetToOriginalState();
        }
    });

    // Click event for cards
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

    // Share article function
    window.shareArticle = function(articleId) {
        // Prevent event propagation to stop card from expanding
        event.stopPropagation();
        
        const card = document.querySelector(`[data-article-id="${articleId}"]`);
        const state = card.dataset.state;
        
        const params = new URLSearchParams();
        params.set('article_id', articleId);
        params.set('state', state);
        const url = `${window.location.origin}${window.location.pathname}?${params}`;
        
        // Create a temporary input to copy the URL
        const tempInput = document.createElement('input');
        tempInput.value = url;
        document.body.appendChild(tempInput);
        tempInput.select();
        document.execCommand('copy');
        document.body.removeChild(tempInput);
        
        // Show a temporary notification
        const notification = document.createElement('div');
        notification.textContent = 'Link copied to clipboard!';
        notification.style.position = 'fixed';
        notification.style.bottom = '20px';
        notification.style.left = '50%';
        notification.style.transform = 'translateX(-50%)';
        notification.style.backgroundColor = 'rgba(0, 0, 0, 0.7)';
        notification.style.color = 'white';
        notification.style.padding = '10px 20px';
        notification.style.borderRadius = '5px';
        notification.style.zIndex = '1000';
        document.body.appendChild(notification);
        
        setTimeout(() => {
            document.body.removeChild(notification);
        }, 2000);
    };

    const deckMiddle = deck.offsetTop + (deck.offsetHeight / 2);
    const targetScroll = deckMiddle - window.innerHeight * 0.5;
    window.scrollTo({ top: targetScroll, behavior: 'smooth' });
});