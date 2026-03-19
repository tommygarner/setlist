import streamlit as st
from supabase import create_client, Client


def init_supabase() -> Client:
    url = st.secrets["connections"]["supabase"]["SUPABASE_URL"]
    key = st.secrets["connections"]["supabase"]["SUPABASE_KEY"]
    return create_client(url, key)


def require_auth():
    """Return the current user, or stop the page if not authenticated."""
    if "authenticated" not in st.session_state or not st.session_state.authenticated:
        st.error("❌ Please login first!")
        if st.button("← Go to Main App", key="main_app_btn"):
            st.switch_page("app.py")
        st.stop()
    return st.session_state.user


def get_friends(supabase: Client, user_id: str) -> list:
    """Get accepted friends for a user."""
    response1 = supabase.table("friendships").select("*").eq("user_id", user_id).eq("status", "accepted").execute()
    response2 = supabase.table("friendships").select("*").eq("friend_id", user_id).eq("status", "accepted").execute()

    friend_ids = [f["friend_id"] for f in response1.data] + [f["user_id"] for f in response2.data]

    if friend_ids:
        return supabase.table("profiles").select("*").in_("id", friend_ids).execute().data
    return []
