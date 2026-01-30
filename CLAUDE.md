# CLAUDE.md - The Setlist Project Context

> This file provides context for AI assistants (Claude, etc.) working on this codebase.

## Project Overview

**The Setlist** is a personalized concert discovery platform built by Tommy Garner. It helps users discover upcoming concerts based on their Spotify listening habits and connect with friends who share similar music taste.

### Core Value Proposition
- Connect Spotify account → Analyze liked artists → Find matching concerts → Swipe to decide → Share with friends

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | Streamlit (Python web framework) |
| **Backend/Auth** | Supabase (PostgreSQL + Auth + Realtime) |
| **Music Data** | Spotify Web API (user's music library) |
| **Concert Data** | Ticketmaster Discovery API + SeatGeek API |
| **Async HTTP** | aiohttp (parallel API requests) |
| **Data Processing** | Pandas |

## Project Structure

```
setlist/
├── app.py                          # Main entry point - auth flow + dashboard
├── pages/                          # Streamlit multi-page app pages
│   ├── 1_connect_spotify.py        # Spotify OAuth flow
│   ├── 2_discover_concerts.py      # Concert discovery (TM + SeatGeek)
│   ├── 3_artist_swipe.py           # Tinder-style artist preference UI
│   ├── 4_music_discovery.py        # "For You" recommendations
│   ├── 5_friends.py                # Friend system + compatibility scoring
│   ├── 6_messages.py               # DM system with concert sharing
│   └── 7_my_concerts.py            # Concert watchlist (Going/Interested)
├── utils/                          
│   ├── __init__.py                 # Package init
│   └── demo_data.py                # Mock data for demo mode
├── tests/                          
│   ├── __init__.py                 # Package init
│   └── test_app.py                 # 16 automated tests (pytest)
├── .github/workflows/
│   └── ci.yml                      # GitHub Actions CI/CD pipeline
├── data/                           # Local data files (gitignored)
├── notebooks/                      
│   └── concert_scraper.ipynb       # Data collection notebook
├── assets/                         # Static assets (images, CSS)
├── .devcontainer/                  
│   └── devcontainer.json           # GitHub Codespaces config
├── .streamlit/
│   ├── secrets.toml                # Streamlit secrets (gitignored)
│   └── secrets.toml.example        # Template for secrets
├── Dockerfile                      # Docker build configuration
├── docker-compose.yml              # Docker Compose for local dev
├── .dockerignore                   # Files to exclude from Docker
├── requirements.txt                # Python dependencies
├── CLAUDE.md                       # This file (AI context)
└── README.md                       # User-facing documentation
```

## Application Flow

### 1. Authentication (app.py)
- Uses Supabase Auth for email/password authentication
- Session state tracks `authenticated` and `user` objects
- All pages check auth state and redirect to login if needed

### 2. Spotify Connection (1_connect_spotify.py)
- OAuth 2.0 flow with `spotipy` library
- Stores tokens in Supabase `profiles` table
- Scopes: `user-library-read`, `user-top-read`
- Handles token refresh automatically

### 3. Concert Discovery (2_discover_concerts.py)
- Fetches user's liked songs from Spotify
- Extracts unique artists
- Parallel async requests to Ticketmaster + SeatGeek APIs
- Deduplicates and saves to `concerts_discovered` table
- Location-based filtering (city, state, radius)

### 4. Artist Swipe (3_artist_swipe.py)
- Tinder-style swipe UI for artists
- Shows artist info from Spotify (image, genres, followers)
- Displays top tracks with audio previews
- Saves preferences to `preferences` table (liked/disliked)

### 5. Music Discovery (4_music_discovery.py)
- "For You" tab: Scores concerts based on liked artists
- "This Weekend" tab: Temporal filtering
- "Surprise Me" tab: Random concert picker
- "Similar Artists" tab: Discovery of new artists

### 6. Friends System (5_friends.py)
- Friend requests with pending/accepted states
- Music compatibility scoring (Jaccard similarity)
- "Blend" feature showing shared artists
- Search by username or email

### 7. Messages (6_messages.py)
- Real-time direct messaging between friends
- Concert sharing with embedded cards
- Unread message tracking
- Message history persistence

### 8. My Concerts (7_my_concerts.py)
- Concert watchlist management
- Status tracking: Going / Interested
- Filtering by date, artist, venue
- Quick share to friends

## Database Schema (Supabase)

### Tables
- **profiles**: User profiles with Spotify tokens
- **preferences**: Artist like/dislike records (user_id, artist_name, preference)
- **concerts_discovered**: Saved concerts per user
- **concert_attendance**: Going/Interested status per user+event
- **friendships**: Friend relationships (user_id, friend_id, status)
- **messages**: Direct messages with optional concert attachments

## Configuration

### Required Secrets (.streamlit/secrets.toml)
```toml
[connections.supabase]
SUPABASE_URL = "https://xxx.supabase.co"
SUPABASE_KEY = "xxx"

[spotify]
CLIENT_ID = "xxx"
CLIENT_SECRET = "xxx"
REDIRECT_URI = "http://localhost:8501/1_connect_spotify"

[ticketmaster]
API_KEY = "xxx"
CITY = "Austin"
STATE_CODE = "TX"
SEARCH_RADIUS = "100"

[seatgeek]
CLIENT_ID = "xxx"
```

## Known Issues / Technical Debt

1. ~~**Hardcoded credentials in 3_artist_swipe.py**~~ ✅ Fixed - now uses `st.secrets`

2. ~~**Hardcoded SeatGeek client ID in 4_music_discovery.py**~~ ✅ Fixed - now uses `st.secrets`

3. ~~**No utils module implemented**~~ ✅ Fixed - `utils/demo_data.py` added with mock data

4. **Session state management**: Some inconsistency in how session state is initialized across pages.

5. **Error handling**: Some API errors are silently caught without user feedback.

## Testing

```bash
# Run all tests
pytest tests/ -v

# 16 tests covering:
# - Demo data generation
# - App structure validation
# - Data format validation
```

## CI/CD Pipeline

GitHub Actions workflow (`.github/workflows/ci.yml`) runs on every push:
1. **Test job**: Runs pytest suite
2. **Build job**: Builds Docker image
3. **Push**: Pushes to GitHub Container Registry (ghcr.io)

4. **Session state management**: Some inconsistency in how session state is initialized across pages.

5. **Error handling**: Some API errors are silently caught without user feedback.

## Docker Deployment

The project is Docker-ready with:
- `Dockerfile` - Multi-stage build for smaller images
- `docker-compose.yml` - Easy local development
- `.dockerignore` - Excludes sensitive files from image
- `.streamlit/secrets.toml.example` - Template for configuration

### Quick Start
```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# Edit secrets.toml with your API keys
docker-compose up --build
```

## Development Commands

```bash
# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Run locally
streamlit run app.py

# Run with specific port
streamlit run app.py --server.port 8501
```

## Docker Deployment Notes

The project already has a `.devcontainer/devcontainer.json` for GitHub Codespaces. For Docker deployment:

1. **Environment variables**: Need to externalize secrets (currently in `.streamlit/secrets.toml`)
2. **Health checks**: Streamlit runs on port 8501
3. **CORS/XSRF**: May need `--server.enableCORS false --server.enableXsrfProtection false` for containerized environments
4. **OAuth callbacks**: Redirect URIs must match deployed URL

## API Rate Limits

- **Spotify**: Standard rate limits apply
- **Ticketmaster**: 5000 calls/day (free tier)
- **SeatGeek**: Liberal limits, but 406 errors occur if too many concurrent requests

## Portfolio Highlights

Features worth discussing in interviews:
1. **Async API orchestration**: Parallel requests to multiple concert APIs
2. **OAuth implementation**: Full Spotify OAuth with token refresh
3. **Real-time features**: Supabase for auth + data + messaging
4. **Social features**: Friend system with compatibility scoring
5. **UX patterns**: Tinder-style swipe interface for preferences
