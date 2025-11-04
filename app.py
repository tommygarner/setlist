import streamlit as st
from supabase import create_client, Client
import os

# Page config
st.set_page_config(page_title="The Setlist", page_icon="🎸", layout="wide")

# Initialize Supabase connection
@st.cache_resource
def init_supabase() -> Client:
    """Initialize Supabase client"""
    url = st.secrets["connections"]["supabase"]["SUPABASE_URL"]
    key = st.secrets["connections"]["supabase"]["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_supabase()

# Session state initialization
if "user" not in st.session_state:
    st.session_state.user = None
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

# Authentication functions
def sign_up(email: str, password: str, username: str):
    """Sign up a new user"""
    try:
        # Create auth user
        response = supabase.auth.sign_up({
            "email": email,
            "password": password
        })
        
        if response.user:
            # Create profile
            supabase.table("profiles").insert({
                "id": response.user.id,
                "username": username,
                "email": email
            }).execute()
            
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

# Check for existing session on load
def check_session():
    """Check if user has active session"""
    try:
        session = supabase.auth.get_session()
        if session:
            st.session_state.user = session.user
            st.session_state.authenticated = True
    except:
        pass

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
                st.error("Passwords don\'t match")
            elif len(password) < 6:
                st.error("Password must be at least 6 characters")
            else:
                success, message = sign_up(email, password, username)
                if success:
                    st.success(message)
                else:
                    st.error(message)

def get_user_preferences(user_id: str):
    """Get user\'s artist preferences from database"""
    try:
        response = supabase.table("preferences").select("*").eq("user_id", user_id).execute()
        # Convert to dict format: {artist_name: preference}
        return {item[\'artist_name\']: item[\'preference\'] for item in response.data}
    except Exception as e:
        st.error(f"Error loading preferences: {str(e)}")
        return {}

def save_preference(user_id: str, artist_name: str, preference: str):
    """Save or update user preference"""
    try:
        # Use upsert to insert or update
        supabase.table("preferences").upsert({
            "user_id": user_id,
            "artist_name": artist_name,
            "preference": preference
        }).execute()
        return True
    except Exception as e:
        st.error(f"Error saving preference: {str(e)}")
        return False

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
                st.write(f"@{profile.data[0][\'username\']}")
        except:
            pass
        
        st.divider()
        
        if st.button("🚪 Logout", use_container_width=True):
            if sign_out():
                st.rerun()
    
    # Main content
    st.title("🎸 The Setlist")
    st.write("**Your personalized concert discovery platform**")
    
    # Load user preferences
    user_preferences = get_user_preferences(user.id)
    
    st.divider()
    
    # Example: Display preferences count
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Artists Liked", len([p for p in user_preferences.values() if p == \'liked\']))
    with col2:
        st.metric("Artists Disliked", len([p for p in user_preferences.values() if p == \'disliked\']))
    with col3:
        st.metric("Total Preferences", len(user_preferences))
    
    st.divider()
    
    # Placeholder for your existing concert discovery features
    st.subheader("🎤 Concert Discovery")
    st.info("Your existing concert discovery features will go here!")
    st.write("This is where you\'ll integrate:")
    st.write("- Ticketmaster API concert listings")
    st.write("- Spotify integration")
    st.write("- Swipe interface")
    st.write("- Concert recommendations")
    
    # Display current preferences
    if user_preferences:
        st.subheader("Your Artist Preferences")
        for artist, pref in user_preferences.items():
            emoji = "👍" if pref == "liked" else "👎"
            st.write(f"{emoji} {artist}")

# Main app logic
check_session()

if st.session_state.authenticated:
    main_app()
else:
    login_page()
