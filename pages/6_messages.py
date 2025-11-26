import streamlit as st
from supabase import create_client, Client
from datetime import datetime
import time

st.set_page_config(page_title="Messages", page_icon="💬", layout="wide")

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
def get_friends(user_id):
    """Get accepted friends"""
    response1 = supabase.table("friendships").select("*").eq("user_id", user_id).eq("status", "accepted").execute()
    response2 = supabase.table("friendships").select("*").eq("friend_id", user_id).eq("status", "accepted").execute()
    
    friend_ids = []
    for f in response1.data:
        friend_ids.append(f['friend_id'])
    for f in response2.data:
        friend_ids.append(f['user_id'])
    
    if friend_ids:
        friends = supabase.table("profiles").select("*").in_("id", friend_ids).execute()
        return friends.data
    return []

def get_conversation(user1_id, user2_id, limit=50):
    """Get messages between two users"""
    messages = supabase.table("messages").select("*").or_(
        f"and(sender_id.eq.{user1_id},receiver_id.eq.{user2_id}),and(sender_id.eq.{user2_id},receiver_id.eq.{user1_id})"
    ).order("created_at", desc=False).limit(limit).execute()
    
    return messages.data

def send_message(sender_id, receiver_id, message_text):
    """Send a message"""
    try:
        result = supabase.table("messages").insert({
            "sender_id": sender_id,
            "receiver_id": receiver_id,
            "message": message_text,
            "read": False
        }).execute()
        
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

# Session state for selected friend
if 'selected_friend' not in st.session_state:
    st.session_state.selected_friend = None

# Layout: Sidebar for friend list, main area for chat
col_friends, col_chat = st.columns([1, 3])

# ==================== FRIEND LIST ====================
with col_friends:
    st.subheader("💬 Conversations")
    
    # Sort friends by last message time
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
    
    # Sort by most recent
    friends_with_last_msg.sort(key=lambda x: x['timestamp'], reverse=True)
    
    for item in friends_with_last_msg:
        friend = item['friend']
        last_msg = item['last_message']
        unread = item['unread']
        
        # Create clickable container
        button_label = f"**{friend['username']}**"
        if unread > 0:
            button_label += f" 🔴 ({unread})"
        
        if last_msg:
            preview = last_msg['message'][:30] + "..." if len(last_msg['message']) > 30 else last_msg['message']
            button_label += f"\n_{preview}_"
        
        if st.button(button_label, key=f"friend_{friend['id']}", use_container_width=True):
            st.session_state.selected_friend = friend
            mark_as_read(user.id, friend['id'])
            st.rerun()
        
        st.markdown("---")

# ==================== CHAT AREA ====================
with col_chat:
    if st.session_state.selected_friend:
        friend = st.session_state.selected_friend
        
        # Chat header
        col_header, col_back = st.columns([4, 1])
        
        with col_header:
            st.subheader(f"💬 Chat with {friend['username']}")
        
        with col_back:
            if st.button("← Back", key="back_btn"):
                st.session_state.selected_friend = None
                st.rerun()
        
        st.markdown("---")
        
        # Messages container
        messages_container = st.container()
        
        with messages_container:
            messages = get_conversation(user.id, friend['id'])
            
            if not messages:
                st.info(f"No messages yet. Say hi to {friend['username']}!")
            else:
                for msg in messages:
                    is_sent = msg['sender_id'] == user.id
                    
                    # Create message bubble
                    if is_sent:
                        # Right-aligned (sent by you)
                        st.markdown(f"""
                        <div style="text-align: right; margin: 10px 0;">
                            <div style="display: inline-block; background: #1DB954; color: white; padding: 10px 15px; border-radius: 15px; max-width: 70%; text-align: left;">
                                {msg['message']}
                            </div>
                            <div style="font-size: 0.8em; opacity: 0.6; margin-top: 2px;">
                                {datetime.fromisoformat(msg['created_at'].replace('Z', '+00:00')).strftime('%I:%M %p')}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        # Left-aligned (received)
                        st.markdown(f"""
                        <div style="text-align: left; margin: 10px 0;">
                            <div style="display: inline-block; background: #f0f0f0; color: black; padding: 10px 15px; border-radius: 15px; max-width: 70%; text-align: left;">
                                {msg['message']}
                            </div>
                            <div style="font-size: 0.8em; opacity: 0.6; margin-top: 2px;">
                                {datetime.fromisoformat(msg['created_at'].replace('Z', '+00:00')).strftime('%I:%M %p')}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Message input
        with st.form(key="message_form", clear_on_submit=True):
            col_input, col_send = st.columns([5, 1])
            
            with col_input:
                message_text = st.text_input("Type a message...", label_visibility="collapsed", placeholder=f"Message {friend['username']}...")
            
            with col_send:
                send_btn = st.form_submit_button("📤 Send", use_container_width=True)
            
            if send_btn and message_text.strip():
                result = send_message(user.id, friend['id'], message_text.strip())
                
                if result['success']:
                    st.rerun()
                else:
                    st.error("Failed to send message")
        
        # Auto-refresh button
        if st.button("🔄 Refresh", key="refresh_chat"):
            st.rerun()
        
    else:
        # No friend selected
        st.info("👈 Select a friend from the list to start chatting")
        
        # Show friend suggestions
        st.subheader("💡 Your Friends:")
        for friend in friends[:5]:
            st.write(f"• **{friend['username']}**")

# ==================== SIDEBAR ====================
with st.sidebar:
    st.markdown("### 📊 Message Stats")
    
    # Total unread
    total_unread = 0
    for friend in friends:
        total_unread += get_unread_count(user.id, friend['id'])
    
    st.metric("Unread Messages", total_unread)
    st.metric("Conversations", len(friends))
