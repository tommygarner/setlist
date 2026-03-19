from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from supabase import Client

from main import get_current_user, get_supabase

router = APIRouter()


class MessageBody(BaseModel):
    receiver_id: str
    message: str
    concert_data: Optional[dict] = None


@router.get("/{friend_id}")
def get_messages(friend_id: str, user=Depends(get_current_user), supabase: Client = Depends(get_supabase)):
    uid = str(user.id)
    result = (
        supabase.table("messages")
        .select("*")
        .or_(f"and(sender_id.eq.{uid},receiver_id.eq.{friend_id}),and(sender_id.eq.{friend_id},receiver_id.eq.{uid})")
        .order("created_at")
        .limit(100)
        .execute()
    )
    # Mark received as read
    supabase.table("messages").update({"read": True}).eq("sender_id", friend_id).eq("receiver_id", uid).eq("read", False).execute()
    return result.data or []


@router.post("")
def send_message(body: MessageBody, user=Depends(get_current_user), supabase: Client = Depends(get_supabase)):
    data = {
        "sender_id": str(user.id),
        "receiver_id": body.receiver_id,
        "message": body.message,
        "read": False,
    }
    if body.concert_data:
        data["concert_event_id"] = body.concert_data.get("event_id")
        data["concert_data"] = body.concert_data
    result = supabase.table("messages").insert(data).execute()
    return result.data[0] if result.data else {}
