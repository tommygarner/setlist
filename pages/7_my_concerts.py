import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="My Concerts", page_icon="🎟️", layout="wide")

# ==================== SUPABASE CONNECTION ====================
def init_supabase() -> Client:
    url = st.secrets["connections"]["supabase"]["SUPABASE_URL"]
    key = st.secrets["connections"]["supabase"]["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_supabase()

# Check authentication
if "authenticated" not in st.session_state or not st.session_state.authenticated:
    st.error("❌ Please login first!")
    if st.button("← Go to Main App", key="main_app_btn"):
        st.switch_page("app.py")
    st.stop()

user = st.session_state.user

# ==================== HELPER FUNCTIONS ====================
def get_concert_attendance_status(user_id, event_id):
    """Get user's attendance status for a concert"""
    result = supabase.table("concert_attendance").select("*").eq("user_id", user_id).eq("event_id", event_id).execute()
    if result.data:
        return result.data[0]['status']
    return None

def update_concert_status(user_id, event_id, status):
    """Update or create concert attendance status"""
    try:
        supabase.table("concert_attendance").upsert({
            "user_id": user_id,
            "event_id": event_id,
            "status": status,
            "updated_at": datetime.now().isoformat()
        }, on_conflict='user_id,event_id').execute()
        return True
    except:
        return False

def get_friends():
    """Get user's friends for sharing"""
    response1 = supabase.table("friendships").select("*").eq("user_id", user.id).eq("status", "accepted").execute()
    response2 = supabase.table("friendships").select("*").eq("friend_id", user.id).eq("status", "accepted").execute()
    
    friend_ids = []
    for f in response1.data:
        friend_ids.append(f['friend_id'])
    for f in response2.data:
        friend_ids.append(f['user_id'])
    
    if friend_ids:
        friends = supabase.table("profiles").select("*").in_("id", friend_ids).execute()
        return friends.data
    return []

def send_concert_to_friend(friend_id, concert_data):
    """Send concert to a friend via DM"""
    message_text = f"Hey! Let's go to this concert together! 🎵"
    
    try:
        supabase.table("messages").insert({
            "sender_id": user.id,
            "receiver_id": friend_id,
            "message": message_text,
            "concert_event_id": concert_data['event_id'],
            "concert_data": concert_data,
            "read": False
        }).execute()
        return True
    except:
        return False

# ==================== MAIN UI ====================
st.title("🎟️ My Concerts")
st.markdown("Your concert watchlist and upcoming shows")

# Tabs
tab1, tab2, tab3 = st.tabs(["📋 All Concerts", "✅ Going", "⭐ Interested"])

# Load all concerts
all_concerts = supabase.table("concerts_discovered").select("*").eq("user_id", user.id).order("date").execute()
concerts_df = pd.DataFrame(all_concerts.data) if all_concerts.data else pd.DataFrame()

if concerts_df.empty:
    st.info("🎵 No concerts saved yet! Go to Discover Concerts to find shows.")
    if st.button("🔍 Discover Concerts"):
        st.switch_page("pages/2_discover_concerts.py")
    st.stop()

# Get attendance statuses
going_concerts = []
interested_concerts = []

for _, concert in concerts_df.iterrows():
    status = get_concert_attendance_status(user.id, concert['event_id'])
    if status == 'going':
        going_concerts.append(concert)
    elif status == 'interested':
        interested_concerts.append(concert)

# ==================== TAB 1: ALL CONCERTS ====================
with tab1:
    st.subheader(f"📋 All Saved Concerts ({len(concerts_df)})")
    
    # Filters
    col_f1, col_f2, col_f3 = st.columns(3)
    
    with col_f1:
        filter_date = st.selectbox("Date Range", ["All", "Upcoming", "This Month", "This Year"])
    
    with col_f2:
        artists = sorted(concerts_df['artist_name'].unique())
        filter_artist = st.selectbox("Artist", ["All Artists"] + artists)
    
    with col_f3:
        venues = sorted(concerts_df['venue_name'].unique())
        filter_venue = st.selectbox("Venue", ["All Venues"] + venues)
    
    # Apply filters
    filtered_df = concerts_df.copy()
    
    if filter_date != "All":
        today = datetime.now()
        if filter_date == "Upcoming":
            filtered_df = filtered_df[filtered_df['date'] >= today.strftime("%Y-%m-%d")]
        elif filter_date == "This Month":
            filtered_df = filtered_df[filtered_df['date'].str.startswith(today.strftime("%Y-%m"))]
        elif filter_date == "This Year":
            filtered_df = filtered_df[filtered_df['date'].str.startswith(str(today.year))]
    
    if filter_artist != "All Artists":
        filtered_df = filtered_df[filtered_df['artist_name'] == filter_artist]
    
    if filter_venue != "All Venues":
        filtered_df = filtered_df[filtered_df['venue_name'] == filter_venue]
    
    st.info(f"Showing {len(filtered_df)} of {len(concerts_df)} concerts")
    
    # Display concerts
    for _, concert in filtered_df.iterrows():
        current_status = get_concert_attendance_status(user.id, concert['event_id'])
        
        with st.container():
            col1, col2, col3 = st.columns([3, 2, 2])
            
            with col1:
                st.markdown(f"### {concert['event_name']}")
                st.write(f"🎤 **{concert['artist_name']}**")
                st.write(f"📍 {concert['venue_name']}, {concert['city']}, {concert['state']}")
                source_emoji = "🎟️" if concert.get('source') == 'ticketmaster' else "💺"
                st.caption(f"{source_emoji} {concert.get('source', 'ticketmaster').title()}")
            
            with col2:
                st.write(f"📅 **Date:** {concert['date']}")
                if concert.get('time'):
                    st.write(f"🕐 **Time:** {concert['time']}")
                
                # Status badge
                if current_status:
                    status_emoji = {"going": "✅", "interested": "⭐", "maybe": "🤔"}
                    st.success(f"{status_emoji.get(current_status, '')} {current_status.title()}")
            
            with col3:
                # Status buttons
                col_going, col_interested = st.columns(2)
                
                with col_going:
                    going_type = "primary" if current_status == "going" else "secondary"
                    if st.button("✅ Going", key=f"going_{concert['event_id']}", use_container_width=True, type=going_type):
                        new_status = None if current_status == "going" else "going"
                        if new_status:
                            update_concert_status(user.id, concert['event_id'], "going")
                        else:
                            supabase.table("concert_attendance").delete().eq("user_id", user.id).eq("event_id", concert['event_id']).execute()
                        st.rerun()
                
                with col_interested:
                    interested_type = "primary" if current_status == "interested" else "secondary"
                    if st.button("⭐ Interested", key=f"int_{concert['event_id']}", use_container_width=True, type=interested_type):
                        new_status = None if current_status == "interested" else "interested"
                        if new_status:
                            update_concert_status(user.id, concert['event_id'], "interested")
                        else:
                            supabase.table("concert_attendance").delete().eq("user_id", user.id).eq("event_id", concert['event_id']).execute()
                        st.rerun()
                
                # Tickets and Share
                col_tickets, col_share = st.columns(2)
                
                with col_tickets:
                    url = concert.get('url') or concert.get('ticket_url')
                    if url:
                        st.link_button("🎟️ Tickets", url, use_container_width=True)
                
                with col_share:
                    if st.button("📤 Share", key=f"share_{concert['event_id']}", use_container_width=True):
                        st.session_state[f'sharing_{concert["event_id"]}'] = True
                        st.rerun()
                
                # Share menu (if open)
                if st.session_state.get(f'sharing_{concert["event_id"]}', False):
                    friends = get_friends()
                    
                    if friends:
                        st.markdown("**Send to:**")
                        for friend in friends:
                            if st.button(f"💬 {friend['username']}", key=f"send_{concert['event_id']}_{friend['id']}", use_container_width=True):
                                success = send_concert_to_friend(friend['id'], concert.to_dict())
                                if success:
                                    st.success(f"Sent to {friend['username']}!")
                                    st.session_state[f'sharing_{concert["event_id"]}'] = False
                                    st.rerun()
                    else:
                        st.caption("Add friends to share concerts")
            
            st.markdown("---")

# ==================== TAB 2: GOING ====================
with tab2:
    st.subheader(f"✅ Concerts I'm Going To ({len(going_concerts)})")
    
    if going_concerts:
        for concert in going_concerts:
            with st.container():
                col1, col2 = st.columns([4, 1])
                
                with col1:
                    st.markdown(f"### {concert['artist_name']}")
                    st.write(f"📍 {concert['venue_name']}")
                    st.write(f"📅 {concert['date']}")
                
                with col2:
                    url = concert.get('url') or concert.get('ticket_url')
                    if url:
                        st.link_button("🎟️ Tickets", url, use_container_width=True)
                
                st.markdown("---")
    else:
        st.info("No concerts marked as 'Going' yet. Mark concerts in the All Concerts tab!")

# ==================== TAB 3: INTERESTED ====================
with tab3:
    st.subheader(f"⭐ Concerts I'm Interested In ({len(interested_concerts)})")
    
    if interested_concerts:
        for concert in interested_concerts:
            with st.container():
                col1, col2 = st.columns([4, 1])
                
                with col1:
                    st.markdown(f"### {concert['artist_name']}")
                    st.write(f"📍 {concert['venue_name']}")
                    st.write(f"📅 {concert['date']}")
                
                with col2:
                    url = concert.get('url') or concert.get('ticket_url')
                    if url:
                        st.link_button("🎟️ Tickets", url, use_container_width=True)
                
                st.markdown("---")
    else:
        st.info("No concerts marked as 'Interested' yet. Mark concerts in the All Concerts tab!")

# ==================== SIDEBAR ====================
with st.sidebar:
    st.markdown("### 🎟️ Concert Stats")
    
    st.metric("Total Saved", len(concerts_df))
    st.metric("Going", len(going_concerts))
    st.metric("Interested", len(interested_concerts))
    
    upcoming = concerts_df[concerts_df['date'] >= datetime.now().strftime("%Y-%m-%d")]
    st.metric("Upcoming", len(upcoming))
