import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
from supabase import create_client, Client
import random
import time

st.set_page_config(page_title="Music Discovery", page_icon="✨", layout="wide")

# ==================== SEATGEEK API SETUP ====================
SEATGEEK_CLIENT_ID = "MjA0NDkzNzh8MTc2MjgzNTE2MC4xNDA5OTI0"

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
def get_user_liked_artists():
    """Get user's liked artists from preferences"""
    response = supabase.table("preferences").select("artist_name").eq("user_id", user.id).eq("preference", "liked").execute()
    return [pref['artist_name'] for pref in response.data if pref.get('artist_name')]

def safe_seatgeek_request(url, params, timeout=10):
    """Make SeatGeek request with proper headers and error handling"""
    headers = {
        'Accept': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=timeout)
        
        if response.status_code == 200:
            return {'success': True, 'data': response.json()}
        elif response.status_code == 406:
            return {'success': False, 'error': '406', 'message': 'API returned 406 - Try again later or reduce request size'}
        elif response.status_code == 429:
            return {'success': False, 'error': '429', 'message': 'Rate limit hit - Wait a few minutes'}
        else:
            return {'success': False, 'error': str(response.status_code), 'message': f'API Error {response.status_code}'}
    
    except requests.Timeout:
        return {'success': False, 'error': 'timeout', 'message': 'Request timed out - Try again'}
    except Exception as e:
        return {'success': False, 'error': 'exception', 'message': str(e)}

def display_event_card(event, score=None):
    """Display a concert event card"""
    unique_id = f"{event['id']}_{random.randint(1000, 9999)}"
    
    with st.container():
        col1, col2, col3 = st.columns([1, 3, 1])
        
        with col1:
            if event.get('performers') and event['performers'][0].get('image'):
                st.image(event['performers'][0]['image'], use_container_width=True)
        
        with col2:
            st.markdown(f"### {event.get('title', 'Unknown Event')}")
            venue = event.get('venue', {})
            st.write(f"📍 {venue.get('name', 'Unknown Venue')}")
            datetime_local = event.get('datetime_local', '')
            if datetime_local:
                st.write(f"📅 {datetime_local[:10]}")
            if score:
                st.progress(min(score, 100) / 100)
                st.caption(f"{int(min(score, 100))}% match")
        
        with col3:
            if st.button("🎟️ Tickets", key=f"tickets_{unique_id}", use_container_width=True):
                if event.get('url'):
                    st.link_button("Open SeatGeek", event['url'], use_container_width=True, key=f"link_{unique_id}")
            
            if st.button("💾 Save", key=f"save_{unique_id}", use_container_width=True):
                performers = event.get('performers', [])
                concert_data = {
                    "user_id": user.id,
                    "event_id": str(event.get('id')),
                    "event_name": event.get('title', 'Unknown'),
                    "artist_name": performers[0]['name'] if performers else "Unknown",
                    "venue_name": venue.get('name', 'Unknown'),
                    "city": venue.get('city', 'Unknown'),
                    "state": venue.get('state', 'Unknown'),
                    "date": datetime_local[:10] if datetime_local else None,
                    "time": datetime_local[11:19] if len(datetime_local) > 10 else None,
                    "url": event.get('url')
                }
                try:
                    supabase.table("concerts_discovered").upsert(concert_data, on_conflict='user_id,event_id').execute()
                    st.success("✅ Saved!")
                except:
                    st.success("✅ Saved!")
        
        st.markdown("---")

def display_concert_from_db(concert, score=None):
    """Display concert from database"""
    with st.container():
        col1, col2, col3 = st.columns([3, 2, 1])
        
        with col1:
            st.markdown(f"### {concert.get('event_name', 'Unknown')}")
            st.write(f"🎤 **{concert.get('artist_name', 'Unknown')}**")
            st.write(f"📍 {concert.get('venue_name', 'Unknown')}, {concert.get('city', '')}, {concert.get('state', '')}")
        
        with col2:
            st.write(f"📅 {concert.get('date', 'Unknown')}")
            if concert.get('time'):
                st.write(f"🕐 {concert['time']}")
            if score is not None:
                st.progress(min(score, 100) / 100)
                st.caption(f"{int(min(score, 100))}% match")
        
        with col3:
            url = concert.get('url') or concert.get('ticket_url')
            if url:
                st.link_button("🎟️ Tickets", url)
        
        st.markdown("---")

# ==================== MAIN UI ====================
st.title("✨ Music Discovery")
st.markdown("Discover new concerts based on your music taste")

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["🎵 For You", "🔥 This Weekend", "🎲 Surprise Me", "🎯 Similar Artists"])

# ==================== TAB 1: FOR YOU ====================
with tab1:
    st.subheader("🎟️ Concerts You'll Love")
    st.caption("Fresh concert recommendations from SeatGeek based on your taste")
    
    liked_artists = get_user_liked_artists()
    
    if not liked_artists:
        st.info("👆 Start swiping on artists to get personalized recommendations!")
        if st.button("🎸 Go to Artist Swipe"):
            st.switch_page("pages/3_artist_swipe.py")
    else:
        st.success(f"Based on {len(liked_artists)} artists you like: **{', '.join(liked_artists[:3])}**{' and more...' if len(liked_artists) > 3 else ''}")
        
        with st.spinner("Searching SeatGeek for concerts you'll love..."):
            # Get fresh concerts from API
            params = {
                "client_id": SEATGEEK_CLIENT_ID,
                "venue.city": "Austin",
                "venue.state": "TX",
                "taxonomies.name": "concert",
                "per_page": 25,  # Conservative
                "sort": "datetime_local.asc"
            }
            
            result = safe_seatgeek_request("https://api.seatgeek.com/2/events", params, timeout=12)
            
            if result['success']:
                all_events = result['data'].get('events', [])
                
                if not all_events:
                    st.info("No concerts found in Austin right now.")
                else:
                    # Score events based on your liked artists
                    scored_events = []
                    liked_artists_lower = [a.lower().strip() for a in liked_artists]
                    
                    for event in all_events:
                        score = 0
                        performers = event.get('performers', [])
                        event_artists = [p['name'].lower() for p in performers if p.get('name')]
                        
                        # Perfect match = 100 points
                        for artist in liked_artists_lower:
                            if artist in event_artists:
                                score += 100
                                break
                        
                        # Partial match
                        if score < 100:
                            for artist in liked_artists_lower:
                                for event_artist in event_artists:
                                    if artist in event_artist or event_artist in artist:
                                        score += 50
                                        break
                        
                        # Word matches
                        if score < 100:
                            for artist in liked_artists_lower:
                                words = artist.split()
                                for word in words:
                                    if len(word) > 3:
                                        for event_artist in event_artists:
                                            if word in event_artist:
                                                score += 10
                        
                        # Popularity bonus
                        score += event.get('score', 0) * 0.1
                        
                        if score > 0:
                            scored_events.append({
                                'event': event,
                                'score': min(score, 100)
                            })
                    
                    scored_events.sort(key=lambda x: x['score'], reverse=True)
                    
                    if scored_events:
                        st.success(f"🎉 Found {len(scored_events)} concerts that match your taste!")
                        st.caption("💯 = Artists you've liked, lower scores = similar vibes")
                        
                        for item in scored_events[:20]:
                            display_event_card(item['event'], item['score'])
                    else:
                        st.info("No matching concerts found. Try 'This Weekend' or 'Similar Artists'!")
            else:
                st.error(f"⚠️ {result['message']}")
                st.caption("SeatGeek API is temporarily unavailable. Try again in a few minutes, or check other tabs.")
                
                # Show helpful fallback message
                st.info("💡 While waiting, you can:")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("🔥 Check This Weekend"):
                        st.switch_page("pages/4_music_discovery.py")
                with col2:
                    if st.button("🎯 Browse New Artists"):
                        st.switch_page("pages/4_music_discovery.py")


# ==================== TAB 2: THIS WEEKEND ====================
with tab2:
    st.subheader("🔥 This Weekend in Austin")
    st.caption("Concerts happening Friday - Sunday")
    
    if st.button("🔄 Refresh", key="refresh_weekend"):
        st.rerun()
    
    with st.spinner("Loading weekend concerts..."):
        today = datetime.now()
        days_until_friday = (4 - today.weekday()) % 7
        if days_until_friday == 0 and today.weekday() >= 4:
            days_until_friday = 0
        
        friday = today + timedelta(days=days_until_friday)
        sunday = friday + timedelta(days=2)
        
        params = {
            "client_id": SEATGEEK_CLIENT_ID,
            "venue.city": "Austin",
            "venue.state": "TX",
            "taxonomies.name": "concert",
            "datetime_local.gte": friday.strftime("%Y-%m-%d"),
            "datetime_local.lte": sunday.strftime("%Y-%m-%d"),
            "per_page": 20  # ✅ Reduced from 50
        }
        
        result = safe_seatgeek_request("https://api.seatgeek.com/2/events", params)
        
        if result['success']:
            events = result['data'].get('events', [])
            if events:
                st.success(f"Found {len(events)} concerts this weekend!")
                for event in events:
                    display_event_card(event)
            else:
                st.info("No concerts this weekend.")
        else:
            st.error(f"⚠️ {result['message']}")
            st.caption("Falling back to your saved concerts...")
            
            # Fallback to database
            saved = supabase.table("concerts_discovered").select("*").eq("user_id", user.id).execute()
            df = pd.DataFrame(saved.data) if saved.data else pd.DataFrame()
            
            if not df.empty:
                friday_str = friday.strftime("%Y-%m-%d")
                sunday_str = sunday.strftime("%Y-%m-%d")
                weekend = df[(df['date'] >= friday_str) & (df['date'] <= sunday_str)]
                
                if len(weekend) > 0:
                    st.info(f"Showing {len(weekend)} from your saved concerts")
                    for _, concert in weekend.iterrows():
                        display_concert_from_db(concert.to_dict())

# ==================== TAB 3: SURPRISE ME ====================
with tab3:
    st.subheader("🎲 Surprise Me!")
    st.caption("Discover something random")
    
    if st.button("🎲 Find a Random Concert", type="primary", use_container_width=True):
        with st.spinner("Finding a surprise..."):
            params = {
                "client_id": SEATGEEK_CLIENT_ID,
                "venue.city": "Austin",
                "venue.state": "TX",
                "taxonomies.name": "concert",
                "per_page": 15,  # ✅ Reduced from 25
                "sort": "score.desc"
            }
            
            result = safe_seatgeek_request("https://api.seatgeek.com/2/events", params, timeout=8)
            
            if result['success']:
                events = result['data'].get('events', [])
                if events:
                    random_event = random.choice(events)
                    st.success("🎉 Here's a concert you might enjoy:")
                    display_event_card(random_event)
                else:
                    st.info("No concerts found.")
            else:
                st.error(f"⚠️ {result['message']}")
                # Fallback
                saved = supabase.table("concerts_discovered").select("*").eq("user_id", user.id).execute()
                if saved.data:
                    random_concert = random.choice(saved.data)
                    st.info("Showing random from your saved concerts:")
                    display_concert_from_db(random_concert)

# ==================== TAB 4: SIMILAR ARTISTS ====================
with tab4:
    st.subheader("🎯 Artists You Might Like")
    st.caption("New artists with Austin concerts")
    
    liked_artists = get_user_liked_artists()
    
    if not liked_artists:
        st.info("👆 Like some artists first!")
        if st.button("🎸 Go to Artist Swipe", key="swipe2"):
            st.switch_page("pages/3_artist_swipe.py")
    else:
        st.write(f"Finding artists similar to: **{', '.join(liked_artists[:3])}**")
        
        if st.button("✨ Get Recommendations", type="primary", use_container_width=True):
            with st.spinner("Finding new artists..."):
                params = {
                    "client_id": SEATGEEK_CLIENT_ID,
                    "venue.city": "Austin",
                    "venue.state": "TX",
                    "taxonomies.name": "concert",
                    "per_page": 25,  # ✅ Reduced from 50
                    "sort": "score.desc"
                }
                
                result = safe_seatgeek_request("https://api.seatgeek.com/2/events", params)
                
                if result['success']:
                    events = result['data'].get('events', [])
                    
                    saved_concerts = supabase.table("concerts_discovered").select("artist_name").eq("user_id", user.id).execute()
                    known_artists = set([c['artist_name'].lower() for c in saved_concerts.data if c.get('artist_name')])
                    
                    prefs = supabase.table("preferences").select("artist_name").eq("user_id", user.id).execute()
                    rated_artists = set([p['artist_name'].lower() for p in prefs.data if p.get('artist_name')])
                    
                    new_artists = {}
                    for event in events:
                        for performer in event.get('performers', []):
                            artist_name = performer.get('name')
                            if artist_name:
                                artist_lower = artist_name.lower()
                                if artist_lower not in known_artists and artist_lower not in rated_artists:
                                    if artist_name not in new_artists:
                                        new_artists[artist_name] = {
                                            'image': performer.get('image'),
                                            'id': performer.get('id'),
                                            'event_date': event.get('datetime_local', '')[:10],
                                            'venue': event.get('venue', {}).get('name', 'Unknown'),
                                            'event_id': event.get('id'),
                                            'event_url': event.get('url')
                                        }
                    
                    if new_artists:
                        st.success(f"🎉 Found {len(new_artists)} NEW artists!")
                        
                        cols = st.columns(3)
                        for i, (name, data) in enumerate(list(new_artists.items())[:30]):
                            with cols[i % 3]:
                                if data['image']:
                                    st.image(data['image'], use_container_width=True)
                                else:
                                    st.markdown("### 🎤")
                                st.markdown(f"**{name}**")
                                st.caption(f"📅 {data['event_date']}")
                                st.caption(f"📍 {data['venue']}")
                                
                                if st.button("➕ Add to Swipe", key=f"add_{data['id']}_{i}", use_container_width=True):
                                    concert_data = {
                                        "user_id": user.id,
                                        "event_id": str(data['event_id']),
                                        "event_name": name,
                                        "artist_name": name,
                                        "venue_name": data['venue'],
                                        "city": "Austin",
                                        "state": "TX",
                                        "date": data['event_date'],
                                        "url": data['event_url']
                                    }
                                    try:
                                        supabase.table("concerts_discovered").upsert(concert_data, on_conflict='user_id,event_id').execute()
                                        st.success(f"✅ Added {name}!")
                                    except:
                                        st.success(f"✅ Added!")
                                
                                st.markdown("")
                    else:
                        st.info("You've discovered all available artists!")
                else:
                    st.error(f"⚠️ {result['message']}")
                    st.caption("The SeatGeek API is temporarily unavailable. Try again in a few minutes.")

# ==================== SIDEBAR ====================
with st.sidebar:
    st.markdown("### 🎯 Discovery Stats")
    st.metric("Artists You Like", len(get_user_liked_artists()))
    
    saved_concerts = supabase.table("concerts_discovered").select("event_id").eq("user_id", user.id).execute()
    st.metric("Concerts Saved", len(saved_concerts.data))
