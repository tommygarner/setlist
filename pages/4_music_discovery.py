import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
from supabase import create_client, Client
import asyncio
import aiohttp

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
    return [pref['artist_name'] for pref in response.data]

def search_seatgeek_performer(artist_name):
    """Search for performer on SeatGeek"""
    url = "https://api.seatgeek.com/2/performers"
    params = {
        "client_id": SEATGEEK_CLIENT_ID,
        "q": artist_name,
        "per_page": 1
    }
    
    try:
        response = requests.get(url, params=params, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('performers'):
                return data['performers'][0]['id']
    except:
        pass
    return None

def get_seatgeek_recommendations(performer_ids, max_results=20):
    """Get recommended events based on performer IDs"""
    if not performer_ids:
        return []
    
    url = "https://api.seatgeek.com/2/recommendations"
    params = {
        "client_id": SEATGEEK_CLIENT_ID,
        "performers.id": ",".join(map(str, performer_ids[:5])),  # Use up to 5 performers as seeds
        "postal_code": "78701",  # Austin, TX
        "range": "50mi",
        "per_page": max_results
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get('recommendations', [])
    except Exception as e:
        st.error(f"Error fetching recommendations: {str(e)}")
    
    return []

def get_weekend_events():
    """Get events happening this weekend"""
    today = datetime.now()
    # Find next Friday
    days_until_friday = (4 - today.weekday()) % 7
    if days_until_friday == 0 and today.weekday() >= 4:  # If today is Fri/Sat/Sun
        days_until_friday = 0
    
    friday = today + timedelta(days=days_until_friday)
    sunday = friday + timedelta(days=2)
    
    url = "https://api.seatgeek.com/2/events"
    params = {
        "client_id": SEATGEEK_CLIENT_ID,
        "venue.city": "Austin",
        "venue.state": "TX",
        "taxonomies.name": "concert",
        "datetime_local.gte": friday.strftime("%Y-%m-%d"),
        "datetime_local.lte": sunday.strftime("%Y-%m-%d"),
        "per_page": 20
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            return response.json().get('events', [])
    except:
        pass
    
    return []

def display_event_card(event, score=None):
    """Display a concert event card"""
    with st.container():
        col1, col2, col3 = st.columns([1, 3, 1])
        
        with col1:
            if event['performers'] and event['performers'][0].get('image'):
                st.image(event['performers'][0]['image'], use_container_width=True)
        
        with col2:
            st.markdown(f"### {event['title']}")
            st.write(f"📍 {event['venue']['name']}")
            st.write(f"📅 {event['datetime_local'][:10]}")
            if score:
                st.progress(score / 100)
                st.caption(f"{int(score)}% match")
        
        with col3:
            if st.button("🎟️ View Tickets", key=f"tickets_{event['id']}", use_container_width=True):
                st.link_button("Open SeatGeek", event['url'], use_container_width=True)
            
            if st.button("💾 Save", key=f"save_{event['id']}", use_container_width=True):
                # Save to concerts_discovered
                concert_data = {
                    "user_id": user.id,
                    "event_id": str(event['id']),
                    "event_name": event['title'],
                    "artist_name": event['performers'][0]['name'] if event['performers'] else "Unknown",
                    "venue_name": event['venue']['name'],
                    "city": event['venue']['city'],
                    "state": event['venue']['state'],
                    "date": event['datetime_local'][:10],
                    "time": event['datetime_local'][11:19] if len(event['datetime_local']) > 10 else None,
                    "url": event['url']
                }
                supabase.table("concerts_discovered").upsert(concert_data, on_conflict='user_id,event_id').execute()
                st.success("✅ Saved to your concerts!")
        
        st.markdown("---")

# ==================== MAIN UI ====================
st.title("✨ Music Discovery")
st.markdown("Discover new concerts based on your music taste")

# Tabs for different discovery modes
tab1, tab2, tab3, tab4 = st.tabs(["🎵 For You", "🔥 This Weekend", "🎲 Surprise Me", "🔍 Similar Artists"])

# ==================== TAB 1: FOR YOU ====================
with tab1:
    st.subheader("🎟️ Concerts You'll Love")
    st.caption("Full concert events based on your music taste")
    
    liked_artists = get_user_liked_artists()
    
    if not liked_artists:
        st.info("👆 Start swiping on artists to get personalized concert recommendations!")
        if st.button("🎸 Go to Artist Swipe"):
            st.switch_page("pages/3_artist_swipe.py")
    else:
        st.success(f"Based on {len(liked_artists)} artists you like: **{', '.join(liked_artists[:3])}**{' and more...' if len(liked_artists) > 3 else ''}")
        
        with st.spinner("Finding concerts you'll love..."):
            # Get all Austin concerts
            url = "https://api.seatgeek.com/2/events"
            params = {
                "client_id": SEATGEEK_CLIENT_ID,
                "venue.city": "Austin",
                "venue.state": "TX",
                "taxonomies.name": "concert",
                "per_page": 100,
                "sort": "datetime_local.asc"
            }
            
            try:
                response = requests.get(url, params=params, timeout=10)
                if response.status_code == 200:
                    all_events = response.json().get('events', [])
                    
                    # Score events based on how well they match your taste
                    scored_events = []
                    for event in all_events:
                        score = 0
                        event_artists = [p['name'].lower() for p in event.get('performers', [])]
                        
                        # High score if you've liked this artist
                        for artist in liked_artists:
                            if artist.lower() in event_artists:
                                score += 100
                        
                        # Medium score if artist name contains words from your liked artists
                        for artist in liked_artists:
                            for word in artist.lower().split():
                                if len(word) > 3:  # Skip short words
                                    for event_artist in event_artists:
                                        if word in event_artist:
                                            score += 10
                        
                        # Bonus for popularity
                        score += event.get('score', 0) * 0.1
                        
                        if score > 0:
                            scored_events.append({
                                'event': event,
                                'score': score
                            })
                    
                    # Sort by score
                    scored_events.sort(key=lambda x: x['score'], reverse=True)
                    
                    if scored_events:
                        st.success(f"🎉 Found {len(scored_events)} concerts recommended for you!")
                        st.caption("Showing concerts sorted by how well they match your taste")
                        
                        for item in scored_events[:15]:
                            event = item['event']
                            score = min(item['score'], 100)  # Cap at 100
                            display_event_card(event, score)
                    else:
                        st.info("No matching concerts found in Austin right now. Check 'This Weekend' or 'Artists You Might Like'!")
            except Exception as e:
                st.error(f"Error: {str(e)}")


# ==================== TAB 2: THIS WEEKEND ====================
with tab2:
    st.subheader("🔥 This Weekend in Austin")
    st.caption("Concerts happening Friday - Sunday")
    
    if st.button("🔄 Refresh Weekend Events", key="refresh_weekend"):
        st.rerun()
    
    with st.spinner("Loading weekend concerts..."):
        weekend_events = get_weekend_events()
        
        if weekend_events:
            st.success(f"Found {len(weekend_events)} concerts this weekend!")
            
            for event in weekend_events:
                display_event_card(event)
        else:
            st.info("No concerts found this weekend. Check back later!")

# ==================== TAB 3: SURPRISE ME ====================
with tab3:
    st.subheader("🎲 Surprise Me!")
    st.caption("Discover something completely random")
    
    if st.button("🎲 Find a Random Concert", type="primary", use_container_width=True):
        with st.spinner("Finding a surprise concert..."):
            # Get random concerts in Austin
            url = "https://api.seatgeek.com/2/events"
            params = {
                "client_id": SEATGEEK_CLIENT_ID,
                "venue.city": "Austin",
                "venue.state": "TX",
                "taxonomies.name": "concert",
                "per_page": 10,
                "sort": "score.desc"
            }
            
            try:
                response = requests.get(url, params=params, timeout=10)
                if response.status_code == 200:
                    events = response.json().get('events', [])
                    if events:
                        import random
                        random_event = random.choice(events)
                        st.success("🎉 Here's a concert you might enjoy:")
                        display_event_card(random_event)
                    else:
                        st.info("No concerts found. Try again!")
            except:
                st.error("Error fetching random concert")

# ==================== TAB 4: SIMILAR ARTISTS ====================
with tab4:
    st.subheader("🎯 Artists You Might Like")
    st.caption("Based on artists you've already liked")
    
    liked_artists = get_user_liked_artists()
    
    if not liked_artists:
        st.info("👆 Like some artists first to get personalized recommendations!")
        if st.button("🎸 Go to Artist Swipe"):
            st.switch_page("pages/3_artist_swipe.py")
    else:
        st.write(f"Finding artists similar to: **{', '.join(liked_artists[:3])}**{' and more...' if len(liked_artists) > 3 else ''}")
        
        if st.button("✨ Get Personalized Recommendations", type="primary", use_container_width=True):
            with st.spinner("Finding artists you'll love..."):
                # Get all Austin concerts
                url = "https://api.seatgeek.com/2/events"
                params = {
                    "client_id": SEATGEEK_CLIENT_ID,
                    "venue.city": "Austin",
                    "venue.state": "TX",
                    "taxonomies.name": "concert",
                    "per_page": 100,
                    "sort": "score.desc"
                }
                
                try:
                    response = requests.get(url, params=params, timeout=10)
                    if response.status_code == 200:
                        events = response.json().get('events', [])
                        
                        # Get your concerts from database to exclude artists you already know about
                        saved_concerts = supabase.table("concerts_discovered").select("artist_name").eq("user_id", user.id).execute()
                        known_artists = set([c['artist_name'].lower() for c in saved_concerts.data])
                        
                        # Also exclude artists you've already liked or disliked
                        prefs = supabase.table("preferences").select("artist_name").eq("user_id", user.id).execute()
                        rated_artists = set([p['artist_name'].lower() for p in prefs.data])
                        
                        # Extract NEW artists you haven't seen yet
                        new_artists = {}
                        for event in events:
                            for performer in event.get('performers', []):
                                artist_name = performer.get('name')
                                if artist_name:
                                    artist_lower = artist_name.lower()
                                    # Only show if you haven't seen this artist before
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
                            st.success(f"🎉 Found {len(new_artists)} NEW artists you haven't discovered yet!")
                            st.caption("These are artists with Austin concerts that you haven't swiped on yet")
                            
                            # Display in grid with save option
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
                                    
                                    # Add to discovery button
                                    if st.button("➕ Add to Swipe", key=f"add_{data['id']}_{i}", use_container_width=True):
                                        # Add this concert to your concerts_discovered
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
                                        supabase.table("concerts_discovered").upsert(concert_data, on_conflict='user_id,event_id').execute()
                                        st.success(f"✅ Added {name}! Go to Artist Swipe to rate them!")
                                    
                                    st.markdown("")
                        else:
                            st.info("🎊 Wow! You've already discovered all Austin concert artists!")
                            st.caption("Check back later for new concerts, or explore 'This Weekend' tab")
                    else:
                        st.error(f"API Error: {response.status_code}")
                except Exception as e:
                    st.error(f"Error: {str(e)}")
    
    # Quick search option
    if liked_artists:
        st.markdown("---")
        st.markdown("### 🔍 Quick Search")
        
        search_artist = st.text_input("Search for a specific artist:", placeholder="e.g. Taylor Swift", key="artist_search")
        
        if search_artist and st.button("Search", key="search_btn"):
            with st.spinner(f"Searching for {search_artist}..."):
                performer_id = search_seatgeek_performer(search_artist)
                
                if performer_id:
                    url = "https://api.seatgeek.com/2/events"
                    params = {
                        "client_id": SEATGEEK_CLIENT_ID,
                        "performers.id": performer_id,
                        "per_page": 10
                    }
                    
                    try:
                        response = requests.get(url, params=params, timeout=10)
                        if response.status_code == 200:
                            events = response.json().get('events', [])
                            
                            if events:
                                st.success(f"Found {len(events)} {search_artist} concerts!")
                                for event in events[:5]:
                                    display_event_card(event)
                            else:
                                st.info(f"No upcoming {search_artist} concerts found")
                    except:
                        st.error("Error fetching events")
                else:
                    st.warning(f"Couldn't find '{search_artist}'")


# ==================== SIDEBAR ====================
with st.sidebar:
    st.markdown("### 🎯 Discovery Stats")
    st.metric("Artists You Like", len(get_user_liked_artists()))
    
    saved_concerts = supabase.table("concerts_discovered").select("event_id").eq("user_id", user.id).execute()
    st.metric("Concerts Saved", len(saved_concerts.data))
