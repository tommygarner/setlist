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

# ==================== HELPER FUNCTIONS ====================
def get_user_by_username(username):
    """Search for user by username"""
    response = supabase.table("profiles").select("*").eq("username", username).execute()
    return response.data[0] if response.data else None

def send_friend_request(user_id, friend_id):
    """Send friend request"""
    try:
        # Check if friendship already exists
        existing = supabase.table("friendships").select("*").or_(
            f"and(user_id.eq.{user_id},friend_id.eq.{friend_id}),and(user_id.eq.{friend_id},friend_id.eq.{user_id})"
        ).execute()
        
        if existing.data:
            return {'success': False, 'message': 'Friend request already exists'}
        
        # Create friend request
        supabase.table("friendships").insert({
            "user_id": user_id,
            "friend_id": friend_id,
            "status": "pending"
        }).execute()
        
        return {'success': True, 'message': 'Friend request sent!'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def get_friends(user_id):
    """Get accepted friends"""
    response = supabase.table("friendships").select(
        "*, friend:friend_id(id, username, email)"
    ).eq("user_id", user_id).eq("status", "accepted").execute()
    
    return response.data

def get_pending_requests(user_id):
    """Get pending friend requests received"""
    response = supabase.table("friendships").select(
        "*, requester:user_id(id, username, email)"
    ).eq("friend_id", user_id).eq("status", "pending").execute()
    
    return response.data

def calculate_compatibility(user1_id, user2_id):
    """Calculate music compatibility between two users"""
    # Get both users' liked artists
    user1_likes = supabase.table("preferences").select("artist_name").eq("user_id", user1_id).eq("preference", "liked").execute()
    user2_likes = supabase.table("preferences").select("artist_name").eq("user_id", user2_id).eq("preference", "liked").execute()
    
    user1_artists = set([p['artist_name'].lower() for p in user1_likes.data if p.get('artist_name')])
    user2_artists = set([p['artist_name'].lower() for p in user2_likes.data if p.get('artist_name')])
    
    if not user1_artists or not user2_artists:
        return 0, []
    
    # Calculate Jaccard similarity
    shared = user1_artists.intersection(user2_artists)
    total = user1_artists.union(user2_artists)
    
    compatibility = (len(shared) / len(total)) * 100 if total else 0
    
    return compatibility, list(shared)

# ==================== MAIN UI ====================
st.title("👥 Friends")
st.markdown("Connect with friends and discover concerts together")

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["🔍 Find Friends", "👥 My Friends", "📬 Requests", "🎵 Compatibility"])

# ==================== TAB 1: FIND FRIENDS ====================
with tab1:
    st.subheader("🔍 Find Friends")
    st.caption("Search for users by username")
    
    search_username = st.text_input("Enter username:", placeholder="e.g. johndoe")
    
    if st.button("Search", type="primary"):
        if search_username:
            if search_username == user.username:
                st.warning("That's you! 😄")
            else:
                found_user = get_user_by_username(search_username)
                
                if found_user:
                    st.success(f"Found: **{found_user['username']}**")
                    
                    # Calculate compatibility
                    compat, shared_artists = calculate_compatibility(user.id, found_user['id'])
                    
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.metric("Music Compatibility", f"{int(compat)}%")
                        if shared_artists:
                            st.caption(f"You both like: {', '.join(list(shared_artists)[:5])}")
                    
                    with col2:
                        if st.button("➕ Add Friend", use_container_width=True):
                            result = send_friend_request(user.id, found_user['id'])
                            if result['success']:
                                st.success(result['message'])
                            else:
                                st.error(result['message'])
                else:
                    st.error("User not found")

# ==================== TAB 2: MY FRIENDS ====================
with tab2:
    st.subheader("👥 My Friends")
    
    friends = get_friends(user.id)
    
    if friends:
        st.success(f"You have {len(friends)} friend(s)")
        
        for friendship in friends:
            friend = friendship['friend']
            
            with st.container():
                col1, col2, col3 = st.columns([2, 2, 1])
                
                with col1:
                    st.markdown(f"### {friend['username']}")
                
                with col2:
                    compat, shared = calculate_compatibility(user.id, friend['id'])
                    st.metric("Compatibility", f"{int(compat)}%")
                    if shared:
                        st.caption(f"Shared artists: {len(shared)}")
                
                with col3:
                    if st.button("View Profile", key=f"view_{friend['id']}"):
                        st.info("Profile view coming soon!")
                
                st.markdown("---")
    else:
        st.info("No friends yet. Search for users in the 'Find Friends' tab!")

# ==================== TAB 3: REQUESTS ====================
with tab3:
    st.subheader("📬 Friend Requests")
    
    pending = get_pending_requests(user.id)
    
    if pending:
        st.info(f"You have {len(pending)} pending request(s)")
        
        for request in pending:
            requester = request['requester']
            
            with st.container():
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.markdown(f"**{requester['username']}** wants to be friends")
                    compat, shared = calculate_compatibility(user.id, requester['id'])
                    st.caption(f"🎵 {int(compat)}% music compatibility")
                
                with col2:
                    col_a, col_b = st.columns(2)
                    
                    with col_a:
                        if st.button("✅", key=f"accept_{request['id']}"):
                            # Accept request
                            supabase.table("friendships").update({"status": "accepted"}).eq("id", request['id']).execute()
                            # Create reciprocal friendship
                            supabase.table("friendships").insert({
                                "user_id": user.id,
                                "friend_id": requester['id'],
                                "status": "accepted"
                            }).execute()
                            st.success("Friend added!")
                            st.rerun()
                    
                    with col_b:
                        if st.button("❌", key=f"reject_{request['id']}"):
                            supabase.table("friendships").delete().eq("id", request['id']).execute()
                            st.info("Request declined")
                            st.rerun()
                
                st.markdown("---")
    else:
        st.info("No pending requests")

# ==================== TAB 4: COMPATIBILITY ====================
with tab4:
    st.subheader("🎵 Music Compatibility")
    st.caption("See how your music taste compares with friends")
    
    friends = get_friends(user.id)
    
    if friends:
        compatibility_data = []
        
        for friendship in friends:
            friend = friendship['friend']
            compat, shared = calculate_compatibility(user.id, friend['id'])
            
            compatibility_data.append({
                'Friend': friend['username'],
                'Compatibility': int(compat),
                'Shared Artists': len(shared)
            })
        
        # Sort by compatibility
        df = pd.DataFrame(compatibility_data).sort_values('Compatibility', ascending=False)
        
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # Show top match
        if len(df) > 0:
            top_match = df.iloc[0]
            st.success(f"🏆 Best Match: **{top_match['Friend']}** ({top_match['Compatibility']}% compatible)")
    else:
        st.info("Add friends to see compatibility!")

# ==================== SIDEBAR ====================
with st.sidebar:
    st.markdown("### 📊 Your Stats")
    
    friends_count = len(get_friends(user.id))
    st.metric("Friends", friends_count)
    
    pending_count = len(get_pending_requests(user.id))
    if pending_count > 0:
        st.metric("Pending Requests", pending_count)
