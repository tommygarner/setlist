# The Setlist

**Personalized concert discovery for Austin**

Connect your Spotify, discover upcoming shows matched to your taste, swipe on artists, and coordinate with friends.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![React](https://img.shields.io/badge/react-18-blue.svg)
![FastAPI](https://img.shields.io/badge/fastapi-0.110-green.svg)
![Docker](https://img.shields.io/badge/docker-ready-blue.svg)

---

## How it works

1. Connect your Spotify account
2. The app scans your liked songs and top artists
3. Ticketmaster is searched for each artist (30mi radius, Austin)
4. Concerts are ranked by an affinity score — your most-listened and explicitly liked artists float to the top
5. Swipe on artists to tune recommendations
6. Share shows with friends via DM

---

## Features

| | |
|---|---|
| **Discover Concerts** | Async fan-out to Ticketmaster across all your Spotify artists. SSE progress bar streams real steps. Results cached 24h. |
| **Affinity Scoring** | Combines Spotify short/medium-term top artists with explicit swipe preferences. Disliked artists filtered out entirely. |
| **Artist Swipe** | Tinder-style queue with artist image, top 5 tracks (album art + Spotify/YouTube links), top 3 albums. Session-persistent index. Next artist prefetched while you read the current one. |
| **Music Discovery** | For You / Similar Artists / This Weekend / Surprise Me. "Similar Artists" uses Spotify related-artists API to find acts you don't know but would like, then finds their Austin shows. |
| **My Concerts** | Only shows you've explicitly marked Going or Interested — not your full discovered list. |
| **Friends + Messages** | Friend requests, DMs, concert cards shared inline. |

---

## Stack

| Layer | Tech |
|---|---|
| Frontend | React 18, Vite, Tailwind CSS |
| Backend | FastAPI, Python 3.11, uvicorn |
| Auth + DB | Supabase (PostgreSQL + Auth) |
| Music data | Spotify Web API |
| Concert data | Ticketmaster Discovery API |
| Deployment | Docker + nginx |

---

## Local development

**Prerequisites:** Python 3.11+, Node 18+, a Supabase project, Spotify app, Ticketmaster API key.

```bash
# Backend
cp backend/.env.example backend/.env
# fill in backend/.env
cd backend
pip install -r requirements.txt
python -m uvicorn main:app --reload

# Frontend (separate terminal)
cp frontend/.env.example frontend/.env
# fill in frontend/.env
cd frontend
npm install
npm run dev
```

App runs at `http://localhost:5173`.

### Supabase setup

Run this SQL in your Supabase SQL editor once:

```sql
create table if not exists profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  username text, email text,
  spotify_connected boolean default false,
  spotify_access_token text, spotify_refresh_token text, spotify_token_expires_at timestamptz,
  created_at timestamptz default now()
);
create or replace function handle_new_user() returns trigger as $$
begin
  insert into public.profiles (id, email, username)
  values (new.id, new.email, new.raw_user_meta_data->>'username')
  on conflict (id) do nothing;
  return new;
end;
$$ language plpgsql security definer;
drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created after insert on auth.users
  for each row execute procedure handle_new_user();

create table if not exists preferences (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references profiles(id) on delete cascade,
  artist_name text not null, preference text not null,
  created_at timestamptz default now(),
  unique(user_id, artist_name)
);
create table if not exists concerts_discovered (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references profiles(id) on delete cascade,
  event_id text unique, artist_name text, event_name text,
  venue_name text, city text, state text, date text, time text,
  ticket_url text, min_price numeric, max_price numeric, source text,
  affinity_score float default 0,
  created_at timestamptz default now()
);
create table if not exists concert_attendance (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references profiles(id) on delete cascade,
  event_id text, status text, concert_data jsonb,
  created_at timestamptz default now(),
  unique(user_id, event_id)
);
create table if not exists friendships (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references profiles(id) on delete cascade,
  friend_id uuid references profiles(id) on delete cascade,
  status text default 'pending',
  created_at timestamptz default now()
);
create table if not exists messages (
  id uuid primary key default gen_random_uuid(),
  sender_id uuid references profiles(id) on delete cascade,
  receiver_id uuid references profiles(id) on delete cascade,
  message text not null, read boolean default false,
  concert_event_id text, concert_data jsonb,
  created_at timestamptz default now()
);
```

Also add `http://localhost:8000/api/spotify/callback` as a redirect URI in your Spotify Developer Dashboard.

---

## Docker deployment

```bash
# Create a .env at repo root with Supabase public keys for the frontend build
echo "VITE_SUPABASE_URL=https://xxx.supabase.co" > .env
echo "VITE_SUPABASE_ANON_KEY=xxx" >> .env

# Fill in backend/.env with all secrets
cp backend/.env.example backend/.env

docker compose up --build
```

Frontend at `http://localhost`, API at `http://localhost:8000`.

The nginx config proxies `/api/*` to the FastAPI backend and handles SPA routing. SSE buffering is disabled on the proxy so the discover progress bar streams correctly.

---

## Architecture notes

**Affinity scoring** — each discovered concert gets a score at discover time:
- Explicitly liked via swipe: +100
- In Spotify short-term top artists: up to +80 (rank-weighted)
- In Spotify medium-term top artists: up to +40 (rank-weighted)
- Explicitly disliked: filtered out

Scores are stored in `concerts_discovered.affinity_score`. The GET endpoint also applies a live preferences adjustment so swipes made after the last discover run take effect immediately.

**Discovery cache** — `POST /api/concerts/discover` checks the age of your existing `concerts_discovered` rows. If fresher than 24h, it streams a cache-hit message and returns immediately. Pass `?force=true` to bypass.

**Streaming** — the discover endpoint uses FastAPI `StreamingResponse` with SSE events. The frontend reads the stream with `fetch` + `ReadableStream` (not `EventSource`) so it can send the Authorization header.
