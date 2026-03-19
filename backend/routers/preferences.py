from fastapi import APIRouter, Depends
from pydantic import BaseModel
from supabase import Client

from main import get_current_user, get_supabase

router = APIRouter()


class PreferenceBody(BaseModel):
    artist_name: str
    preference: str  # "liked" | "disliked"


@router.post("")
def save_preference(
    body: PreferenceBody,
    user=Depends(get_current_user),
    supabase: Client = Depends(get_supabase),
):
    supabase.table("preferences").upsert(
        {"user_id": str(user.id), "artist_name": body.artist_name, "preference": body.preference},
        on_conflict="user_id,artist_name",
    ).execute()
    return {"ok": True}


@router.get("")
def get_preferences(user=Depends(get_current_user), supabase: Client = Depends(get_supabase)):
    result = supabase.table("preferences").select("*").eq("user_id", str(user.id)).execute()
    return result.data or []
