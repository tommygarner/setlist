"""
Music discovery endpoints: personalized, this weekend, and surprise picks.
Calls SeatGeek and scores against user's liked artists.
"""
import os
import random
from datetime import datetime, timedelta

import requests
from fastapi import APIRouter, Depends
from supabase import Client

from main import get_current_user, get_supabase

router = APIRouter()

SEATGEEK_URL = "https://api.seatgeek.com/2/events"
HEADERS = {"Accept": "application/json", "User-Agent": "Mozilla/5.0"}


def _sg_request(params: dict):
    params["client_id"] = os.getenv("SEATGEEK_CLIENT_ID", "")
    params["venue.city"] = "Austin"
    params["venue.state"] = "TX"
    r = requests.get(SEATGEEK_URL, params=params, headers=HEADERS, timeout=12)
    if r.status_code == 200:
        return r.json().get("events", [])
    return []


def _liked_artists(supabase: Client, user_id: str):
    result = (
        supabase.table("preferences")
        .select("artist_name")
        .eq("user_id", user_id)
        .eq("preference", "liked")
        .execute()
    )
    return [p["artist_name"].lower() for p in (result.data or [])]


def _score(event: dict, liked_lower: list[str]) -> float:
    performers = [p["name"].lower() for p in event.get("performers", [])]
    score = 0.0
    for a in liked_lower:
        if a in performers:
            score += 100
            break
        for p in performers:
            if a in p or p in a:
                score += 50
                break
    score += event.get("score", 0) * 0.1
    return min(score, 100)


@router.get("/for-you")
def for_you(user=Depends(get_current_user), supabase: Client = Depends(get_supabase)):
    liked = _liked_artists(supabase, str(user.id))
    events = _sg_request({"taxonomies.name": "concert", "per_page": 25, "sort": "datetime_local.asc"})
    scored = [{"event": e, "score": _score(e, liked)} for e in events if _score(e, liked) > 0]
    scored.sort(key=lambda x: x["score"], reverse=True)
    return {"events": scored[:20]}


@router.get("/this-weekend")
def this_weekend(user=Depends(get_current_user)):
    today = datetime.now()
    days = (4 - today.weekday()) % 7
    friday = today + timedelta(days=days)
    sunday = friday + timedelta(days=2)
    events = _sg_request({
        "taxonomies.name": "concert",
        "datetime_local.gte": friday.strftime("%Y-%m-%d"),
        "datetime_local.lte": sunday.strftime("%Y-%m-%d"),
        "per_page": 20,
    })
    return {"events": events}


@router.get("/surprise")
def surprise(user=Depends(get_current_user)):
    events = _sg_request({"taxonomies.name": "concert", "per_page": 15, "sort": "score.desc"})
    if not events:
        return {"events": []}
    return {"events": [random.choice(events)]}
