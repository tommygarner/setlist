import streamlit as st
from datetime import datetime
import json
from utils.supabase_client import init_supabase, require_auth, get_friends as _get_friends

st.set_page_config(page_title="Messages", page_icon="💬", layout="wide")

supabase = init_supabase()
user = require_auth()


def get_friends(user_id):
    return _get_friends(supabase, user_id)

def get_conversation(user1_id, user2_id, limit=50):
    """Get messages between two users"""
    messages = supabase.table("messages").select("*").or_(
        f"and(sender_id.eq.{user1_id},receiver_id.eq.{user2_id}),and(sender_id.eq.{user2_id},receiver_id.eq.{user1_id})"
    ).order("created_at", desc=False).limit(limit).execute()
    
    return messages.data

def send_message(sender_id, receiver_id, message_text, concert_data=None):
    """Send a message with optional concert attachment"""
    try:
        data = {
            "sender_id": sender_id,
            "receiver_id": receiver_id,
            "message": message_text,
            "read": False
        }
        
        if concert_data:
            data["concert_event_id"] = concert_data.get('event_id')
            data["concert_data"] = concert_data
        
        result = supabase.table("messages").insert(data).execute()
        
        return {'success': True, 'data': result.data}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def mark_as_read(user_id, friend_id):
    """Mark all messages from friend as read"""
    try:
        supabase.table("messages").update({"read": True}).eq("sender_id", friend_id).eq("receiver_id", user_id).eq("read", False).execute()
    except:
        pass

def get_unread_count(user_id, friend_id):
    """Get unread message count from a specific friend"""
    result = supabase.table("messages").select("id").eq("sender_id", friend_id).eq("receiver_id", user_id).eq("read", False).execute()
    return len(result.data)

def get_last_message(user1_id, user2_id):
    """Get the last message between two users"""
    result = supabase.table("messages").select("*").or_(
        f"and(sender_id.eq.{user1_id},receiver_id.eq.{user2_id}),and(sender_id.eq.{user2_id},receiver_id.eq.{user1_id})"
    ).order("created_at", desc=True).limit(1).execute()
    
    if result.data:
        return result.data[0]
    return None

def get_user_concerts():
    """Get user's saved concerts"""
    result = supabase.table("concerts_discovered").select("*").eq("user_id", user.id).order("date").execute()
    return result.data

def display_concert_card(concert_data, in_chat=False):
    """Display concert card in message"""
    artist = concert_data.get('artist_name', 'Unknown Artist')
    event = concert_data.get('event_name', 'Concert')
    venue = concert_data.get('venue_name', 'Unknown Venue')
    city = concert_data.get('city', '')
    state = concert_data.get('state', '')
    date = concert_data.get('date', 'TBA')
    url = concert_data.get('url') or concert_data.get('ticket_url')
    
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, #1DB95422 0%, #1DB95444 100%);
        border-left: 4px solid #1DB954;
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
    ">
        <h4 style="margin: 0; color: #1DB954;">🎤 {artist}</h4>
        <p style="margin: 5px 0; font-weight: bold;">{event}</p>
        <p style="margin: 5px 0; font-size: 0.9em;">📍 {venue}, {city}, {state}</p>
        <p style="margin: 5px 0; font-size: 0.9em;">📅 {date}</p>
    </div>
    """, unsafe_allow_html=True)
    
    if url and in_chat:
        st.link_button("🎟️ Get Tickets", url, use_container_width=True)

# ==================== MAIN UI ====================
st.title("💬 Messages")
st.markdown("Chat with your concert buddies")

# Get friends
friends = get_friends(user.id)

if not friends:
    st.info("👥 You don't have any friends yet. Add friends to start chatting!")
    if st.button("🔍 Find Friends"):
        st.switch_page("pages/5_friends.py")
    st.stop()

# Session state
if 'selected_friend' not in st.session_state:
    st.session_state.selected_friend = None
if 'show_concert_picker' not in st.session_state:
    st.session_state.show_concert_picker = False

# Layout
col_friends, col_chat = st.columns([1, 3])

# ==================== FRIEND LIST ====================
with col_friends:
    st.subheader("💬 Chats")
    
    friends_with_last_msg = []
    for friend in friends:
        last_msg = get_last_message(user.id, friend['id'])
        unread = get_unread_count(user.id, friend['id'])
        
        friends_with_last_msg.append({
            'friend': friend,
            'last_message': last_msg,
            'unread': unread,
            'timestamp': last_msg['created_at'] if last_msg else '2000-01-01'
        })
    
    friends_with_last_msg.sort(key=lambda x: x['timestamp'], reverse=True)
    
    for item in friends_with_last_msg:
        friend = item['friend']
        last_msg = item['last_message']
        unread = item['unread']
        
        button_label = f"**{friend['username']}**"
        if unread > 0:
            button_label += f" 🔴 ({unread})"
        
        if last_msg:
            if last_msg.get('concert_event_id'):
                preview = "🎟️ Shared a concert"
            else:
                preview = last_msg['message'][:30] + "..." if len(last_msg['message']) > 30 else last_msg['message']
            button_label += f"\n_{preview}_"
        
        if st.button(button_label, key=f"friend_{friend['id']}", use_container_width=True):
            st.session_state.selected_friend = friend
            st.session_state.show_concert_picker = False
            mark_as_read(user.id, friend['id'])
            st.rerun()
        
        st.markdown("---")

# ==================== CHAT AREA ====================
with col_chat:
    if st.session_state.selected_friend:
        friend = st.session_state.selected_friend
        
        # Chat header
        col_h1, col_h2, col_h3 = st.columns([3, 1, 1])
        
        with col_h1:
            st.subheader(f"💬 {friend['username']}")
        
        with col_h2:
            if st.button("🎟️ Share Concert", key="share_concert_btn", use_container_width=True):
                st.session_state.show_concert_picker = not st.session_state.show_concert_picker
                st.rerun()
        
        with col_h3:
            if st.button("← Back", key="back_btn", use_container_width=True):
                st.session_state.selected_friend = None
                st.session_state.show_concert_picker = False
                st.rerun()
        
        # Concert picker (if enabled)
        if st.session_state.show_concert_picker:
            st.markdown("---")
            st.markdown("### 🎟️ Share a Concert")
            
            user_concerts = get_user_concerts()
            
            if user_concerts:
                # Organize concerts by status
                going_concerts = []
                interested_concerts = []
                other_concerts = []
                
                for concert in user_concerts:
                    # Check status
                    status_check = supabase.table("concert_attendance").select("status").eq("user_id", user.id).eq("event_id", concert['event_id']).execute()
                    
                    if status_check.data:
                        status = status_check.data[0]['status']
                        if status == 'going':
                            going_concerts.append(concert)
                        elif status == 'interested':
                            interested_concerts.append(concert)
                        else:
                            other_concerts.append(concert)
                    else:
                        other_concerts.append(concert)
                
                # Build organized dropdown options
                concert_options = {}
                
                # Add Going concerts first
                if going_concerts:
                    for concert in going_concerts[:10]:
                        label = f"✅ Going: {concert['artist_name']} - {concert['venue_name']} ({concert['date']})"
                        concert_options[label] = concert
                
                # Add Interested concerts
                if interested_concerts:
                    for concert in interested_concerts[:10]:
                        label = f"⭐ Interested: {concert['artist_name']} - {concert['venue_name']} ({concert['date']})"
                        concert_options[label] = concert
                
                # Add other concerts
                if other_concerts:
                    for concert in other_concerts[:15]:
                        label = f"📋 {concert['artist_name']} - {concert['venue_name']} ({concert['date']})"
                        concert_options[label] = concert
                
                # Concert selector dropdown
                selected_label = st.selectbox(
                    "Choose a concert:", 
                    list(concert_options.keys()),
                    help="✅ = Going, ⭐ = Interested, 📋 = Saved"
                )
                
                col_preview, col_send_concert = st.columns([3, 1])
                
                with col_preview:
                    if selected_label:
                        selected_concert = concert_options[selected_label]
                        display_concert_card(selected_concert, in_chat=False)
                
                with col_send_concert:
                    st.write("")
                    st.write("")
                    if st.button("📤 Send Concert", key="send_concert_btn", use_container_width=True, type="primary"):
                        message_text = f"Hey! Let's go to this concert together! 🎵"
                        result = send_message(user.id, friend['id'], message_text, concert_data=selected_concert)
                        
                        if result['success']:
                            st.session_state.show_concert_picker = False
                            st.success("Concert shared!")
                            st.rerun()
                        else:
                            st.error("Failed to share concert")
                
                # Quick link to My Concerts
                st.caption("💡 Tip: Mark concerts as Going/Interested in [My Concerts](/my_concerts) for easy sharing")
                
            else:
                st.info("You haven't saved any concerts yet. Go to Discover Concerts first!")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("🔍 Discover Concerts", use_container_width=True):
                        st.switch_page("pages/2_discover_concerts.py")
                with col2:
                    if st.button("🎟️ My Concerts", use_container_width=True):
                        st.switch_page("pages/7_my_concerts.py")
        
        st.markdown("---")
        
        # Messages
        messages = get_conversation(user.id, friend['id'])
        
        if not messages:
            st.info(f"No messages yet. Say hi to {friend['username']}!")
        else:
            for msg in messages:
                is_sent = msg['sender_id'] == user.id
                timestamp = datetime.fromisoformat(msg['created_at'].replace('Z', '+00:00')).strftime('%I:%M %p')
                
                if is_sent:
                    # Sent message
                    with st.container():
                        col_space, col_msg = st.columns([1, 4])
                        with col_msg:
                            st.markdown(f"""
                            <div style="text-align: right;">
                                <div style="display: inline-block; background: #1DB954; color: white; padding: 10px 15px; border-radius: 15px; max-width: 100%; text-align: left;">
                                    {msg['message']}
                                </div>
                                <div style="font-size: 0.75em; opacity: 0.6; margin-top: 2px;">
                                    {timestamp}
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # Show concert card if attached
                            if msg.get('concert_data'):
                                display_concert_card(msg['concert_data'], in_chat=True)
                else:
                    # Received message
                    with st.container():
                        col_msg, col_space = st.columns([4, 1])
                        with col_msg:
                            st.markdown(f"""
                            <div style="text-align: left;">
                                <div style="display: inline-block; background: #f0f0f0; color: black; padding: 10px 15px; border-radius: 15px; max-width: 100%; text-align: left;">
                                    {msg['message']}
                                </div>
                                <div style="font-size: 0.75em; opacity: 0.6; margin-top: 2px;">
                                    {timestamp}
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # Show concert card if attached
                            if msg.get('concert_data'):
                                display_concert_card(msg['concert_data'], in_chat=True)
        
        st.markdown("---")
        
        # Message input
        with st.form(key="message_form", clear_on_submit=True):
            col_input, col_send = st.columns([5, 1])
            
            with col_input:
                message_text = st.text_input("Type a message...", label_visibility="collapsed", placeholder=f"Message {friend['username']}...")
            
            with col_send:
                send_btn = st.form_submit_button("📤", use_container_width=True)
            
            if send_btn and message_text.strip():
                result = send_message(user.id, friend['id'], message_text.strip())
                
                if result['success']:
                    st.rerun()
                else:
                    st.error("Failed to send")
        
        if st.button("🔄 Refresh", key="refresh_chat"):
            st.rerun()
        
    else:
        st.info("👈 Select a friend to start chatting")

# ==================== SIDEBAR ====================
with st.sidebar:
    st.markdown("### 📊 Stats")
    
    total_unread = sum(get_unread_count(user.id, f['id']) for f in friends)
    
    st.metric("Unread", total_unread)
    st.metric("Friends", len(friends))
