"""Artist info, top tracks, and albums via Spotify client credentials."""
import base64
import os

import requests
from fastapi import APIRouter, HTTPException
from functools import lru_cache

router = APIRouter()


@lru_cache(maxsize=1)
def _app_token() -> str:
    cid = os.getenv("SPOTIFY_CLIENT_ID", "")
    secret = os.getenv("SPOTIFY_CLIENT_SECRET", "")
    auth = base64.b64encode(f"{cid}:{secret}".encode()).decode()
    r = requests.post(
        "https://accounts.spotify.com/api/token",
        headers={"Authorization": f"Basic {auth}", "Content-Type": "application/x-www-form-urlencoded"},
        data={"grant_type": "client_credentials"},
    )
    r.raise_for_status()
    return r.json()["access_token"]


def _headers():
    return {"Authorization": f"Bearer {_app_token()}"}


def _search_artist(name: str):
    r = requests.get(
        "https://api.spotify.com/v1/search",
        headers=_headers(),
        params={"q": name, "type": "artist", "limit": 1},
    )
    items = r.json().get("artists", {}).get("items", [])
    return items[0] if items else None


@router.get("/{name}/info")
def get_artist_info(name: str):
    artist = _search_artist(name)
    if not artist:
        raise HTTPException(status_code=404, detail="Artist not found")
    return {
        "name": artist["name"],
        "image": artist["images"][0]["url"] if artist["images"] else None,
        "genres": artist["genres"][:3],
        "followers": artist["followers"]["total"],
        "popularity": artist["popularity"],
        "spotify_url": artist["external_urls"]["spotify"],
        "spotify_id": artist["id"],
    }


@router.get("/{name}/tracks")
def get_artist_tracks(name: str):
    artist = _search_artist(name)
    if not artist:
        return []
    r = requests.get(
        f"https://api.spotify.com/v1/artists/{artist['id']}/top-tracks",
        headers=_headers(),
        params={"market": "US"},
    )
    tracks = r.json().get("tracks", [])
    return [
        {
            "name": t["name"],
            "artist": t["artists"][0]["name"],
            "preview_url": t["preview_url"],
            "album_image": t["album"]["images"][0]["url"] if t["album"]["images"] else None,
            "album_name": t["album"]["name"],
            "spotify_url": t["external_urls"]["spotify"],
        }
        for t in tracks[:5]
    ]


@router.get("/{name}/albums")
def get_artist_albums(name: str):
    artist = _search_artist(name)
    if not artist:
        return []
    r = requests.get(
        f"https://api.spotify.com/v1/artists/{artist['id']}/albums",
        headers=_headers(),
        params={"market": "US", "limit": 3, "include_groups": "album"},
    )
    albums = r.json().get("items", [])
    return [
        {
            "name": a["name"],
            "image": a["images"][0]["url"] if a["images"] else None,
            "release_date": a["release_date"],
            "spotify_url": a["external_urls"]["spotify"],
        }
        for a in albums
    ]
