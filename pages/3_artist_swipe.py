import streamlit as st
import json
import pandas as pd
from pathlib import Path
import requests
import base64
from urllib.parse import quote
from supabase import create_client, Client
import streamlit.components.v1 as components

st.set_page_config(page_title="Artist Swipe", page_icon="🎵", layout="wide")

if 'scroll_to_top' not in st.session_state:
    st.session_state.scroll_to_top = False

if st.session_state.scroll_to_top:
    components.html(
        """
        <script>
            window.parent.document.querySelector('section.main').scrollTo(0, 0);
        </script>
        """,
        height=0,
    )
    st.session_state.scroll_to_top = False


# ==================== SPOTIFY API SETUP ====================
SPOTIFY_CLIENT_ID = "684f79d886db4d05829a92140ea463c1"
SPOTIFY_CLIENT_SECRET = "42a5ba77b17a4bd9934cfe12d37a4a7c"

def get_spotify_token():
    """Get Spotify access token"""
    auth_string = f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}"
    auth_bytes = auth_string.encode("utf-8")
    auth_base64 = base64.b64encode(auth_bytes).decode("utf-8")

    url = "https://accounts.spotify.com/api/token"
    headers = {
        "Authorization": f"Basic {auth_base64}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {"grant_type": "client_credentials"}

    response = requests.post(url, headers=headers, data=data)
    return response.json()["access_token"]

@st.cache_data(ttl=3600)
def search_artist_spotify(artist_name, token):
    """Search for artist on Spotify and get their info"""
    url = "https://api.spotify.com/v1/search"
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "q": artist_name,
        "type": "artist",
        "limit": 1
    }

    response = requests.get(url, headers=headers, params=params)
    data = response.json()

    if data['artists']['items']:
        artist = data['artists']['items'][0]
        return {
            "name": artist['name'],
            "image": artist['images'][0]['url'] if artist['images'] else None,
            "genres": artist['genres'][:3],
            "popularity": artist['popularity'],
            "followers": artist['followers']['total'],
            "spotify_url": artist['external_urls']['spotify'],
            "spotify_id": artist['id']
        }
    return None

@st.cache_data(ttl=3600)
def get_artist_top_tracks(artist_id, token, limit=10):
    """Get artist's top tracks with preview URLs"""
    url = f"https://api.spotify.com/v1/artists/{artist_id}/top-tracks"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"market": "US"}

    response = requests.get(url, headers=headers, params=params)
    tracks = response.json().get('tracks', [])

    return [{
        "name": track['name'],
        "artist": track['artists'][0]['name'],
        "preview_url": track['preview_url'],
        "album_image": track['album']['images'][0]['url'] if track['album']['images'] else None,
        "spotify_url": track['external_urls']['spotify'],
        "album_name": track['album']['name']
    } for track in tracks[:limit]]

@st.cache_data(ttl=3600)
def get_artist_albums(artist_id, token):
    """Get artist's albums"""
    url = f"https://api.spotify.com/v1/artists/{artist_id}/albums"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"market": "US", "limit": 5, "include_groups": "album,single"}

    response = requests.get(url, headers=headers, params=params)
    albums = response.json().get('items', [])

    return [{
        "name": album['name'],
        "image": album['images'][0]['url'] if album['images'] else None,
        "release_date": album['release_date'],
        "spotify_url": album['external_urls']['spotify']
    } for album in albums]

def get_youtube_search_url(artist_name, track_name):
    """Generate YouTube search URL for a track"""
    query = f"{artist_name} {track_name} official audio"
    return f"https://www.youtube.com/results?search_query={quote(query)}"

# ==================== SUPABASE CONNECTION ====================
def init_supabase() -> Client:
    url = st.secrets["connections"]["supabase"]["SUPABASE_URL"]
    key = st.secrets["connections"]["supabase"]["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_supabase()

# Check authentication
if "authenticated" not in st.session_state or not st.session_state.authenticated:
    st.error("❌ Please login first!")
    if st.button("← Go to Main App", key="main_app_btn"):
        st.switch_page("app.py")
    st.stop()

user = st.session_state.user

# ==================== DATABASE FUNCTIONS ====================
@st.cache_data(ttl=60)
def load_concerts(user_id):
    """Load concerts from Supabase for current user"""
    response = supabase.table("concerts_discovered").select("*").eq("user_id", user_id).execute()
    df = pd.DataFrame(response.data)
    if not df.empty:
        df = df.drop_duplicates(subset=['event_id'])
    return df

def load_preferences(user_id):
    """Load user preferences from Supabase"""
    response = supabase.table("preferences").select("*").eq("user_id", user_id).execute()

    liked = []
    disliked = []

    for pref in response.data:
        artist = pref['artist_name']
        if pref['preference'] == 'liked':
            liked.append(artist)
        elif pref['preference'] == 'disliked':
            disliked.append(artist)

    return {"liked": liked, "disliked": disliked, "swipe_history": []}

def save_preference(user_id, artist_name, preference):
    """Save preference to Supabase"""
    supabase.table("preferences").upsert({
        "user_id": user_id,
        "artist_name": artist_name,
        "preference": preference
    }, on_conflict='user_id,artist_name').execute()

# ==================== SESSION STATE ====================
if 'prefs' not in st.session_state:
    st.session_state.prefs = load_preferences(user.id)

if 'current_idx' not in st.session_state:
    st.session_state.current_idx = 0

if 'artists_list' not in st.session_state:
    df = load_concerts(user.id)
    if not df.empty:
        all_artists = df['artist_name'].drop_duplicates().dropna().tolist()
        already_rated = st.session_state.prefs['liked'] + st.session_state.prefs['disliked']
        st.session_state.artists_list = [a for a in all_artists if a not in already_rated]
    else:
        st.session_state.artists_list = []

if 'spotify_token' not in st.session_state:
    try:
        st.session_state.spotify_token = get_spotify_token()
    except:
        st.error("⚠️ Spotify API credentials not configured.")
        st.session_state.spotify_token = None

if 'show_review_page' not in st.session_state:
    st.session_state.show_review_page = False

# ==================== REVIEW & EDIT PAGE ====================
if st.session_state.show_review_page:
    st.title("📝 Review & Edit Your Choices")

    # Back button
    if st.button("⬅️ Back to Swiping"):
        st.session_state.show_review_page = False
        st.rerun()

    st.markdown("---")

    # Two columns for liked and disliked
    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"### ✅ Liked Artists ({len(st.session_state.prefs['liked'])})")

        if st.session_state.prefs['liked']:
            for i, artist in enumerate(sorted(st.session_state.prefs['liked'])):
                col_a, col_b = st.columns([3, 1])
                with col_a:
                    st.markdown(f"**{artist}**")
                with col_b:
                    if st.button("❌", key=f"unlike_{i}", help="Move to Passed"):
                        st.session_state.prefs['liked'].remove(artist)
                        st.session_state.prefs['disliked'].append(artist)
                        save_preference(user.id, artist, 'disliked')
			st.session_state.scroll_to_top = True
                        st.rerun()
        else:
            st.caption("No liked artists yet")

    with col2:
        st.markdown(f"### ❌ Passed Artists ({len(st.session_state.prefs['disliked'])})")

        if st.session_state.prefs['disliked']:
            for i, artist in enumerate(sorted(st.session_state.prefs['disliked'])):
                col_a, col_b = st.columns([3, 1])
                with col_a:
                    st.markdown(f"**{artist}**")
                with col_b:
                    if st.button("✅", key=f"relike_{i}", help="Move to Liked"):
                        st.session_state.prefs['disliked'].remove(artist)
                        st.session_state.prefs['liked'].append(artist)
                        save_preference(user.id, artist, 'liked')
			st.session_state.scroll_to_top = True
                        st.rerun()
        else:
            st.caption("No passed artists yet")

    st.stop()

# ==================== MAIN UI ====================
st.title("🎸 Artist Swipe")
st.markdown('<div id="top"></div>', unsafe_allow_html=True)
st.markdown("Discover artists and decide if you want to see them live!")

# Progress
total_artists = len(st.session_state.artists_list)

if total_artists == 0:
    st.info("🎵 No artists to swipe on! Go to 'Discover Concerts' first to find shows.")
    if st.button("🔍 Go to Discover Concerts"):
        st.switch_page("pages/2_discover_concerts.py")
    st.stop()

progress = st.session_state.current_idx / max(total_artists, 1)

# Top metrics
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Progress", f"{st.session_state.current_idx}/{total_artists}")
with col2:
    st.metric("✅ Liked", len(st.session_state.prefs['liked']))
with col3:
    st.metric("❌ Passed", len(st.session_state.prefs['disliked']))
with col4:
    remaining = total_artists - st.session_state.current_idx
    st.metric("Remaining", remaining)

st.progress(progress)

# Check if done
if st.session_state.current_idx >= total_artists:
    st.success("🎉 You've reviewed all artists!")
    st.balloons()

    col1, col2 = st.columns(2)
    with col1:
        st.metric("✅ Total Liked", len(st.session_state.prefs['liked']))
    with col2:
        st.metric("❌ Total Passed", len(st.session_state.prefs['disliked']))

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("🔄 Reset and Start Over", use_container_width=True):
            # Clear all preferences from database
            for artist in st.session_state.prefs['liked']:
                supabase.table("preferences").delete().eq("user_id", user.id).eq("artist_name", artist).execute()
            for artist in st.session_state.prefs['disliked']:
                supabase.table("preferences").delete().eq("user_id", user.id).eq("artist_name", artist).execute()

            st.session_state.prefs = {"liked": [], "disliked": [], "swipe_history": []}
            st.session_state.current_idx = 0
            st.rerun()
    with col_b:
        if st.button("📝 Review Choices", use_container_width=True, type="primary"):
            st.session_state.show_review_page = True
            st.rerun()

    st.stop()

# Current artist
artist = st.session_state.artists_list[st.session_state.current_idx]
df = load_concerts(user.id)
artist_shows = df[df['artist_name'] == artist].sort_values('date')
show_count = len(artist_shows)
next_show = artist_shows.iloc[0] if show_count > 0 else None

# ==================== SPOTIFY DATA ====================
spotify_data = None
top_tracks = []
albums = []

if st.session_state.spotify_token:
    with st.spinner("Loading artist info..."):
        spotify_data = search_artist_spotify(artist, st.session_state.spotify_token)
        if spotify_data:
            top_tracks = get_artist_top_tracks(spotify_data['spotify_id'], st.session_state.spotify_token, limit=10)
            albums = get_artist_albums(spotify_data['spotify_id'], st.session_state.spotify_token)

# ==================== ARTIST CARD ====================
st.markdown("---")

col_img, col_info = st.columns([1, 2])

with col_img:
    if spotify_data and spotify_data['image']:
        st.image(spotify_data['image'], use_container_width=True)
    else:
        st.markdown("### 🎤")
        st.markdown(f"**{artist}**")

with col_info:
    st.markdown(f"## {artist}")

    if spotify_data:
        if spotify_data['followers']:
            st.markdown(f"👥 **{spotify_data['followers']:,} followers**")

        if spotify_data['genres']:
            st.markdown(f"🎵 **Genres:** {', '.join(spotify_data['genres'])}")

    # Show concert details
    if next_show is not None:
        st.markdown("### 🎫 Concert Details")
        st.markdown(f"**Event:** {next_show['event_name']}")
        st.markdown(f"**Venue:** {next_show['venue_name']}")
        st.markdown(f"**Location:** {next_show['city']}, {next_show['state']}")
        st.markdown(f"**Date:** {next_show['date']}")
        if next_show.get('time'):
            st.markdown(f"**Time:** {next_show['time']}")

# ==================== TOP TRACKS ====================
if top_tracks:
    st.markdown("---")
    st.markdown("### 🎵 Top 5 Tracks")
    
    for i, track in enumerate(top_tracks[:5], 1):
        with st.container():
            st.markdown(f"**{i}. {track['name']}**")
            st.caption(f"from {track['album_name']}")
            
            if track['preview_url']:
                st.audio(track['preview_url'], format="audio/mp3")
            elif track.get('spotify_url'):
                safe_key = f"{st.session_state.current_idx}_{i}"
                
                col_a, col_b = st.columns(2)
                
                with col_a:
                    # Spotify button - opens in new tab
                    spotify_html = f"""
                    <a href="{track['spotify_url']}" target="_blank" style="text-decoration: none;">
                        <button style="
                            background-color: #1DB954;
                            color: white;
                            border: none;
                            padding: 10px 20px;
                            font-size: 16px;
                            border-radius: 5px;
                            cursor: pointer;
                            width: 100%;
                            font-weight: bold;
                        ">
                            🎵 Listen on Spotify
                        </button>
                    </a>
                    """
                    st.markdown(spotify_html, unsafe_allow_html=True)
                
                with col_b:
                    # YouTube button - opens in new tab
                    youtube_url = get_youtube_search_url(track['artist'], track['name'])
                    youtube_html = f"""
                    <a href="{youtube_url}" target="_blank" style="text-decoration: none;">
                        <button style="
                            background-color: #FF0000;
                            color: white;
                            border: none;
                            padding: 10px 20px;
                            font-size: 16px;
                            border-radius: 5px;
                            cursor: pointer;
                            width: 100%;
                            font-weight: bold;
                        ">
                            ▶️ Find on YouTube
                        </button>
                    </a>
                    """
                    st.markdown(youtube_html, unsafe_allow_html=True)
            else:
                st.caption("🔇 No preview available")
            
            st.markdown("")  # Spacing


# ==================== ALBUMS ====================
if albums:
    st.markdown("---")
    st.markdown("### 💿 Top 5 Albums")
    cols = st.columns(min(5, len(albums)))
    for i, album in enumerate(albums[:5]):
        with cols[i]:
            if album['image']:
                st.image(album['image'], use_container_width=True)
            st.caption(album['name'])

# ==================== ACTION BUTTONS ====================
st.markdown("---")
st.markdown("### What do you think?")

# Main swipe buttons
# Main swipe buttons
col1, col2, col3 = st.columns([1, 1, 1])

with col1:
    if st.button("❌ Pass", use_container_width=True, type="secondary", key="pass"):
        st.session_state.prefs['disliked'].append(artist)
        st.session_state.prefs['swipe_history'].append({
            "artist": artist,
            "action": "disliked",
            "timestamp": pd.Timestamp.now().isoformat()
        })
        st.session_state.current_idx += 1
        save_preference(user.id, artist, 'disliked')
        st.session_state.scroll_to_top = True
        st.rerun()

with col2:
    # Undo button
    if st.session_state.current_idx > 0:
        if st.button("↩️ Undo", use_container_width=True, type="secondary"):
            last_history = st.session_state.prefs['swipe_history'][-1] if st.session_state.prefs['swipe_history'] else None

            if last_history:
                last_artist = last_history['artist']
                last_action = last_history['action']

                if last_action == 'liked' and last_artist in st.session_state.prefs['liked']:
                    st.session_state.prefs['liked'].remove(last_artist)
                elif last_action == 'disliked' and last_artist in st.session_state.prefs['disliked']:
                    st.session_state.prefs['disliked'].remove(last_artist)

                st.session_state.prefs['swipe_history'].pop()
                st.session_state.current_idx -= 1

                supabase.table("preferences").delete().eq("user_id", user.id).eq("artist_name", last_artist).execute()
		st.session_state.scroll_to_top = True
                st.rerun()

with col3:
    if st.button("✅ Like", use_container_width=True, type="primary", key="like"):
        st.session_state.prefs['liked'].append(artist)
        st.session_state.prefs['swipe_history'].append({
            "artist": artist,
            "action": "liked",
            "timestamp": pd.Timestamp.now().isoformat()
        })
        st.session_state.current_idx += 1
        save_preference(user.id, artist, 'liked')
        st.session_state.scroll_to_top = True
        st.rerun()

# Show progress
st.caption(f"Concert {st.session_state.current_idx + 1} of {total_artists}")

# ==================== SIDEBAR ====================
with st.sidebar:
    st.markdown("### 📊 Your Stats")
    st.metric("✅ Liked Artists", len(st.session_state.prefs['liked']))
    st.metric("❌ Passed Artists", len(st.session_state.prefs['disliked']))

    st.markdown("---")

    if st.button("📝 Review & Edit All Choices", use_container_width=True, type="primary"):
        st.session_state.show_review_page = True
        st.rerun()

    st.markdown("---")

    if st.session_state.prefs['liked']:
        st.markdown("#### 💚 Recent Likes:")
        for liked_artist in st.session_state.prefs['liked'][-5:]:
            st.markdown(f"✓ {liked_artist}")