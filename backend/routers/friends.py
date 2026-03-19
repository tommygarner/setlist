from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from supabase import Client

from main import get_current_user, get_supabase

router = APIRouter()


class FriendRequest(BaseModel):
    friend_id: str


def _get_friends(supabase: Client, user_id: str):
    r1 = supabase.table("friendships").select("*").eq("user_id", user_id).eq("status", "accepted").execute()
    r2 = supabase.table("friendships").select("*").eq("friend_id", user_id).eq("status", "accepted").execute()
    ids = [f["friend_id"] for f in r1.data] + [f["user_id"] for f in r2.data]
    if not ids:
        return []
    return supabase.table("profiles").select("*").in_("id", ids).execute().data or []


@router.get("")
def get_friends(user=Depends(get_current_user), supabase: Client = Depends(get_supabase)):
    return _get_friends(supabase, str(user.id))


@router.get("/search")
def search_users(q: str = Query(...), user=Depends(get_current_user), supabase: Client = Depends(get_supabase)):
    by_username = supabase.table("profiles").select("*").ilike("username", f"%{q}%").execute()
    results = by_username.data or []
    if not results:
        by_email = supabase.table("profiles").select("*").ilike("email", f"%{q}%").execute()
        results = by_email.data or []
    return [r for r in results if r["id"] != str(user.id)]


@router.post("/request")
def send_friend_request(
    body: FriendRequest,
    user=Depends(get_current_user),
    supabase: Client = Depends(get_supabase),
):
    uid = str(user.id)
    fid = body.friend_id

    # Check for mutual pending request
    mutual = (
        supabase.table("friendships")
        .select("*")
        .eq("user_id", fid)
        .eq("friend_id", uid)
        .eq("status", "pending")
        .execute()
    )
    if mutual.data:
        supabase.table("friendships").update({"status": "accepted"}).eq("id", mutual.data[0]["id"]).execute()
        supabase.table("friendships").insert({"user_id": uid, "friend_id": fid, "status": "accepted"}).execute()
        return {"message": "You are now friends (mutual request accepted)"}

    supabase.table("friendships").insert({"user_id": uid, "friend_id": fid, "status": "pending"}).execute()
    return {"message": "Friend request sent"}
