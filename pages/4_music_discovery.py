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
    st.subheader("Concerts Recommended For You")
    st.caption("Based on artists you've liked")
    
    liked_artists = get_user_liked_artists()
    
    if not liked_artists:
        st.info("👆 Start swiping on artists to get personalized recommendations!")
        if st.button("🎸 Go to Artist Swipe"):
            st.switch_page("pages/3_artist_swipe.py")
    else:
        st.success(f"Finding concerts based on {len(liked_artists)} artists you like...")
        
        with st.spinner("Searching for recommendations..."):
            # Get SeatGeek performer IDs for liked artists
            performer_ids = []
            for artist in liked_artists[:10]:  # Use top 10 liked artists
                performer_id = search_seatgeek_performer(artist)
                if performer_id:
                    performer_ids.append(performer_id)
            
            if performer_ids:
                recommendations = get_seatgeek_recommendations(performer_ids)
                
                if recommendations:
                    st.success(f"Found {len(recommendations)} recommended concerts!")
                    
                    for rec in recommendations:
                        event = rec.get('event')
                        score = rec.get('score', 50)
                        if event:
                            display_event_card(event, score)
                else:
                    st.info("No recommendations found. Try liking more artists!")
            else:
                st.warning("Couldn't find SeatGeek data for your liked artists. Try searching for concerts manually!")

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
    st.subheader("🔍 Find Similar Artists")
    st.caption("Search for an artist and discover concerts by similar performers")
    
    search_artist = st.text_input("Enter an artist name:", placeholder="e.g. Ed Sheeran")
    
    if search_artist and st.button("Search", type="primary"):
        with st.spinner(f"Finding artists similar to {search_artist}..."):
            # First, find the artist's genre/type
            performer_id = search_seatgeek_performer(search_artist)
            
            if performer_id:
                # Get events featuring this artist
                url = "https://api.seatgeek.com/2/events"
                params = {
                    "client_id": SEATGEEK_CLIENT_ID,
                    "performers.id": performer_id,
                    "per_page": 1
                }
                
                try:
                    response = requests.get(url, params=params, timeout=10)
                    if response.status_code == 200:
                        events = response.json().get('events', [])
                        
                        if events and events[0].get('taxonomies'):
                            # Get the genre/taxonomy
                            taxonomy = events[0]['taxonomies'][0]['name']
                            
                            # Now search for similar concerts in that genre
                            similar_url = "https://api.seatgeek.com/2/events"
                            similar_params = {
                                "client_id": SEATGEEK_CLIENT_ID,
                                "taxonomies.name": taxonomy,
                                "venue.city": "Austin",
                                "venue.state": "TX",
                                "per_page": 15,
                                "sort": "score.desc"
                            }
                            
                            similar_response = requests.get(similar_url, params=similar_params, timeout=10)
                            if similar_response.status_code == 200:
                                similar_events = similar_response.json().get('events', [])
                                
                                # Extract unique artists
                                similar_artists = {}
                                for event in similar_events:
                                    for performer in event.get('performers', []):
                                        artist_name = performer.get('name')
                                        if artist_name and artist_name.lower() != search_artist.lower():
                                            if artist_name not in similar_artists:
                                                similar_artists[artist_name] = {
                                                    'image': performer.get('image'),
                                                    'id': performer.get('id'),
                                                    'event_count': 1
                                                }
                                            else:
                                                similar_artists[artist_name]['event_count'] += 1
                                
                                if similar_artists:
                                    st.success(f"Found {len(similar_artists)} similar artists in {taxonomy}!")
                                    
                                    # Display in grid
                                    cols = st.columns(3)
                                    for i, (name, data) in enumerate(list(similar_artists.items())[:12]):
                                        with cols[i % 3]:
                                            if data['image']:
                                                st.image(data['image'], use_container_width=True)
                                            st.markdown(f"**{name}**")
                                            st.caption(f"{data['event_count']} event{'s' if data['event_count'] > 1 else ''} in Austin")
                                            
                                            if st.button("🔍 Find Shows", key=f"find_{data['id']}_{i}"):
                                                st.info(f"Search for '{name}' in the Discover Concerts page!")
                                            st.markdown("---")
                                else:
                                    st.info(f"No similar {taxonomy} artists found in Austin right now")
                        else:
                            st.warning("Couldn't determine artist genre. Try a different artist!")
                except Exception as e:
                    st.error(f"Error: {str(e)}")
            else:
                st.warning(f"Couldn't find '{search_artist}' on SeatGeek. Try a different spelling!")
    
    # Show popular artists as suggestions
    if not search_artist:
        st.markdown("### 💡 Try searching for:")
        suggestions = ["Taylor Swift", "Billie Eilish", "The Weeknd", "Drake", "Ed Sheeran", "Bad Bunny"]
        cols = st.columns(3)
        for i, artist in enumerate(suggestions):
            with cols[i % 3]:
                if st.button(f"🎤 {artist}", key=f"suggest_{i}", use_container_width=True):
                    st.rerun()

# ==================== SIDEBAR ====================
with st.sidebar:
    st.markdown("### 🎯 Discovery Stats")
    st.metric("Artists You Like", len(get_user_liked_artists()))
    
    saved_concerts = supabase.table("concerts_discovered").select("event_id").eq("user_id", user.id).execute()
    st.metric("Concerts Saved", len(saved_concerts.data))
