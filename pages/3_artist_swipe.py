import streamlit as st
from supabase import create_client, Client
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import requests
from urllib.parse import quote

st.set_page_config(page_title="🎸 Artist Swipe", page_icon="🎸", layout="wide")

# Initialize Supabase
def init_supabase() -> Client:
    url = st.secrets["connections"]["supabase"]["SUPABASE_URL"]
    key = st.secrets["connections"]["supabase"]["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_supabase()

# Check authentication
if "authenticated" not in st.session_state or not st.session_state.authenticated:
    st.error("Please login first!")
    st.stop()

user = st.session_state.user

# Initialize Spotify
@st.cache_resource
def get_spotify_client():
    auth_manager = SpotifyOAuth(
        client_id=st.secrets["spotify"]["CLIENT_ID"],
        client_secret=st.secrets["spotify"]["CLIENT_SECRET"],
        redirect_uri=st.secrets["spotify"]["REDIRECT_URI"],
        scope="user-library-read"
    )
    return spotipy.Spotify(auth_manager=auth_manager)

sp = get_spotify_client()

# Fetch artist info from Spotify
@st.cache_data(ttl=3600)
def get_artist_info(artist_name):
    """Get artist info including image, top tracks, and albums"""
    try:
        # Search for artist
        results = sp.search(q=f"artist:{artist_name}", type="artist", limit=1)
        
        if not results['artists']['items']:
            return None
        
        artist = results['artists']['items'][0]
        artist_id = artist['id']
        
        # Get artist image
        image_url = artist['images'][0]['url'] if artist['images'] else None
        
        # Get top tracks
        top_tracks_result = sp.artist_top_tracks(artist_id, country='US')
        top_tracks = top_tracks_result['tracks'][:5]
        
        # Get albums
        albums_result = sp.artist_albums(artist_id, album_type='album', limit=5, country='US')
        albums = albums_result['items']
        
        return {
            'name': artist['name'],
            'image': image_url,
            'followers': artist['followers']['total'],
            'genres': artist['genres'],
            'spotify_url': artist['external_urls']['spotify'],
            'top_tracks': [{
                'name': track['name'],
                'album': track['album']['name'],
                'spotify_url': track['external_urls']['spotify'],
                'preview_url': track.get('preview_url'),
                'image': track['album']['images'][0]['url'] if track['album']['images'] else None
            } for track in top_tracks],
            'albums': [{
                'name': album['name'],
                'release_date': album['release_date'],
                'spotify_url': album['external_urls']['spotify'],
                'image': album['images'][0]['url'] if album['images'] else None
            } for album in albums]
        }
    except Exception as e:
        st.error(f"Error fetching artist info: {str(e)}")
        return None

def get_youtube_search_url(query):
    """Generate YouTube search URL"""
    return f"https://www.youtube.com/results?search_query={quote(query)}"

# Main App
st.title("🎸 Artist Swipe")
st.write("Discover artists and decide if you want to see them live!")

# Initialize session state
if 'current_index' not in st.session_state:
    st.session_state.current_index = 0

# Load concerts from database
@st.cache_data(ttl=300)
def load_concerts(user_id):
    result = supabase.table("concerts_discovered").select("*").eq("user_id", user_id).order("date").execute()
    return result.data

concerts = load_concerts(user.id)

if not concerts:
    st.info("No concerts discovered yet! Go to Discover Concerts to find shows.")
    if st.button("🎤 Go to Discover Concerts"):
        st.switch_page("pages/2_discover_concerts.py")
    st.stop()

# Get current concert
if st.session_state.current_index >= len(concerts):
    st.success("🎉 You've swiped through all concerts!")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 Start Over", use_container_width=True):
            st.session_state.current_index = 0
            st.rerun()
    with col2:
        if st.button("🎤 Discover More Concerts", use_container_width=True):
            st.switch_page("pages/2_discover_concerts.py")
    st.stop()

concert = concerts[st.session_state.current_index]

# Fetch artist info
with st.spinner(f"🔍 Loading {concert['artist_name']} info..."):
    artist_info = get_artist_info(concert['artist_name'])

st.divider()

# Display Artist Card
if artist_info:
    # Artist Header with Image
    col_img, col_info = st.columns([1, 2])
    
    with col_img:
        if artist_info['image']:
            st.image(artist_info['image'], use_container_width=True)
        else:
            st.info("No image available")
    
    with col_info:
        st.markdown(f"# {artist_info['name']}")
        st.markdown(f"**👥 {artist_info['followers']:,} followers**")
        
        if artist_info['genres']:
            st.markdown(f"**🎵 Genres:** {', '.join(artist_info['genres'][:3])}")
        
        st.link_button("🎧 Open in Spotify", artist_info['spotify_url'], use_container_width=True)
        st.link_button("📺 Search on YouTube", get_youtube_search_url(artist_info['name']), use_container_width=True)
    
    st.divider()
    
    # Concert Details
    st.subheader("🎫 Concert Details")
    col1, col2 = st.columns(2)
    
    with col1:
        st.write(f"**Event:** {concert['event_name']}")
        st.write(f"**Venue:** {concert['venue_name']}")
        st.write(f"**Location:** {concert['city']}, {concert['state']}")
    
    with col2:
        st.write(f"**Date:** {concert['date']}")
        if concert.get('time'):
            st.write(f"**Time:** {concert['time']}")
        if concert.get('min_price') and concert.get('max_price'):
            st.write(f"**Price:** ${concert['min_price']} - ${concert['max_price']}")
    
    if concert.get('ticket_url'):
        st.link_button("🎟️ Get Tickets", concert['ticket_url'], use_container_width=True)
    
    st.divider()
    
    # Top Tracks
    # Top Tracks
    st.subheader("🎵 Top 5 Tracks")
    
    for i, track in enumerate(artist_info['top_tracks'], 1):
        with st.container():
            col_img, col_info, col_spotify, col_youtube = st.columns([1, 4, 1, 1])
            
            with col_img:
                if track['image']:
                    st.image(track['image'], width=80)
                else:
                    st.write("🎵")
            
            with col_info:
                st.write(f"**{i}. {track['name']}**")
                st.caption(f"from {track['album']}")
            
            with col_spotify:
                st.link_button("🎧", track['spotify_url'], use_container_width=True)
            
            with col_youtube:
                youtube_url = get_youtube_search_url(f"{artist_info['name']} {track['name']}")
                st.link_button("📺", youtube_url, use_container_width=True)
            
            st.divider()
    
    # Top Albums
    # Top Albums
    st.subheader("💿 Top 5 Albums")
    
    album_cols = st.columns(5)
    for i, album in enumerate(artist_info['albums'][:5]):
        with album_cols[i]:
            if album['image']:
                st.image(album['image'], use_container_width=True)
            st.caption(f"**{album['name']}**")
            st.caption(album['release_date'][:4])
            st.link_button("🎧", album['spotify_url'], use_container_width=True)

else:
    # Fallback if Spotify API fails
    st.warning(f"Could not load info for {concert['artist_name']}")
    st.markdown(f"### {concert['event_name']}")
    st.write(f"🎤 **{concert['artist_name']}**")
    st.write(f"📍 {concert['venue_name']}, {concert['city']}, {concert['state']}")
    st.write(f"📅 {concert['date']}")

st.divider()

# Swipe buttons
st.subheader("What do you think?")

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("👎 Not Interested", use_container_width=True, type="secondary", key="dislike"):
        # Save preference
        try:
            supabase.table("preferences").upsert({
                "user_id": user.id,
                "artist_name": concert['artist_name'],
                "preference": "disliked"
            }).execute()
        except:
            pass
        
        st.session_state.current_index += 1
        st.rerun()

with col2:
    if st.button("⏭️ Skip", use_container_width=True, key="skip"):
        st.session_state.current_index += 1
        st.rerun()

with col3:
    if st.button("❤️ I'm Interested!", use_container_width=True, type="primary", key="like"):
        # Save preference
        try:
            supabase.table("preferences").upsert({
                "user_id": user.id,
                "artist_name": concert['artist_name'],
                "preference": "liked"
            }).execute()
        except:
            pass
        
        st.session_state.current_index += 1
        st.rerun()

# Progress
st.divider()
progress = (st.session_state.current_index) / len(concerts)
st.progress(progress)
st.caption(f"Concert {st.session_state.current_index + 1} of {len(concerts)}")
