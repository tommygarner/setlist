"""
Concert discovery and retrieval.
Ports the async Ticketmaster + SeatGeek fan-out from 2_discover_concerts.py.
"""
import asyncio
import os
from typing import Optional

import aiohttp
from fastapi import APIRouter, Depends, Query
from supabase import Client

from main import get_current_user, get_supabase

router = APIRouter()

HEADERS = {
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0",
}


async def _search_ticketmaster(session, artist, api_key, city, state, radius):
    params = {
        "apikey": api_key,
        "keyword": artist,
        "city": city,
        "stateCode": state,
        "radius": radius,
        "unit": "miles",
        "classificationName": "music",
        "sort": "date,asc",
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
    params = {
        "client_id": client_id,
        "q": artist,
        "venue.city": city,
        "venue.state": state,
        "range": f"{radius}mi",
        "type": "concert",
        "per_page": 25,
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


@router.post("/discover")
async def discover_concerts(
    city: str = Query("Austin"),
    state: str = Query("TX"),
    radius: int = Query(100),
    user=Depends(get_current_user),
    supabase: Client = Depends(get_supabase),
):
    # Get artists from user's liked songs via stored Spotify token
    profile = supabase.table("profiles").select("*").eq("id", user.id).single().execute()
    access_token = profile.data.get("spotify_access_token") if profile.data else None

    if not access_token:
        return {"error": "Spotify not connected", "concerts": []}

    # Fetch liked songs artists via Spotify
    import requests as req
    artists = set()
    offset = 0
    while True:
        r = req.get(
            "https://api.spotify.com/v1/me/tracks",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"limit": 50, "offset": offset},
        )
        if r.status_code != 200:
            break
        items = r.json().get("items", [])
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

    artists = list(artists)
    tm_key = os.getenv("TICKETMASTER_API_KEY", "")
    sg_id = os.getenv("SEATGEEK_CLIENT_ID", "")
    all_concerts = []

    async with aiohttp.ClientSession() as session:
        for i in range(0, len(artists), 20):
            batch = artists[i : i + 20]
            tasks = (
                [_search_ticketmaster(session, a, tm_key, city, state, radius) for a in batch]
                + [_search_seatgeek(session, a, sg_id, city, state, radius) for a in batch]
            )
            results = await asyncio.gather(*tasks)
            tm_results, sg_results = results[: len(batch)], results[len(batch) :]

            for artist_name, data in tm_results:
                if data:
                    for ev in data.get("_embedded", {}).get("events", []):
                        c = _parse_tm(ev, artist_name, str(user.id))
                        if c:
                            all_concerts.append(c)

            for _, data in sg_results:
                if data:
                    for ev in data.get("events", []):
                        c = _parse_sg(ev, str(user.id))
                        if c:
                            all_concerts.append(c)

    # Deduplicate by (artist, venue, date)
    seen = {}
    unique = []
    for c in all_concerts:
        key = (c["artist_name"].lower(), c["venue_name"].lower(), c["date"])
        if key not in seen:
            seen[key] = True
            unique.append(c)

    # Upsert to database
    if unique:
        supabase.table("concerts_discovered").delete().eq("user_id", str(user.id)).execute()
        for concert in unique:
            supabase.table("concerts_discovered").upsert(concert, on_conflict="event_id").execute()

    return {"concerts": unique, "count": len(unique)}


@router.get("")
def get_concerts(
    user=Depends(get_current_user),
    supabase: Client = Depends(get_supabase),
):
    result = (
        supabase.table("concerts_discovered")
        .select("*")
        .eq("user_id", str(user.id))
        .order("date")
        .execute()
    )
    return result.data or []
