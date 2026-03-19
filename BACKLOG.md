# Feature Backlog

Things to port from Streamlit or build new. Work through these one at a time.

---

## Music Discovery (MusicDiscovery.jsx)

Currently shows only artist name. Port from `4_music_discovery.py`:

- **For You tab**: Concert cards with venue, date, ticket URL, price range, match score badge
- **This Weekend tab**: Same card layout filtered to Fri–Sun
- **Surprise Me tab**: Full card for the single random result (not just name)
- **Similar Artists tab**: Discovery of new artists based on liked preferences (Spotify recommendations API or manual similarity)
- Score display: show the match score (0–100) as a colored pill on each card
- Link to ticket purchase (Ticketmaster/SeatGeek URL)

---

## Artist Swipe (ArtistSwipe.jsx)

Port from `3_artist_swipe.py`:

- Artist image (Spotify artist image, not placeholder)
- Genres listed under name
- Follower count
- Top 5 tracks with album art per track + Spotify link + YouTube search link
- Top 3 albums (album type only) with cover art + Spotify album link
- Audio preview playback (30-second Spotify preview_url)
- Swipe left (dislike) / right (like) with keyboard shortcuts ← →
- Skip button
- Queue: pull unrated artists from the user's Spotify library

---

## Discover Concerts (DiscoverConcerts.jsx)

Port from `2_discover_concerts.py`:

- City/state/radius input controls (currently hardcoded to Austin TX)
- Progress indicator while fetching (async fan-out takes a few seconds)
- Results table or card grid with: artist, venue, date, time, price range, source badge (TM vs SG)
- Filter by artist / date range
- "Add to watchlist" button on each card (writes to concert_attendance)

---

## My Concerts (MyConcerts.jsx)

Port from `7_my_concerts.py`:

- Concert list with Going / Interested status toggle
- Filter by status, date, artist, venue
- Quick share button: opens DM composer with concert pre-filled
- Sort by date ascending

---

## Friends (Friends.jsx)

Port from `5_friends.py`:

- Pending requests tab (incoming requests the user hasn't accepted yet)
- Music compatibility score (Jaccard similarity on liked artists)
- "Blend" section showing shared artists between you and a friend
- Accept/decline incoming requests (currently only send works)

---

## Messages (Messages.jsx)

Port from `6_messages.py`:

- Concert share card: when a message has `concert_data`, render a mini concert card inline
- Unread badge on friend list (count of unread messages)
- Auto-scroll to bottom on new message
- Real-time updates via Supabase Realtime (subscribe to `messages` table inserts)

---

## Home (Home.jsx)

- Actual stats from Supabase (liked artists count, discovered concerts count, friends count)
- Quick action cards linking to each feature
- "Connect Spotify" prompt if not connected

---

## General / Infrastructure

- Toast notifications for success/error states (currently silent failures)
- Loading skeletons instead of spinner-only states
- Mobile responsive layout check
- Supabase RLS policies — verify all tables are protected
