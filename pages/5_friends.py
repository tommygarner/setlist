import streamlit as st
from supabase import create_client, Client
import pandas as pd

st.set_page_config(page_title="Friends", page_icon="👥", layout="wide")

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

# Get current user's profile
current_user_profile = supabase.table("profiles").select("*").eq("id", user.id).execute()
current_username = current_user_profile.data[0]['username'] if current_user_profile.data else user.email

# ==================== HELPER FUNCTIONS ====================
def search_user(search_term):
    """Search for user by username OR email"""
    # Try username first
    response = supabase.table("profiles").select("*").ilike("username", f"%{search_term}%").execute()
    
    if not response.data:
        # Try email
        response = supabase.table("profiles").select("*").ilike("email", f"%{search_term}%").execute()
    
    return response.data

def send_friend_request(user_id, friend_id):
    """Send friend request or auto-accept if mutual"""
    try:
        # Validate inputs
        if not user_id or not friend_id:
            return {'success': False, 'message': 'Invalid user IDs'}
        
        if user_id == friend_id:
            return {'success': False, 'message': 'Cannot friend yourself'}
        
        # Check if the OTHER person already sent you a request
        existing_request = supabase.table("friendships").select("*").eq("user_id", friend_id).eq("friend_id", user_id).eq("status", "pending").execute()
        
        if existing_request.data:
            # They already requested you! Auto-accept both ways
            request_id = existing_request.data[0]['id']
            
            # Accept their request
            supabase.table("friendships").update({"status": "accepted"}).eq("id", request_id).execute()
            
            # Create your accepted friendship
            supabase.table("friendships").insert({
                "user_id": user_id,
                "friend_id": friend_id,
                "status": "accepted"
            }).execute()
            
            return {'success': True, 'message': '✅ You are now friends! (Mutual request accepted)', 'type': 'mutual'}
        
        # Check if friendship already exists
        existing = supabase.table("friendships").select("*").or_(
            f"and(user_id.eq.{user_id},friend_id.eq.{friend_id}),and(user_id.eq.{friend_id},friend_id.eq.{user_id})"
        ).execute()
        
        if existing.data:
            status = existing.data[0]['status']
            if status == 'accepted':
                return {'success': False, 'message': 'You are already friends', 'type': 'duplicate'}
            else:
                return {'success': False, 'message': 'Friend request already sent', 'type': 'duplicate'}
        
        # Create new friend request
        insert_result = supabase.table("friendships").insert({
            "user_id": str(user_id),
            "friend_id": str(friend_id),
            "status": "pending"
        }).execute()
        
        # Check if insert succeeded
        if insert_result.data:
            return {'success': True, 'message': '✨ Friend request sent! They can accept in their Requests tab.', 'type': 'sent', 'data': insert_result.data}
        else:
            return {'success': False, 'message': 'Failed to send request - no data returned', 'type': 'error'}
        
    except Exception as e:
        return {'success': False, 'message': f'Error: {str(e)}', 'type': 'exception'}


def get_friends(user_id):
    """Get accepted friends"""
    # Get friendships where user is the requester
    response1 = supabase.table("friendships").select("*").eq("user_id", user_id).eq("status", "accepted").execute()
    
    # Get friendships where user is the friend
    response2 = supabase.table("friendships").select("*").eq("friend_id", user_id).eq("status", "accepted").execute()
    
    friend_ids = []
    for f in response1.data:
        friend_ids.append(f['friend_id'])
    for f in response2.data:
        friend_ids.append(f['user_id'])
    
    # Get friend profiles
    if friend_ids:
        friends = supabase.table("profiles").select("*").in_("id", friend_ids).execute()
        return friends.data
    return []

def get_pending_requests(user_id):
    """Get pending friend requests received"""
    response = supabase.table("friendships").select("*").eq("friend_id", user_id).eq("status", "pending").execute()
    
    # Get requester profiles
    requests_with_profiles = []
    for req in response.data:
        profile = supabase.table("profiles").select("*").eq("id", req['user_id']).execute()
        if profile.data:
            requests_with_profiles.append({
                'id': req['id'],
                'requester': profile.data[0]
            })
    
    return requests_with_profiles

def calculate_compatibility(user1_id, user2_id):
    """Calculate music compatibility between two users (Spotify Blend style)"""
    # Get both users' liked artists
    user1_likes = supabase.table("preferences").select("artist_name").eq("user_id", user1_id).eq("preference", "liked").execute()
    user2_likes = supabase.table("preferences").select("artist_name").eq("user_id", user2_id).eq("preference", "liked").execute()
    
    user1_artists = set([p['artist_name'].lower().strip() for p in user1_likes.data if p.get('artist_name')])
    user2_artists = set([p['artist_name'].lower().strip() for p in user2_likes.data if p.get('artist_name')])
    
    if not user1_artists and not user2_artists:
        return 0, [], [], []
    
    if not user1_artists or not user2_artists:
        return 5, [], list(user1_artists or user2_artists), []
    
    # Calculate similarity
    shared = user1_artists.intersection(user2_artists)
    user1_only = user1_artists - user2_artists
    user2_only = user2_artists - user1_artists
    total = user1_artists.union(user2_artists)
    
    # Jaccard similarity
    compatibility = (len(shared) / len(total)) * 100 if total else 0
    
    return compatibility, list(shared), list(user1_only), list(user2_only)

def display_compatibility_card(friend_name, compatibility, shared_artists):
    """Display a Spotify Blend-style compatibility card"""
    with st.container():
        # Gradient background based on compatibility
        if compatibility >= 75:
            color = "#1DB954"  # Green
            emoji = "🔥"
            vibe = "Perfect Match!"
        elif compatibility >= 50:
            color = "#FFA500"  # Orange
            emoji = "✨"
            vibe = "Great Taste"
        elif compatibility >= 25:
            color = "#4169E1"  # Blue
            emoji = "🎵"
            vibe = "Similar Vibes"
        else:
            color = "#9B59B6"  # Purple
            emoji = "🎧"
            vibe = "Unique Tastes"
        
        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, {color}22 0%, {color}44 100%);
            border-left: 4px solid {color};
            padding: 20px;
            border-radius: 10px;
            margin: 10px 0;
        ">
            <h3 style="margin:0; color: {color};">{emoji} {friend_name}</h3>
            <h1 style="margin:10px 0; font-size: 3em;">{int(compatibility)}%</h1>
            <p style="margin:0; opacity: 0.8;">{vibe}</p>
        </div>
        """, unsafe_allow_html=True)
        
        if shared_artists:
            with st.expander(f"🎤 {len(shared_artists)} Shared Artists"):
                cols = st.columns(3)
                for i, artist in enumerate(sorted(shared_artists)[:15]):
                    with cols[i % 3]:
                        st.write(f"• {artist.title()}")

# ==================== MAIN UI ====================
st.title("👥 Friends")
st.markdown("Connect with friends and discover concerts together")

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["🔍 Find Friends", "👥 My Friends", "📬 Requests", "🎵 Blend"])

# ==================== TAB 1: FIND FRIENDS ====================
with tab1:
    st.subheader("🔍 Find Friends")
    st.caption("Search by username or email")
    
    # Initialize session state for search results
    if 'search_results' not in st.session_state:
        st.session_state.search_results = []
    if 'last_search' not in st.session_state:
        st.session_state.last_search = ""
    
    search_term = st.text_input("Search:", placeholder="e.g. johndoe or john@example.com", value=st.session_state.last_search)
    
    col_search, col_clear = st.columns([3, 1])
    
    with col_search:
        if st.button("🔍 Search", type="primary", use_container_width=True):
            if search_term:
                if search_term.lower() == current_username.lower() or search_term.lower() == user.email.lower():
                    st.warning("That's you! 😄")
                    st.session_state.search_results = []
                else:
                    found_users = search_user(search_term)
                    st.session_state.search_results = found_users
                    st.session_state.last_search = search_term
            else:
                st.warning("Please enter a username or email")
    
    with col_clear:
        if st.button("🗑️ Clear", use_container_width=True):
            st.session_state.search_results = []
            st.session_state.last_search = ""
            st.rerun()
    
    # Display search results from session state
    if st.session_state.search_results:
        st.success(f"Found {len(st.session_state.search_results)} user(s)")
        
        for found_user in st.session_state.search_results[:5]:
            # Check current relationship status
            existing = supabase.table("friendships").select("*").or_(
                f"and(user_id.eq.{user.id},friend_id.eq.{found_user['id']}),and(user_id.eq.{found_user['id']},friend_id.eq.{user.id})"
            ).execute()
            
            # Determine relationship
            relationship = "none"
            if existing.data:
                for rel in existing.data:
                    if rel['status'] == 'accepted':
                        relationship = "friends"
                        break
                    elif rel['user_id'] == user.id:
                        relationship = "requested"
                    else:
                        relationship = "pending"
            
            with st.container():
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.markdown(f"### {found_user['username']}")
                    st.caption(f"📧 {found_user['email']}")
                    
                    # Calculate compatibility
                    compat, shared, _, _ = calculate_compatibility(user.id, found_user['id'])
                    
                    if compat > 0:
                        st.progress(compat / 100)
                        st.caption(f"🎵 {int(compat)}% music match • {len(shared)} shared artists")
                
                with col2:
                    # Dynamic button based on relationship
                    if relationship == "friends":
                        st.button("✅ Friends", key=f"btn_{found_user['id']}", disabled=True, use_container_width=True)
                    
                    elif relationship == "requested":
                        st.button("⏳ Requested", key=f"btn_{found_user['id']}", disabled=True, use_container_width=True)
                    
                    elif relationship == "pending":
                        if st.button("📬 View Request", key=f"btn_{found_user['id']}", use_container_width=True):
                            st.info("Go to the 'Requests' tab to accept!")
                    
                    else:
                        # Show Add Friend button
                        if st.button("➕ Add Friend", key=f"btn_{found_user['id']}", use_container_width=True, type="primary"):
                            with st.spinner("Sending friend request..."):
                                result = send_friend_request(user.id, found_user['id'])
                                
                                # Show result with debug
                                st.write("**Result:**")
                                st.json(result)
                                
                                if result['success']:
                                    st.success(result['message'])
                                    st.balloons()
                                    
                                    # Wait a moment then refresh
                                    import time
                                    time.sleep(1.5)
                                    st.rerun()
                                else:
                                    st.error(f"Error: {result['message']}")
                
                st.markdown("---")
    
    elif st.session_state.last_search:
        st.info("No users found. Try a different search term.")


# ==================== TAB 2: MY FRIENDS ====================
with tab2:
    st.subheader("👥 My Friends")
    
    friends = get_friends(user.id)
    
    if friends:
        st.success(f"You have {len(friends)} friend(s)")
        
        for friend in friends:
            compat, shared, _, _ = calculate_compatibility(user.id, friend['id'])
            
            with st.container():
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.markdown(f"### {friend['username']}")
                    st.progress(compat / 100)
                    st.caption(f"🎵 {int(compat)}% compatible • {len(shared)} shared artists")
                
                with col2:
                    if st.button("View Blend", key=f"blend_{friend['id']}", use_container_width=True):
                        st.session_state['blend_friend'] = friend
                        st.rerun()
                
                st.markdown("---")
    else:
        st.info("No friends yet. Search for users in the 'Find Friends' tab!")

# ==================== TAB 3: REQUESTS ====================
with tab3:
    st.subheader("📬 Friend Requests")
    
    pending = get_pending_requests(user.id)
    
    # Add auto-accept mutual requests button
    if pending:
        if st.button("✨ Auto-Accept Mutual Requests", type="primary"):
            accepted_count = 0
            for request in pending:
                requester = request['requester']
                
                # Check if you also sent them a request
                mutual = supabase.table("friendships").select("*").eq("user_id", user.id).eq("friend_id", requester['id']).eq("status", "pending").execute()
                
                if mutual.data:
                    # Accept their request
                    supabase.table("friendships").update({"status": "accepted"}).eq("id", request['id']).execute()
                    # Accept your request
                    supabase.table("friendships").update({"status": "accepted"}).eq("id", mutual.data[0]['id']).execute()
                    accepted_count += 1
            
            if accepted_count > 0:
                st.success(f"✅ Accepted {accepted_count} mutual request(s)!")
                st.rerun()
            else:
                st.info("No mutual requests found")
    
    if pending:
        st.info(f"You have {len(pending)} pending request(s)")
        
        for request in pending:
            requester = request['requester']
            compat, shared, _, _ = calculate_compatibility(user.id, requester['id'])
            
            with st.container():
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.markdown(f"### {requester['username']}")
                    st.caption(f"🎵 {int(compat)}% music compatibility")
                    if shared:
                        st.caption(f"You both like: {', '.join(list(shared)[:3])}")
                
                with col2:
                    col_a, col_b = st.columns(2)
                    
                    with col_a:
                        if st.button("✅", key=f"accept_{request['id']}", help="Accept"):
                            # Accept request
                            supabase.table("friendships").update({"status": "accepted"}).eq("id", request['id']).execute()
                            st.success("Friend added!")
                            st.rerun()
                    
                    with col_b:
                        if st.button("❌", key=f"reject_{request['id']}", help="Decline"):
                            supabase.table("friendships").delete().eq("id", request['id']).execute()
                            st.info("Request declined")
                            st.rerun()
                
                st.markdown("---")
    else:
        st.info("No pending requests")

# ==================== TAB 4: BLEND (SPOTIFY-STYLE) ====================
with tab4:
    st.subheader("🎵 Your Music Blend")
    st.caption("See how your taste matches with friends (like Spotify Blend!)")
    
    friends = get_friends(user.id)
    
    if friends:
        # Sort by compatibility
        friend_compat = []
        for friend in friends:
            compat, shared, _, _ = calculate_compatibility(user.id, friend['id'])
            friend_compat.append({'friend': friend, 'compat': compat, 'shared': shared})
        
        friend_compat.sort(key=lambda x: x['compat'], reverse=True)
        
        # Display top matches
        for data in friend_compat:
            display_compatibility_card(
                data['friend']['username'],
                data['compat'],
                data['shared']
            )
    else:
        st.info("Add friends to see your music blend!")
        if st.button("🔍 Find Friends"):
            st.switch_page("pages/5_friends.py")

# ==================== SIDEBAR ====================
with st.sidebar:
    st.markdown("### 📊 Your Stats")
    
    friends_count = len(get_friends(user.id))
    st.metric("Friends", friends_count)
    
    pending_count = len(get_pending_requests(user.id))
    if pending_count > 0:
        st.metric("⏳ Pending Requests", pending_count)
    
    # Show your liked artists count
    my_likes = supabase.table("preferences").select("artist_name").eq("user_id", user.id).eq("preference", "liked").execute()
    st.metric("🎵 Artists You Like", len(my_likes.data))
