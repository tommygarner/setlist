import base64
from datetime import datetime, timedelta

import requests
import streamlit as st


def get_spotify_app_token() -> str:
    """Get Spotify access token using client credentials flow (app-level, no user scope)."""
    client_id = st.secrets["spotify"]["CLIENT_ID"]
    client_secret = st.secrets["spotify"]["CLIENT_SECRET"]
    auth_b64 = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()

    response = requests.post(
        "https://accounts.spotify.com/api/token",
        headers={
            "Authorization": f"Basic {auth_b64}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={"grant_type": "client_credentials"},
    )
    return response.json()["access_token"]


def get_valid_user_token(supabase, user_id: str):
    """Get a valid user-scoped Spotify token, refreshing if expired. Returns None if not connected."""
    try:
        profile = supabase.table("profiles").select("*").eq("id", user_id).execute()
        if not profile.data:
            return None

        user_data = profile.data[0]
        expires_at = user_data.get("spotify_token_expires_at")

        if expires_at:
            expires_dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            if datetime.now(expires_dt.tzinfo) >= expires_dt:
                st.info("🔄 Refreshing Spotify token...")
                from spotipy.oauth2 import SpotifyOAuth

                auth_manager = SpotifyOAuth(
                    client_id=st.secrets["spotify"]["CLIENT_ID"],
                    client_secret=st.secrets["spotify"]["CLIENT_SECRET"],
                    redirect_uri=st.secrets["spotify"]["REDIRECT_URI"],
                    scope="user-library-read user-top-read",
                )
                refresh_token = user_data.get("spotify_refresh_token")
                if refresh_token:
                    token_info = auth_manager.refresh_access_token(refresh_token)
                    new_expires = datetime.utcnow() + timedelta(seconds=token_info["expires_in"])
                    supabase.table("profiles").update({
                        "spotify_access_token": token_info["access_token"],
                        "spotify_token_expires_at": new_expires.isoformat(),
                    }).eq("id", user_id).execute()
                    return token_info["access_token"]

        return user_data.get("spotify_access_token")
    except Exception as e:
        st.error(f"Token refresh error: {str(e)}")
        return None
