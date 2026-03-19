"""
Concert discovery and retrieval.
Ports the async Ticketmaster + SeatGeek fan-out from 2_discover_concerts.py.
"""
import asyncio
import json
import os
from datetime import date, datetime, timedelta, timezone
from typing import Optional

import aiohttp
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from supabase import Client

from dependencies import get_current_user, get_supabase

router = APIRouter()

HEADERS = {
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0",
}


async def _search_ticketmaster(session, artist, api_key, city, state, radius):
    today = date.today().isoformat()
    params = {
        "apikey": api_key,
        "keyword": artist,
        "city": city,
        "stateCode": state,
        "radius": radius,
        "unit": "miles",
        "segmentName": "Music",
        "sort": "date,asc",
        "startDateTime": f"{today}T00:00:00Z",
    }
    try:
        async with session.get(
            "https://app.ticketmaster.com/discovery/v2/events.json",
            params=params,
            timeout=aiohttp.ClientTimeout(total=10),
        ) as r:
            if r.status == 200:
                return artist, await r.json()
    except Exception:
        pass
    return artist, None


async def _search_seatgeek(session, artist, client_id, city, state, radius):
    today = date.today().isoformat()
    params = {
        "client_id": client_id,
        "q": artist,
        "venue.city": city,
        "venue.state": state,
        "range": f"{radius}mi",
        "type": "concert",
        "per_page": 25,
        "datetime_local.gte": today,
    }
    try:
        async with session.get(
            "https://api.seatgeek.com/2/events",
            params=params,
            headers=HEADERS,
            timeout=aiohttp.ClientTimeout(total=10),
        ) as r:
            if r.status == 200:
                return artist, await r.json()
    except Exception:
        pass
    return artist, None


def _parse_tm(event, artist_name, user_id):
    try:
        venue = event.get("_embedded", {}).get("venues", [{}])[0]
        dates = event.get("dates", {}).get("start", {})
        prices = event.get("priceRanges", [])
        return {
            "user_id": user_id,
            "event_id": event.get("id"),
            "artist_name": artist_name,
            "event_name": event.get("name", ""),
            "venue_name": venue.get("name", ""),
            "city": venue.get("city", {}).get("name", ""),
            "state": venue.get("state", {}).get("stateCode", ""),
            "date": dates.get("localDate", ""),
            "time": dates.get("localTime", ""),
            "ticket_url": event.get("url", ""),
            "min_price": prices[0].get("min") if prices else None,
            "max_price": prices[0].get("max") if prices else None,
            "source": "ticketmaster",
        }
    except Exception:
        return None


def _parse_sg(event, user_id):
    try:
        performers = event.get("performers", [])
        if not performers:
            return None
        venue = event.get("venue", {})
        dt = event.get("datetime_local", "")
        date, time = (dt.split("T") + [""])[:2]
        stats = event.get("stats", {})
        return {
            "user_id": user_id,
            "event_id": f"sg_{event['id']}",
            "artist_name": performers[0].get("name", ""),
            "event_name": event.get("title", ""),
            "venue_name": venue.get("name", ""),
            "city": venue.get("city", ""),
            "state": venue.get("state", ""),
            "date": date,
            "time": time,
            "ticket_url": event.get("url", ""),
            "min_price": stats.get("lowest_price"),
            "max_price": stats.get("highest_price"),
            "source": "seatgeek",
        }
    except Exception:
        return None


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


async def _fetch_top_artists(session: aiohttp.ClientSession, access_token: str) -> dict[str, float]:
    """
    Returns {artist_name_lower: score} from Spotify top artists.
    Short-term (4 wk) contributes up to 80 pts, medium-term (6 mo) up to 40 pts.
    Both time ranges fetched concurrently.
    """
    auth = {"Authorization": f"Bearer {access_token}"}

    async def _fetch_range(time_range: str, max_pts: float):
        try:
            async with session.get(
                "https://api.spotify.com/v1/me/top/artists",
                headers=auth,
                params={"time_range": time_range, "limit": 50},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as r:
                if r.status == 200:
                    return max_pts, (await r.json(content_type=None)).get("items", [])
        except Exception:
            pass
        return max_pts, []

    results = await asyncio.gather(
        _fetch_range("short_term", 80),
        _fetch_range("medium_term", 40),
    )

    scores: dict[str, float] = {}
    for max_pts, items in results:
        for rank, artist in enumerate(items):
            name = artist["name"].lower()
            pts = max_pts * (1 - rank / len(items)) if items else 0
            scores[name] = scores.get(name, 0) + pts
    return scores


async def _fetch_liked_artists(session: aiohttp.ClientSession, access_token: str) -> list[str]:
    """Paginate through Spotify liked tracks and collect unique artist names."""
    auth = {"Authorization": f"Bearer {access_token}"}
    artists: set[str] = set()
    offset = 0
    while True:
        try:
            async with session.get(
                "https://api.spotify.com/v1/me/tracks",
                headers=auth,
                params={"limit": 50, "offset": offset},
                timeout=aiohttp.ClientTimeout(total=15),
            ) as r:
                if r.status != 200:
                    break
                data = await r.json(content_type=None)
                items = data.get("items", [])
                if not items:
                    break
                for item in items:
                    track = item.get("track")
                    if track:
                        for a in track.get("artists", []):
                            artists.add(a["name"])
                offset += 50
                if len(items) < 50:
                    break
        except Exception:
            break
    return list(artists)


def _affinity_score(artist_name: str, liked: set, disliked: set, top_scores: dict) -> float:
    name = artist_name.lower()
    if name in disliked:
        return -1.0
    score = top_scores.get(name, 0.0)
    if name in liked:
        score += 100.0
    return round(score, 2)


CACHE_TTL_HOURS = 24


def _cache_age(supabase: Client, user_id: str):
    """Return (age_hours, count) of the most recently saved concerts, or (None, 0) if none."""
    result = (
        supabase.table("concerts_discovered")
        .select("created_at")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    if not result.data:
        return None, 0
    latest = datetime.fromisoformat(result.data[0]["created_at"].replace("Z", "+00:00"))
    age_hours = (datetime.now(timezone.utc) - latest).total_seconds() / 3600
    count_result = (
        supabase.table("concerts_discovered")
        .select("id", count="exact")
        .eq("user_id", user_id)
        .execute()
    )
    return age_hours, count_result.count or 0


@router.post("/discover")
async def discover_concerts(
    city: str = Query("Austin"),
    state: str = Query("TX"),
    radius: int = Query(25),
    force: bool = Query(False),
    user=Depends(get_current_user),
    supabase: Client = Depends(get_supabase),
):
    async def stream():
        # Cache check — skip full fetch if data is fresh
        if not force:
            age_hours, count = _cache_age(supabase, str(user.id))
            if age_hours is not None and age_hours < CACHE_TTL_HOURS:
                hours_ago = round(age_hours, 1)
                yield _sse({
                    "step": f"Using cached results ({count} concerts, updated {hours_ago}h ago). Click Refresh to force update.",
                    "progress": 100,
                    "done": True,
                    "count": count,
                    "cached": True,
                })
                return

        yield _sse({"step": "Connecting to Spotify…", "progress": 5})

        profile = supabase.table("profiles").select("*").eq("id", user.id).single().execute()
        access_token = profile.data.get("spotify_access_token") if profile.data else None

        if not access_token:
            yield _sse({"step": "Spotify not connected. Go to Connect Spotify first.", "progress": 0, "error": True})
            return

        async with aiohttp.ClientSession() as session:
            yield _sse({"step": "Fetching your taste profile & liked songs…", "progress": 15})

            # Run top-artists fetch and liked-tracks fetch concurrently
            top_scores, artists = await asyncio.gather(
                _fetch_top_artists(session, access_token),
                _fetch_liked_artists(session, access_token),
            )

            # Explicit preferences from swipe screen
            pref_rows = (
                supabase.table("preferences")
                .select("artist_name,preference")
                .eq("user_id", str(user.id))
                .execute()
                .data or []
            )
            liked = {p["artist_name"].lower() for p in pref_rows if p["preference"] == "liked"}
            disliked = {p["artist_name"].lower() for p in pref_rows if p["preference"] == "disliked"}

            total_batches = max(1, (len(artists) + 19) // 20)
            yield _sse({"step": f"Found {len(artists)} artists — searching Ticketmaster…", "progress": 35})

            tm_key = os.getenv("TICKETMASTER_API_KEY", "")
            all_concerts = []

            for batch_num, i in enumerate(range(0, len(artists), 20)):
                batch = artists[i: i + 20]
                progress = 35 + int((batch_num / total_batches) * 55)
                yield _sse({
                    "step": f"Searching batch {batch_num + 1} of {total_batches}…",
                    "progress": progress,
                })

                results = await asyncio.gather(
                    *[_search_ticketmaster(session, a, tm_key, city, state, radius) for a in batch]
                )

                for artist_name, data in results:
                    if data:
                        for ev in data.get("_embedded", {}).get("events", []):
                            c = _parse_tm(ev, artist_name, str(user.id))
                            if c:
                                all_concerts.append(c)

        yield _sse({"step": f"Found {len(all_concerts)} results — deduplicating…", "progress": 87})

        seen = {}
        unique = []
        for c in all_concerts:
            key = (c["artist_name"].lower(), c["venue_name"].lower(), c["date"])
            if key not in seen:
                seen[key] = True
                unique.append(c)

        # Score and sort by affinity
        for c in unique:
            c["affinity_score"] = _affinity_score(c["artist_name"], liked, disliked, top_scores)

        unique = [c for c in unique if c["affinity_score"] >= 0]  # drop disliked artists
        unique.sort(key=lambda c: (-c["affinity_score"], c["date"]))

        yield _sse({"step": f"Saving {len(unique)} concerts to your library…", "progress": 93})

        if unique:
            supabase.table("concerts_discovered").delete().eq("user_id", str(user.id)).execute()
            for concert in unique:
                supabase.table("concerts_discovered").upsert(concert, on_conflict="event_id").execute()

        yield _sse({"step": f"Done! Found {len(unique)} concerts.", "progress": 100, "done": True, "count": len(unique)})

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("")
def get_concerts(
    user=Depends(get_current_user),
    supabase: Client = Depends(get_supabase),
):
    today = date.today().isoformat()
    concerts = (
        supabase.table("concerts_discovered")
        .select("*")
        .eq("user_id", str(user.id))
        .gte("date", today)
        .execute()
        .data or []
    )

    # Live preferences adjustment — swipes made after last discover are applied here
    pref_rows = (
        supabase.table("preferences")
        .select("artist_name,preference")
        .eq("user_id", str(user.id))
        .execute()
        .data or []
    )
    liked = {p["artist_name"].lower() for p in pref_rows if p["preference"] == "liked"}
    disliked = {p["artist_name"].lower() for p in pref_rows if p["preference"] == "disliked"}

    def sort_key(c):
        name = (c.get("artist_name") or "").lower()
        base = c.get("affinity_score") or 0
        if name in disliked:
            return (2, 0, c.get("date", ""))   # push to bottom
        if name in liked:
            base = max(base, 100)              # ensure liked artists float up
        return (0, -base, c.get("date", ""))

    concerts = [c for c in concerts if (c.get("artist_name") or "").lower() not in disliked]
    concerts.sort(key=sort_key)
    return concerts
