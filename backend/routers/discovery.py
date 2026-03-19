"""
Music discovery endpoints: For You, This Weekend, Surprise Me, Similar Artists.
Uses Ticketmaster (SeatGeek client_id is expired/invalid).
All external HTTP calls run concurrently via asyncio + aiohttp.
"""
import asyncio
import base64
import os
import random
from datetime import date, datetime, timedelta

import aiohttp
import requests
from fastapi import APIRouter, Depends
from supabase import Client

from dependencies import get_current_user, get_supabase

router = APIRouter()

TM_URL = "https://app.ticketmaster.com/discovery/v2/events.json"

# Module-level Spotify token cache
_spotify_token_cache: str | None = None


def _get_spotify_token() -> str:
    global _spotify_token_cache
    if _spotify_token_cache:
        return _spotify_token_cache
    cid = os.getenv("SPOTIFY_CLIENT_ID", "")
    secret = os.getenv("SPOTIFY_CLIENT_SECRET", "")
    auth = base64.b64encode(f"{cid}:{secret}".encode()).decode()
    r = requests.post(
        "https://accounts.spotify.com/api/token",
        headers={"Authorization": f"Basic {auth}", "Content-Type": "application/x-www-form-urlencoded"},
        data={"grant_type": "client_credentials"},
        timeout=10,
    )
    r.raise_for_status()
    _spotify_token_cache = r.json()["access_token"]
    return _spotify_token_cache


def _liked_artists(supabase: Client, user_id: str) -> list[str]:
    result = (
        supabase.table("preferences")
        .select("artist_name")
        .eq("user_id", user_id)
        .eq("preference", "liked")
        .execute()
    )
    return [p["artist_name"] for p in (result.data or [])]


def _normalize_tm(event: dict, matched_artist: str = "", because_of: str = "", score: float = 0) -> dict:
    """Convert a Ticketmaster event into a flat dict the frontend normalize() understands."""
    venue = event.get("_embedded", {}).get("venues", [{}])[0]
    dates = event.get("dates", {}).get("start", {})
    prices = event.get("priceRanges", [])
    attractions = event.get("_embedded", {}).get("attractions", [{}])
    dt_date = dates.get("localDate", "")
    dt_time = dates.get("localTime", "")
    datetime_local = f"{dt_date}T{dt_time}" if dt_date and dt_time else dt_date
    return {
        "id": event.get("id", ""),
        "title": event.get("name", ""),
        "performers": [{"name": a.get("name", ""), "image": (a.get("images") or [{}])[0].get("url")} for a in attractions],
        "venue": {
            "name": venue.get("name", ""),
            "city": venue.get("city", {}).get("name", ""),
            "state": venue.get("state", {}).get("stateCode", ""),
        },
        "datetime_local": datetime_local,
        "url": event.get("url", ""),
        "stats": {
            "lowest_price": prices[0].get("min") if prices else None,
            "highest_price": prices[0].get("max") if prices else None,
        },
        "_matched_artist": matched_artist,
        "_because_of": because_of,
        "score": score,
    }


# ── Async TM helpers ──────────────────────────────────────────────────────────

TM_BASE_PARAMS = {
    "city": "Austin",
    "stateCode": "TX",
    "radius": "30",
    "unit": "miles",
    "segmentName": "Music",
    "sort": "date,asc",
    "startDateTime": "",  # filled in per-call
}


async def _tm_search(session: aiohttp.ClientSession, artist: str, extra: dict = None) -> list[dict]:
    params = {
        **TM_BASE_PARAMS,
        "apikey": os.getenv("TICKETMASTER_API_KEY", ""),
        "keyword": artist,
        "size": 5,
        "startDateTime": f"{date.today().isoformat()}T00:00:00Z",
    }
    if extra:
        params.update(extra)
    try:
        async with session.get(TM_URL, params=params, timeout=aiohttp.ClientTimeout(total=10)) as r:
            if r.status == 200:
                data = await r.json(content_type=None)
                return data.get("_embedded", {}).get("events", [])
    except Exception:
        pass
    return []


async def _tm_browse(session: aiohttp.ClientSession, extra: dict = None) -> list[dict]:
    params = {
        **TM_BASE_PARAMS,
        "apikey": os.getenv("TICKETMASTER_API_KEY", ""),
        "size": 20,
        "startDateTime": f"{date.today().isoformat()}T00:00:00Z",
    }
    if extra:
        params.update(extra)
    try:
        async with session.get(TM_URL, params=params, timeout=aiohttp.ClientTimeout(total=10)) as r:
            if r.status == 200:
                data = await r.json(content_type=None)
                return data.get("_embedded", {}).get("events", [])
    except Exception:
        pass
    return []


async def _spotify_related_async(session: aiohttp.ClientSession, artist_name: str, token: str) -> tuple[str, list[str]]:
    headers = {"Authorization": f"Bearer {token}"}
    try:
        async with session.get(
            "https://api.spotify.com/v1/search",
            headers=headers,
            params={"q": artist_name, "type": "artist", "limit": 1},
            timeout=aiohttp.ClientTimeout(total=8),
        ) as r:
            if r.status != 200:
                return artist_name, []
            items = (await r.json(content_type=None)).get("artists", {}).get("items", [])
            if not items:
                return artist_name, []
            artist_id = items[0]["id"]

        async with session.get(
            f"https://api.spotify.com/v1/artists/{artist_id}/related-artists",
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=8),
        ) as r:
            if r.status != 200:
                return artist_name, []
            related = [a["name"] for a in (await r.json(content_type=None)).get("artists", [])[:5]]
            return artist_name, related
    except Exception:
        return artist_name, []


def _dedupe(events: list[dict]) -> list[dict]:
    seen: set = set()
    out = []
    for e in events:
        eid = e.get("id", "")
        if eid and eid not in seen:
            seen.add(eid)
            out.append(e)
    return out


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/for-you")
async def for_you(user=Depends(get_current_user), supabase: Client = Depends(get_supabase)):
    liked = _liked_artists(supabase, str(user.id))
    if not liked:
        return {
            "events": [],
            "hint": "No liked artists yet — use Artist Swipe to rate some artists and we'll find matching shows.",
        }

    async with aiohttp.ClientSession() as session:
        results = await asyncio.gather(*[_tm_search(session, artist) for artist in liked[:12]])

    seen_ids: set = set()
    all_events = []
    for artist, raw_events in zip(liked, results):
        for ev in raw_events:
            if ev["id"] not in seen_ids:
                seen_ids.add(ev["id"])
                all_events.append(_normalize_tm(ev, matched_artist=artist, score=100))

    all_events.sort(key=lambda e: e.get("datetime_local", ""))
    return {"events": all_events[:25]}


@router.get("/this-weekend")
async def this_weekend(user=Depends(get_current_user), supabase: Client = Depends(get_supabase)):
    liked_lower = {a.lower() for a in _liked_artists(supabase, str(user.id))}
    today = datetime.now()
    days_to_friday = (4 - today.weekday()) % 7
    if days_to_friday == 0 and today.hour >= 18:
        days_to_friday = 7
    friday = today + timedelta(days=days_to_friday)
    sunday = friday + timedelta(days=2)

    async with aiohttp.ClientSession() as session:
        raw = await _tm_browse(session, {
            "startDateTime": f"{friday.strftime('%Y-%m-%d')}T00:00:00Z",
            "endDateTime": f"{sunday.strftime('%Y-%m-%d')}T23:59:59Z",
            "size": 25,
        })

    events = [_normalize_tm(ev) for ev in raw]

    def weekend_score(e):
        performers = {p["name"].lower() for p in e.get("performers", [])}
        return 1 if performers & liked_lower else 0

    events.sort(key=weekend_score, reverse=True)
    return {"events": events}


@router.get("/surprise")
async def surprise(user=Depends(get_current_user)):
    # Fetch a random page from the 340 available Austin music events
    rand_page = random.randint(0, 16)  # ~340 events / 20 per page
    async with aiohttp.ClientSession() as session:
        raw = await _tm_browse(session, {"size": 20, "page": rand_page})
    if not raw:
        # fallback to page 0 if random page is empty
        async with aiohttp.ClientSession() as session:
            raw = await _tm_browse(session, {"size": 20})
    if not raw:
        return {"events": []}
    return {"events": [_normalize_tm(random.choice(raw))]}


@router.get("/similar")
async def similar(user=Depends(get_current_user), supabase: Client = Depends(get_supabase)):
    liked = _liked_artists(supabase, str(user.id))
    if not liked:
        return {"events": [], "hint": "Like some artists first so we can find similar acts near you."}

    liked_lower = {a.lower() for a in liked}

    try:
        token = _get_spotify_token()
    except Exception:
        return {"events": [], "hint": "Could not reach Spotify. Check your API credentials."}

    async with aiohttp.ClientSession() as session:
        related_results = await asyncio.gather(
            *[_spotify_related_async(session, artist, token) for artist in liked[:5]]
        )

        seen_related: set[str] = set()
        related_pairs: list[tuple[str, str]] = []
        for source_artist, related_names in related_results:
            for name in related_names:
                key = name.lower()
                if key not in liked_lower and key not in seen_related:
                    seen_related.add(key)
                    related_pairs.append((name, source_artist))

        if not related_pairs:
            return {"events": [], "hint": "No related artists found. Try liking more artists via Artist Swipe."}

        tm_results = await asyncio.gather(
            *[_tm_search(session, rel_artist, {"size": 3}) for rel_artist, _ in related_pairs[:15]]
        )

    seen_ids: set = set()
    all_events = []
    for (rel_artist, because_of), raw_events in zip(related_pairs, tm_results):
        for ev in raw_events:
            if ev["id"] not in seen_ids:
                seen_ids.add(ev["id"])
                all_events.append(_normalize_tm(ev, matched_artist=rel_artist, because_of=because_of, score=70))

    all_events.sort(key=lambda e: e.get("datetime_local", ""))
    return {"events": all_events[:20]}
