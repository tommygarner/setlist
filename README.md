# The Setlist

**Your personalized concert planner**

AI-powered concert discovery that matches your music taste with upcoming shows in your city. Connect your Spotify, discover concerts, swipe on artists, and find friends to go with.

**[Try it live!](https://tommygarner-setlist.streamlit.app)**

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![Streamlit](https://img.shields.io/badge/streamlit-1.28+-red.svg)
![Docker](https://img.shields.io/badge/docker-ready-blue.svg)
![Tests](https://img.shields.io/badge/tests-16%20passing-brightgreen.svg)

---

## Features

| Feature | Description |
|---------|-------------|
| **Spotify Integration** | Connect your account and auto-import your favorite artists |
| **Concert Discovery** | Find shows from Ticketmaster + SeatGeek in your city |
| **Artist Swipe** | Tinder-style interface to rate artists and build preferences |
| **Smart Recommendations** | "For You" feed based on your music taste |
| **Social Features** | Add friends, see music compatibility, share concerts |
| **Messaging** | DM friends with embedded concert cards |
| **Concert Tracking** | Mark shows as "Going" or "Interested" |

---

## Quick Start

### Option 1: Run with Docker (Recommended)

**Prerequisites:** [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed

#### Step 1: Clone the repository
```bash
git clone https://github.com/yourusername/setlist.git
cd setlist
```

#### Step 2: Create your secrets file
```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

#### Step 3: Add your API keys
Open `.streamlit/secrets.toml` in a text editor and fill in your credentials:

```toml
[connections.supabase]
SUPABASE_URL = "https://your-project.supabase.co"
SUPABASE_KEY = "your-supabase-anon-key"

[spotify]
CLIENT_ID = "your-spotify-client-id"
CLIENT_SECRET = "your-spotify-client-secret"
REDIRECT_URI = "http://localhost:8501/1_connect_spotify"

[ticketmaster]
API_KEY = "your-ticketmaster-api-key"
CITY = "Austin"
STATE_CODE = "TX"
SEARCH_RADIUS = "100"

[seatgeek]
CLIENT_ID = "your-seatgeek-client-id"
```

#### Step 4: Build and run
```bash
docker-compose up --build
```

#### Step 5: Open the app
Navigate to **http://localhost:8501** in your browser.

---

### Option 2: Run Locally (Without Docker)

#### Step 1: Clone and setup
```bash
git clone https://github.com/yourusername/setlist.git
cd setlist

# Create virtual environment
python -m venv venv

# Activate it
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate
```

#### Step 2: Install dependencies
```bash
pip install -r requirements.txt
```

#### Step 3: Configure secrets
```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# Edit .streamlit/secrets.toml with your API keys
```

#### Step 4: Run the app
```bash
streamlit run app.py
```

The app opens at **http://localhost:8501**

---

## Getting API Keys

### 1. Supabase (Database + Auth)
1. Go to [supabase.com](https://supabase.com) and create a free account
2. Create a new project
3. Go to **Settings > API** and copy:
   - `Project URL` > `SUPABASE_URL`
   - `anon public` key > `SUPABASE_KEY`

### 2. Spotify API
1. Go to [developer.spotify.com/dashboard](https://developer.spotify.com/dashboard)
2. Create a new app
3. Copy **Client ID** and **Client Secret**
4. Add `http://localhost:8501/1_connect_spotify` to Redirect URIs

### 3. Ticketmaster API
1. Go to [developer.ticketmaster.com](https://developer.ticketmaster.com)
2. Sign up for a free account
3. Copy your **Consumer Key** (this is your API key)

### 4. SeatGeek API
1. Go to [seatgeek.com/account/develop](https://seatgeek.com/account/develop)
2. Register for API access
3. Copy your **Client ID**

---

## Docker Commands Reference

```bash
# Build and start (foreground)
docker-compose up --build

# Start in background
docker-compose up -d

# Stop the app
docker-compose down

# View logs
docker-compose logs -f

# Rebuild after code changes
docker-compose up --build --force-recreate
```

---

## Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=utils

# Run specific test file
pytest tests/test_app.py -v
```

---

## Deploying to Production

### Railway (Recommended)

1. Push your code to GitHub
2. Go to [railway.app](https://railway.app) and create a new project
3. Connect your GitHub repository
4. Add environment variables in Railway dashboard:
   - `SUPABASE_URL`, `SUPABASE_KEY`
   - `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`
   - `TICKETMASTER_API_KEY`, `SEATGEEK_CLIENT_ID`
5. Update Spotify Redirect URI to your Railway URL

### Fly.io

```bash
# Install flyctl
curl -L https://fly.io/install.sh | sh

# Launch app
fly launch

# Set secrets
fly secrets set SUPABASE_URL="..." SUPABASE_KEY="..."

# Deploy
fly deploy
```

### Streamlit Community Cloud

1. Push to GitHub (public repo)
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your repo
4. Add secrets in the Streamlit dashboard

---

## Project Structure

```
setlist/
├── app.py                          # Main entry point + auth
├── pages/                          # Streamlit multi-page app
│   ├── 1_connect_spotify.py        # Spotify OAuth flow
│   ├── 2_discover_concerts.py      # Concert search (TM + SeatGeek)
│   ├── 3_artist_swipe.py           # Tinder-style artist rating
│   ├── 4_music_discovery.py        # Recommendations engine
│   ├── 5_friends.py                # Friend system + compatibility
│   ├── 6_messages.py               # Direct messaging
│   └── 7_my_concerts.py            # Concert watchlist
├── utils/
│   ├── __init__.py
│   └── demo_data.py                # Mock data for demo mode
├── tests/
│   ├── __init__.py
│   └── test_app.py                 # 16 automated tests
├── .github/workflows/
│   └── ci.yml                      # GitHub Actions CI/CD
├── .streamlit/
│   └── secrets.toml.example        # Secrets template
├── Dockerfile                      # Docker build config
├── docker-compose.yml              # Docker Compose config
├── requirements.txt                # Python dependencies
├── CLAUDE.md                       # AI assistant context
└── README.md                       # This file
```

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | Streamlit |
| **Backend/Auth** | Supabase (PostgreSQL + Auth) |
| **Music Data** | Spotify Web API |
| **Concert Data** | Ticketmaster + SeatGeek APIs |
| **Async HTTP** | aiohttp |
| **Data Processing** | Pandas |
| **Containerization** | Docker |
| **CI/CD** | GitHub Actions |
| **Testing** | pytest |

---

## Roadmap

- [x] Concert discovery dashboard
- [x] Artist preference swipe interface
- [x] Spotify API integration
- [x] Ticketmaster + SeatGeek integration
- [x] User authentication (Supabase)
- [x] Friend system with compatibility scores
- [x] Direct messaging
- [x] Docker deployment
- [x] CI/CD pipeline
- [x] Automated tests
- [ ] Push notifications
- [ ] Calendar integration
- [ ] Price alerts
- [ ] Mobile app

---

## Contributing

This is a personal project, but feedback and suggestions are welcome! Feel free to open an issue or submit a PR.

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Author

**Tommy Garner**
- GitHub: [@tommygarner](https://github.com/tommygarner)
- LinkedIn: [My Profile](https://www.linkedin.com/in/tommy-garner/)

---

*This repository was refined and cleaned up with [Claude Code](https://claude.ai/code).*
