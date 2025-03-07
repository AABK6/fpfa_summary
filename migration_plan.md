# Migration Plan: Converting to React Native & React Native for Web

## Project Overview
The current application is a Flask-based web app that scrapes, summarizes, and displays articles from Foreign Policy and Foreign Affairs websites. It uses SQLite for data storage, Flask for the backend, and vanilla HTML/CSS/JS for the frontend with a card-based UI featuring flip animations and expandable content.

## Migration Goals
- Create a cross-platform application that works on web, iOS, and Android
- Maintain all existing features and UI/UX design elements
- Use a single database solution that works across platforms
- Ensure the application remains performant on all platforms

## Technical Architecture

### Frontend
1. **React Native & React Native for Web**
   - Use React Native for mobile platforms (iOS/Android)
   - Use React Native for Web for browser support
   - Shared component library with platform-specific optimizations where needed

2. **UI Components**
   - Convert the card-based UI to React Native components
   - Implement the card flip and expansion animations using React Native Animated API
   - Use responsive design patterns to ensure consistent experience across devices

3. **State Management**
   - Implement Redux or Context API for global state management
   - Handle article data fetching and caching

### Backend
1. **API Layer**
   - Convert Flask routes to a RESTful API
   - Implement endpoints for article fetching and summarization

2. **Article Scraping & Summarization**
   - Move the scraping and summarization logic to API endpoints
   - Maintain the Google Gemini API integration for article summarization

### Database
1. **Cross-Platform Solution**
   - Replace SQLite with a cloud-based solution that works across platforms:
     - Option 1: **Firebase Firestore**
       - Real-time data synchronization with offline capabilities
       - Automatic scaling with Google Cloud infrastructure
       - Built-in authentication and security rules
       - Native SDKs for React Native and web
       - Serverless architecture with pay-as-you-go pricing
     - Option 2: **MongoDB Atlas**
       - Fully managed cloud database service
       - Document-based structure similar to JSON
       - Cross-platform SDKs with React Native compatibility
       - Robust querying capabilities and indexing
       - Flexible scaling options with multi-region deployment
     - Option 3: **Supabase**
       - PostgreSQL database with real-time capabilities
       - REST and GraphQL APIs for data access
       - Row-level security and authentication
       - Open-source with managed cloud option
       - Relational database benefits with modern API
     - Option 4: **AWS Amplify DataStore**
       - Seamless synchronization between devices
       - Conflict detection and resolution
       - Works with DynamoDB on the backend
       - Offline-first architecture
       - Deep integration with AWS services

2. **Data Schema**
   - Maintain the existing data structure:
     ```
     articles {
       id: string,
       source: string,
       url: string,
       title: string,
       author: string,
       article_text: string,
       core_thesis: string,
       detailed_abstract: string,
       supporting_data_quotes: string,
       date_added: timestamp
     }
     ```

## Implementation Strategy

### Phase 1: Project Setup & Environment Configuration
1. Initialize React Native project with Expo or React Native CLI
2. Configure React Native for Web
3. Set up the development environment for cross-platform development
4. Configure the chosen database solution

### Phase 2: Backend Migration
1. Create a new Node.js/Express backend API
2. Migrate the article scraping and summarization logic
3. Implement database operations for the new database solution
4. Set up authentication if needed

### Phase 3: Frontend Implementation
1. Create shared UI components
   - Card component with flip and expansion animations
   - Article list/deck component
   - Typography and styling components

2. Implement screens/pages
   - Home screen with article deck
   - Article detail view

3. Connect to backend API
   - Implement data fetching and state management
   - Handle loading and error states

### Phase 4: Platform-Specific Optimizations
1. Optimize UI for different screen sizes and platforms
2. Implement platform-specific features if needed
3. Ensure animations and interactions work well on all platforms

### Phase 5: Testing & Deployment
1. Test on multiple devices and platforms
2. Fix platform-specific issues
3. Prepare for deployment to web, App Store, and Google Play

## Component Structure

```
src/
├── api/
│   ├── articles.js       # Article API functions
│   └── summarization.js  # Summarization API functions
├── components/
│   ├── common/           # Shared UI components
│   │   ├── Button.js
│   │   ├── Typography.js
│   │   └── ...
│   ├── ArticleCard.js    # Card component with flip animation
│   ├── ArticleDeck.js    # Container for article cards
│   └── ...
├── screens/
│   ├── HomeScreen.js     # Main screen with article deck
│   └── ...
├── store/                # State management
│   ├── actions/
│   ├── reducers/
│   └── ...
├── utils/                # Utility functions
├── App.js                # Main app component
└── index.js              # Entry point
```

## Key Technical Challenges

1. **Card Animation Implementation**
   - The current implementation uses CSS transitions and 3D transforms
   - Need to recreate with React Native's Animated API
   - Ensure smooth performance on mobile devices
   - **Detailed Card Deck Rendering Approach**:
     - Implement a stacked card effect with z-index manipulation
     - Use React Native's transform property with perspective values
     - Apply shadow effects with elevation (Android) and shadowProps (iOS)
     - Create a cascading layout where each card is offset by 10-15dp vertically
     - Implement subtle rotation (2-3 degrees) for cards to create 3D depth
     - Display prominent card titles with partially visible content
     - Use Animated.Value to track user interactions
     - Implement spring physics for natural card movement
     - Apply scale transforms during interactions for tactile feedback
     - Optimize with useNativeDriver for 60fps animations on mobile
     - Implement platform-specific optimizations for web vs mobile rendering

2. **Database Access Across Platforms**
   - Ensure consistent data access patterns on web and mobile
   - Handle offline capabilities and synchronization

3. **Scraping and API Integration**
   - Move scraping logic to the backend
   - Ensure API rate limiting and caching

4. **Responsive Design**
   - Adapt the card-based UI to different screen sizes
   - Ensure touch interactions work well on mobile

## Next Steps

1. Set up the initial React Native project with React Native for Web
2. Create proof-of-concept implementations of key components:
   - ArticleCard with flip animation
   - ArticleDeck with card stacking
3. Implement the database solution and test cross-platform compatibility
4. Begin migrating the backend functionality to API endpoints