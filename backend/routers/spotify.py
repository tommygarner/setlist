"""Spotify OAuth redirect flow — stores tokens in Supabase profiles table."""
import os
from datetime import datetime, timedelta

import requests
from fastapi import APIRouter, Query
from fastapi.responses import RedirectResponse
from spotipy.oauth2 import SpotifyOAuth

router = APIRouter()

SCOPE = "user-library-read user-top-read"


def _auth_manager(state: str = None):
    return SpotifyOAuth(
        client_id=os.getenv("SPOTIFY_CLIENT_ID"),
        client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
        redirect_uri=os.getenv("SPOTIFY_REDIRECT_URI"),
        scope=SCOPE,
        state=state,
        cache_path=None,
        open_browser=False,
    )


@router.get("/auth")
def spotify_auth(user_id: str = Query(...)):
    """Redirect user to Spotify authorization page, passing user_id as state."""
    manager = _auth_manager(state=user_id)
    return RedirectResponse(url=manager.get_authorize_url())


@router.get("/callback")
def spotify_callback(code: str = Query(...), state: str = Query(...)):
    """Handle OAuth callback, store tokens, redirect to frontend."""
    from supabase import create_client
    supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))

    manager = _auth_manager(state=state)
    token_info = manager.get_access_token(code, as_dict=True, check_cache=False)

    expires_at = datetime.utcnow() + timedelta(seconds=token_info["expires_in"])
    supabase.table("profiles").update({
        "spotify_connected": True,
        "spotify_access_token": token_info["access_token"],
        "spotify_refresh_token": token_info["refresh_token"],
        "spotify_token_expires_at": expires_at.isoformat(),
    }).eq("id", state).execute()

    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
    return RedirectResponse(url=f"{frontend_url}/connect-spotify?connected=true")
