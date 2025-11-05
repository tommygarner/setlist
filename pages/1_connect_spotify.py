import streamlit as st
from supabase import create_client, Client
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import time
from datetime import datetime, timedelta

st.set_page_config(page_title="🎵 Connect Spotify", page_icon="🎵", layout="wide")

# Initialize Supabase
def init_supabase() -> Client:
    url = st.secrets["connections"]["supabase"]["SUPABASE_URL"]
    key = st.secrets["connections"]["supabase"]["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_supabase()

def check_session():
    try:
        session = supabase.auth.get_session()
        if session and session.user:
            st.session_state.user = session.user
            st.session_state.authenticated = True
    except:
        pass
check_session()

# Check authentication - MUST BE AT TOP
if "authenticated" not in st.session_state or not st.session_state.authenticated:
    st.error("❌ Please login first!")
    if st.button("← Go to Main App", key="main_app_btn"):
        st.switch_page("app.py")
    st.stop()

# Now safe to access user
current_user = st.session_state.user

# Check if user has Spotify tokens
def check_spotify_connection(user_id):
    """Check if user has valid Spotify connection"""
    try:
        profile = supabase.table("profiles").select("spotify_access_token, spotify_token_expires_at").eq("id", user_id).execute()
        validate = profile.data[0] if profile.data else None
        if not validate or not validate.get('spotify_access_token'):
            return False
        expires_at = validate.get('spotify_token_expires_at')
        if expires_at:
            expires_datetime = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
            if datetime.now(expires_datetime.tzinfo) < expires_datetime:
                return True
        return False
    except:
        return False

# Save Spotify tokens
def save_spotify_tokens(user_id, access_token, refresh_token, expires_in):
    """Save Spotify OAuth tokens to database"""
    try:
        expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        supabase.table("profiles").update({
            "spotify_connected": True,
            "spotify_access_token": access_token,
            "spotify_refresh_token": refresh_token,
            "spotify_token_expires_at": expires_at.isoformat()
        }).eq("id", user_id).execute()
        return True
    except Exception as e:
        st.error(f"Error saving tokens: {str(e)}")
        return False

# Page header
st.title("🎵 Connect Your Spotify")
st.write("Link your Spotify account to discover concerts from your favorite artists")

# Check if already connected
is_connected = check_spotify_connection(current_user.id)

if is_connected:
    # Already connected
    st.success("✅ Spotify Connected!")
    st.balloons()
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🎤 Go to Discover Concerts →", type="primary", use_container_width=True, key="discover_btn"):
            st.switch_page("pages/2_discover_concerts.py")
    with col2:
        if st.button("🔄 Reconnect Spotify", use_container_width=True, key="reconnect_btn"):
            supabase.table("profiles").update({
                "spotify_connected": False,
                "spotify_access_token": None,
                "spotify_refresh_token": None,
                "spotify_token_expires_at": None
            }).eq("id", current_user.id).execute()
            st.rerun()
else:
    # Not connected - show connection flow
    st.info("🎵 Connect your Spotify to discover concerts")
    st.write("**What we'll access:**")
    st.write("• Your liked songs")
    st.write("• Your top artists")
    st.divider()
    # Handle OAuth callback
    query_params = st.query_params
    if 'code' in query_params:
        code = query_params['code']
        with st.spinner("🔗 Connecting to Spotify..."):
            try:
                auth_manager = SpotifyOAuth(
                    client_id=st.secrets["spotify"]["CLIENT_ID"],
                    client_secret=st.secrets["spotify"]["CLIENT_SECRET"],
                    redirect_uri=st.secrets["spotify"]["REDIRECT_URI"],
                    scope="user-library-read user-top-read"
                )
                token_info = auth_manager.get_access_token(code, as_dict=True, check_cache=False)
                if token_info:
                    success = save_spotify_tokens(
                        current_user.id,
                        token_info['access_token'],
                        token_info['refresh_token'],
                        token_info['expires_in']
                    )
                    if success:
                        st.success("✅ Spotify Connected!")
                        st.balloons()
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.error("Failed to save Spotify connection")
                else:
                    st.error("Failed to get Spotify tokens")
            except Exception as e:
                st.error(f"Connection error: {str(e)}")
    else:
        # Show connect button
        auth_manager = SpotifyOAuth(
            client_id=st.secrets["spotify"]["CLIENT_ID"],
            client_secret=st.secrets["spotify"]["CLIENT_SECRET"],
            redirect_uri=st.secrets["spotify"]["REDIRECT_URI"],
            scope="user-library-read user-top-read"
        )
        auth_url = auth_manager.get_authorize_url()
        # Debug line - shows the OAuth URL (remove after testing)
        st.write("OAuth URL:", auth_url)
        st.link_button("🎵 Connect Spotify", auth_url, type="primary", use_container_width=True)
        st.caption("You'll be redirected to Spotify to authorize access")
