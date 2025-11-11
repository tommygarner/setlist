import streamlit as st
from supabase import create_client, Client
import os

# Page config
st.set_page_config(page_title="The Setlist", page_icon="🎸", layout="wide")

# Initialize Supabase connection
def init_supabase() -> Client:
    """Initialize Supabase client (no cache - each call gets fresh client)"""
    url = st.secrets["connections"]["supabase"]["SUPABASE_URL"]
    key = st.secrets["connections"]["supabase"]["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_supabase()  # Creates a fresh client per session

# Session state initialization
if "user" not in st.session_state:
    st.session_state.user = None
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

# Authentication functions
def sign_up(email: str, password: str, username: str):
    """Sign up a new user"""
    try:
        response = supabase.auth.sign_up({
            "email": email,
            "password": password,
            "options": {
                "data": {
                    "username": username
                }
            }
        })
        
        if response.user:
            return True, "Account created! Please check your email to verify."
        return False, "Sign up failed"
    except Exception as e:
        return False, str(e)

def sign_in(email: str, password: str):
    """Sign in existing user"""
    try:
        response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        
        if response.user:
            st.session_state.user = response.user
            st.session_state.authenticated = True
            return True, "Login successful!"
        return False, "Login failed"
    except Exception as e:
        return False, str(e)

def sign_out():
    """Sign out current user"""
    try:
        supabase.auth.sign_out()
        st.session_state.user = None
        st.session_state.authenticated = False
        return True
    except Exception as e:
        st.error(f"Sign out error: {str(e)}")
        return False

def check_session():
    """Check if user has active session"""
    try:
        session = supabase.auth.get_session()
        if session:
            st.session_state.user = session.user
            st.session_state.authenticated = True
    except:
        pass

def ensure_session():
    """Ensure session state is properly set"""
    if not st.session_state.get('authenticated', False):
        check_session()

# UI Components
def login_page():
    """Display login/signup page"""
    st.title("🎸 Welcome to The Setlist")
    st.write("Discover concerts you'll love with your friends")
    
    tab1, tab2 = st.tabs(["Login", "Sign Up"])
    
    with tab1:
        st.subheader("Login to your account")
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_password")
        
        if st.button("Login", type="primary", use_container_width=True):
            if email and password:
                success, message = sign_in(email, password)
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)
            else:
                st.warning("Please enter both email and password")
    
    with tab2:
        st.subheader("Create a new account")
        username = st.text_input("Username", key="signup_username")
        email = st.text_input("Email", key="signup_email")
        password = st.text_input("Password", type="password", key="signup_password")
        password_confirm = st.text_input("Confirm Password", type="password", key="signup_password_confirm")
        
        if st.button("Sign Up", type="primary", use_container_width=True):
            if not all([username, email, password, password_confirm]):
                st.warning("Please fill in all fields")
            elif password != password_confirm:
                st.error("Passwords don't match")
            elif len(password) < 6:
                st.error("Password must be at least 6 characters")
            else:
                success, message = sign_up(email, password, username)
                if success:
                    st.success(message)
                else:
                    st.error(message)

def main_app():
    """Main application (shown when authenticated)"""
    user = st.session_state.user
    
    # Sidebar with user info
    with st.sidebar:
        st.write(f"👤 **{user.email}**")
        
        # Get user profile
        try:
            profile = supabase.table("profiles").select("username").eq("id", user.id).execute()
            if profile.data:
                st.write(f"@{profile.data[0]['username']}")
        except:
            pass
        
        st.divider()
        
        if st.button("🚪 Logout", use_container_width=True):
            if sign_out():
                st.rerun()
    
    # Main content
    st.title("🎸 The Setlist")
    st.write("**Your personalized concert discovery platform**")
    
    st.divider()
    
    # User Stats - REAL DATA FROM DATABASE (NO CACHE)
    st.subheader("📊 Your Stats")
    
    try:
        # Query preferences from database (fresh every time)
        prefs_result = supabase.table("preferences").select("preference").eq("user_id", user.id).execute()
        
        liked_count = sum(1 for p in prefs_result.data if p['preference'] == 'liked')
        disliked_count = sum(1 for p in prefs_result.data if p['preference'] == 'disliked')
        total_count = len(prefs_result.data)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Artists Liked", liked_count, delta="👍")
        
        with col2:
            st.metric("Artists Disliked", disliked_count, delta="👎")
        
        with col3:
            st.metric("Total Preferences", total_count)
    
    except Exception as e:
        st.warning(f"Could not load stats: {str(e)}")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Artists Liked", 0)
        with col2:
            st.metric("Artists Disliked", 0)
        with col3:
            st.metric("Total Preferences", 0)
    
    st.divider()
    
    # Placeholder for concert discovery features
    st.subheader("🎤 Concert Discovery")
    st.info("Your concert discovery features are ready!")
    st.write("**Navigate using the sidebar:**")
    st.write("- 🎵 **Connect Spotify** - Link your Spotify account")
    st.write("- 🎤 **Discover Concerts** - Find shows from your favorite artists")
    st.write("- 🎸 **Artist Swipe** - Swipe through concerts and choose your favorites")

# Handle Spotify OAuth callback
query_params = st.query_params
if 'code' in query_params and st.session_state.authenticated:
    st.switch_page("pages/1_connect_spotify.py")

if st.session_state.authenticated:
    main_app()
else:
    login_page()
