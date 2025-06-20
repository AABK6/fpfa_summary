# Flutter Stacked Card Deck Application

This document outlines the design of the Flutter application located in `fpfa_app`. The app displays articles in a 3D stacked deck of cards, allowing users to browse summaries and detailed content interactively.

## Purpose

- Provide a visually appealing and intuitive interface to browse a collection of articles.
- Allow users to scroll through a stack of cards, extract a card for detailed viewing, flip between multiple content views, and reset the deck.
- Adapt gracefully to different screen sizes and input methods.

## Key Features

1. **3D Stacked Deck** – Cards are arranged in a vertical deck with a depth effect. Only the top card is fully visible while background cards peek from behind it.
2. **Scrolling** – Users can move through the deck (mouse wheel, swipe, or other scroll gestures). As they scroll, cards shift vertically, bringing new cards forward and hiding those leaving the view.
3. **Card Extraction** – Tapping a stacked card moves it to the center of the screen in focus. Other cards remain behind it.
4. **Card Flipping** – Once a card is extracted, further taps cycle through its available views (e.g., front summary, back details, quotes). A 3D flip transition is used for view changes.
5. **Long Content Handling** – Extracted cards respect a maximum display height. If the card's content exceeds that height, it becomes scrollable while the card frame stays fixed.
6. **Reset** – Tapping outside the focused card or deck returns all cards to their stacked state, showing the primary view on top.

## Card Structure

- Each card represents an article with at least two views:
  - **Front View** – Shows the title, source, author, date, and the core thesis.
  - **Back View** – Presents the detailed abstract and, optionally, supporting quotes.
- Additional views can be added (for example, quotes as a separate view). Cards switch views when tapped while in the extracted state.

## Card States

1. **Stacked** – Default state where cards are layered in the deck. Only minimal information is visible on background cards.
2. **Front** – The card is extracted and shows its primary view (front content).
3. **Back/Quotes** – Subsequent states that display additional information. The design can be extended for more views if needed.

## Layout and Visual Style

- The deck sits in a fixed-height region in the middle of the screen. Cards are centered horizontally and share the same width (with a maximum width on larger displays).
- Vertical offsets and scaling simulate depth in the stacked state. Background cards appear slightly smaller and higher than the card above them.
- Cards feature rounded corners, subtle shadows, and a light background color. The surrounding app background is neutral.
- Animated transitions are used for scrolling, extraction, view flips, and fading cards in or out of the visible area.

## Behavior Overview

### Initialization

- Cards are placed in a stacked configuration when the app starts. The topmost card is fully visible, showing its front view. Internal state tracks whether each card is stacked, displaying the front, back, or other view.

### Scrolling

- Scrolling over the deck adjusts an offset that moves the entire stack up or down. Cards update their position and visibility based on this offset. Cards leaving the visible area fade out smoothly.

### Card Extraction and View Cycling

- Tapping a stacked card brings it forward and centers it. The card expands to its maximum height while respecting the defined size constraint.
- Further taps on the focused card cycle through its available views, flipping it with a 3D rotation animation.
- If the current view's content exceeds the card's height, only the content section scrolls, keeping titles and other fixed elements in place.

### Reset

- Tapping anywhere outside the deck or the focused card triggers a reset. All cards return to the stacked state, and the previously extracted card reverts to showing its primary content.

## Adaptability

- The UI adjusts to various screen sizes. On wide displays (e.g., web or desktop), cards use a capped width so the deck remains centered. On small mobile screens, cards expand to the available width while maintaining the maximum height rule for extracted cards.
- Input is handled consistently across mouse, touch, and keyboard interactions where applicable.

---

This design description replaces the previous placeholder documentation and aligns the Flutter app with the card-based specification.
