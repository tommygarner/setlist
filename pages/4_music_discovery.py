import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
from supabase import create_client, Client
import random

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
    headers = {
        'Accept': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    params = {
        "client_id": SEATGEEK_CLIENT_ID,
        "q": artist_name,
        "per_page": 1
    }
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('performers'):
                return data['performers'][0]['id']
    except:
        pass
    return None

def display_event_card(event, score=None):
    """Display a concert event card"""
    unique_id = f"{event['id']}_{random.randint(1000, 9999)}"
    
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
                st.progress(min(score, 100) / 100)
                st.caption(f"{int(min(score, 100))}% match")
        
        with col3:
            if st.button("🎟️ Tickets", key=f"tickets_{unique_id}", use_container_width=True):
                st.link_button("Open SeatGeek", event['url'], use_container_width=True, key=f"link_{unique_id}")
            
            if st.button("💾 Save", key=f"save_{unique_id}", use_container_width=True):
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
                try:
                    supabase.table("concerts_discovered").upsert(concert_data, on_conflict='user_id,event_id').execute()
                    st.success("✅ Saved!")
                except:
                    st.success("✅ Saved!")
        
        st.markdown("---")

# ==================== MAIN UI ====================
st.title("✨ Music Discovery")
st.markdown("Discover new concerts based on your music taste")

# Tabs for different discovery modes
tab1, tab2, tab3, tab4 = st.tabs(["🎵 For You", "🔥 This Weekend", "🎲 Surprise Me", "🎯 Similar Artists"])

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
            url = "https://api.seatgeek.com/2/events"
            headers = {
                'Accept': 'application/json',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            params = {
                "client_id": SEATGEEK_CLIENT_ID,
                "venue.city": "Austin",
                "venue.state": "TX",
                "taxonomies.name": "concert",
                "per_page": 50,
                "sort": "datetime_local.asc"
            }
            
            try:
                response = requests.get(url, params=params, headers=headers, timeout=15)
                
                if response.status_code == 200:
                    all_events = response.json().get('events', [])
                    
                    if not all_events:
                        st.info("No concerts found in Austin right now. Check 'This Weekend' or 'Similar Artists'!")
                    else:
                        scored_events = []
                        liked_artists_lower = [a.lower() for a in liked_artists]
                        
                        for event in all_events:
                            score = 0
                            event_artists = [p['name'].lower() for p in event.get('performers', []) if p.get('name')]
                            
                            for artist in liked_artists_lower:
                                if artist in event_artists:
                                    score += 100
                            
                            for artist in liked_artists_lower:
                                for word in artist.split():
                                    if len(word) > 3:
                                        for event_artist in event_artists:
                                            if word in event_artist:
                                                score += 10
                            
                            score += event.get('score', 0) * 0.1
                            
                            if score > 0:
                                scored_events.append({
                                    'event': event,
                                    'score': score
                                })
                        
                        scored_events.sort(key=lambda x: x['score'], reverse=True)
                        
                        if scored_events:
                            st.success(f"🎉 Found {len(scored_events)} concerts recommended for you!")
                            st.caption("Showing concerts sorted by how well they match your taste")
                            
                            for item in scored_events[:15]:
                                event = item['event']
                                score = min(item['score'], 100)
                                display_event_card(event, score)
                        else:
                            st.info("No matching concerts found. Try 'This Weekend' or 'Similar Artists'!")
                
                elif response.status_code == 406:
                    st.error("⚠️ API returned 406 error. Try refreshing the page.")
                else:
                    st.error(f"API Error: {response.status_code}")
                    
            except requests.Timeout:
                st.error("⏱️ Request timed out. Try again!")
            except Exception as e:
                st.error(f"Error: {str(e)}")

# ==================== TAB 2: THIS WEEKEND ====================
with tab2:
    st.subheader("🔥 This Weekend in Austin")
    st.caption("Concerts happening Friday - Sunday")
    
    if st.button("🔄 Refresh Weekend Events", key="refresh_weekend"):
        st.rerun()
    
    with st.spinner("Loading weekend concerts..."):
        today = datetime.now()
        days_until_friday = (4 - today.weekday()) % 7
        if days_until_friday == 0 and today.weekday() >= 4:
            days_until_friday = 0
        
        friday = today + timedelta(days=days_until_friday)
        sunday = friday + timedelta(days=2)
        
        url = "https://api.seatgeek.com/2/events"
        headers = {
            'Accept': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        params = {
            "client_id": SEATGEEK_CLIENT_ID,
            "venue.city": "Austin",
            "venue.state": "TX",
            "taxonomies.name": "concert",
            "datetime_local.gte": friday.strftime("%Y-%m-%d"),
            "datetime_local.lte": sunday.strftime("%Y-%m-%d"),
            "per_page": 50
        }
        
        try:
            response = requests.get(url, params=params, headers=headers, timeout=10)
            
            if response.status_code == 200:
                weekend_events = response.json().get('events', [])
                
                if weekend_events:
                    st.success(f"Found {len(weekend_events)} concerts this weekend!")
                    
                    for event in weekend_events:
                        display_event_card(event)
                else:
                    st.info("No concerts found this weekend. Check back later!")
            
            elif response.status_code == 406:
                st.error("⚠️ API returned 406 error. Try refreshing the page.")
            else:
                st.error(f"API Error: {response.status_code}")
                
        except Exception as e:
            st.error(f"Error loading weekend events: {str(e)}")

# ==================== TAB 3: SURPRISE ME ====================
with tab3:
    st.subheader("🎲 Surprise Me!")
    st.caption("Discover something completely random")
    
    if st.button("🎲 Find a Random Concert", type="primary", use_container_width=True):
        with st.spinner("Finding a surprise concert..."):
            url = "https://api.seatgeek.com/2/events"
            headers = {
                'Accept': 'application/json',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            params = {
                "client_id": SEATGEEK_CLIENT_ID,
                "venue.city": "Austin",
                "venue.state": "TX",
                "taxonomies.name": "concert",
                "per_page": 25,
                "sort": "score.desc"
            }
            
            try:
                response = requests.get(url, params=params, headers=headers, timeout=10)
                if response.status_code == 200:
                    events = response.json().get('events', [])
                    if events:
                        random_event = random.choice(events)
                        st.success("🎉 Here's a concert you might enjoy:")
                        display_event_card(random_event)
                    else:
                        st.info("No concerts found. Try again!")
                else:
                    st.error(f"API Error: {response.status_code}")
            except Exception as e:
                st.error(f"Error: {str(e)}")

# ==================== TAB 4: SIMILAR ARTISTS ====================
with tab4:
    st.subheader("🎯 Artists You Might Like")
    st.caption("Based on artists you've already liked")
    
    liked_artists = get_user_liked_artists()
    
    if not liked_artists:
        st.info("👆 Like some artists first to get personalized recommendations!")
        if st.button("🎸 Go to Artist Swipe", key="swipe2"):
            st.switch_page("pages/3_artist_swipe.py")
    else:
        st.write(f"Finding artists similar to: **{', '.join(liked_artists[:3])}**{' and more...' if len(liked_artists) > 3 else ''}")
        
        if st.button("✨ Get Personalized Recommendations", type="primary", use_container_width=True):
            with st.spinner("Finding artists you'll love..."):
                url = "https://api.seatgeek.com/2/events"
                headers = {
                    'Accept': 'application/json',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                params = {
                    "client_id": SEATGEEK_CLIENT_ID,
                    "venue.city": "Austin",
                    "venue.state": "TX",
                    "taxonomies.name": "concert",
                    "per_page": 50,
                    "sort": "score.desc"
                }
                
                try:
                    response = requests.get(url, params=params, headers=headers, timeout=10)
                    
                    if response.status_code == 200:
                        events = response.json().get('events', [])
                        
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
                            st.success(f"🎉 Found {len(new_artists)} NEW artists you haven't discovered yet!")
                            st.caption("These are artists with Austin concerts that you haven't swiped on yet")
                            
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
                                            st.success(f"✅ Added {name}!")
                                    
                                    st.markdown("")
                        else:
                            st.info("🎊 You've already discovered all available artists!")
                    
                    elif response.status_code == 406:
                        st.error("⚠️ API returned 406 error. Try refreshing.")
                    else:
                        st.error(f"API Error: {response.status_code}")
                        
                except Exception as e:
                    st.error(f"Error: {str(e)}")
    
    if liked_artists:
        st.markdown("---")
        st.markdown("### 🔍 Quick Search")
        
        search_artist = st.text_input("Search for a specific artist:", placeholder="e.g. Taylor Swift", key="artist_search")
        
        if search_artist and st.button("Search", key="search_btn"):
            with st.spinner(f"Searching for {search_artist}..."):
                performer_id = search_seatgeek_performer(search_artist)
                
                if performer_id:
                    url = "https://api.seatgeek.com/2/events"
                    headers = {
                        'Accept': 'application/json',
                        'User-Agent': 'Mozilla/5.0'
                    }
                    params = {
                        "client_id": SEATGEEK_CLIENT_ID,
                        "performers.id": performer_id,
                        "per_page": 10
                    }
                    
                    try:
                        response = requests.get(url, params=params, headers=headers, timeout=10)
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
