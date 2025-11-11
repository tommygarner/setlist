import streamlit as st
from supabase import create_client, Client
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import aiohttp
import asyncio
from datetime import datetime, timedelta
import time

st.set_page_config(page_title="🎤 Discover Concerts", page_icon="🎤", layout="wide")

# Initialize Supabase
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

# Token Refresh Function
def get_valid_spotify_token(user_id):
    """Get valid Spotify token, refreshing if expired"""
    try:
        profile = supabase.table("profiles").select("*").eq("id", user_id).execute()
        if not profile.data:
            return None
        
        user_data = profile.data[0]
        expires_at = user_data.get('spotify_token_expires_at')
        
        # Check if token is expired
        if expires_at:
            expires_datetime = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
            if datetime.now(expires_datetime.tzinfo) >= expires_datetime:
                # Token expired - refresh it
                st.info("🔄 Refreshing Spotify token...")
                auth_manager = SpotifyOAuth(
                    client_id=st.secrets["spotify"]["CLIENT_ID"],
                    client_secret=st.secrets["spotify"]["CLIENT_SECRET"],
                    redirect_uri=st.secrets["spotify"]["REDIRECT_URI"],
                    scope="user-library-read user-top-read"
                )
                
                refresh_token = user_data.get('spotify_refresh_token')
                if refresh_token:
                    token_info = auth_manager.refresh_access_token(refresh_token)
                    
                    # Update database with new token
                    new_expires = datetime.utcnow() + timedelta(seconds=token_info['expires_in'])
                    supabase.table("profiles").update({
                        "spotify_access_token": token_info['access_token'],
                        "spotify_token_expires_at": new_expires.isoformat()
                    }).eq("id", user_id).execute()
                    
                    return token_info['access_token']
        
        return user_data.get('spotify_access_token')
    except Exception as e:
        st.error(f"Token refresh error: {str(e)}")
        return None

# Spotify Functions
def get_user_liked_artists(sp, limit=None):
    """Get unique artists from user's liked songs"""
    artists = set()
    offset = 0
    
    progress_bar = st.progress(0)
    status = st.empty()
    
    while True:
        try:
            results = sp.current_user_saved_tracks(limit=50, offset=offset)
            
            if not results['items']:
                break
            
            for item in results['items']:
                track = item['track']
                if track and track.get('artists'):
                    for artist in track['artists']:
                        artists.add(artist['name'])
            
            status.text(f"Fetching liked songs... (found {len(artists)} unique artists so far)")
            offset += 50
            
            if limit and len(artists) >= limit:
                break
            
            if len(results['items']) < 50:
                break
        except Exception as e:
            st.warning(f"Error fetching songs at offset {offset}: {str(e)}")
            break
    
    progress_bar.empty()
    status.empty()
    
    return list(artists)

# Async Ticketmaster search
async def search_ticketmaster_async(session, artist_name, api_key, city, state_code, radius):
    """Async search for a single artist"""
    url = "https://app.ticketmaster.com/discovery/v2/events.json"
    params = {
        'apikey': api_key,
        'keyword': artist_name,
        'city': city,
        'stateCode': state_code,
        'radius': radius,
        'unit': 'miles',
        'classificationName': 'music',
        'sort': 'date,asc'
    }
    
    try:
        async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
            if response.status == 200:
                data = await response.json()
                return artist_name, data
            else:
                return artist_name, None
    except Exception:
        return artist_name, None

async def search_all_artists_async(artists, api_key, city, state_code, radius, progress_bar, status_text):
    """Search all artists"""
    concerts = []
    batch_size = 20  # Process 20 artists at once
    total = len(artists)
    
    async with aiohttp.ClientSession() as session:
        for i in range(0, total, batch_size):
            batch = artists[i:i + batch_size]
            
            # Create tasks for this batch
            tasks = [
                search_ticketmaster_async(session, artist, api_key, city, state_code, radius)
                for artist in batch
            ]
            
            # Wait for all tasks in batch to complete
            results = await asyncio.gather(*tasks)
            
            # Process results
            for artist_name, data in results:
                if data and '_embedded' in data and 'events' in data['_embedded']:
                    for event in data['_embedded']['events']:
                        concert = parse_concert_data(event, artist_name, user.id)
                        if concert:
                            concerts.append(concert)
            
            # Update progress
            progress = min((i + batch_size) / total, 1.0)
            progress_bar.progress(progress)
            status_text.text(f"Searched {min(i + batch_size, total)}/{total} artists... ({len(concerts)} concerts found)")
            
            # Small delay to respect rate limits
            await asyncio.sleep(0.5)
    
    return concerts

def parse_concert_data(event, artist_name, user_id):
    """Parse Ticketmaster event data"""
    try:
        venue = event.get('_embedded', {}).get('venues', [{}])[0]
        date = event.get('dates', {}).get('start', {}).get('localDate', '')
        time_str = event.get('dates', {}).get('start', {}).get('localTime', '')
        
        price_ranges = event.get('priceRanges', [])
        min_price = price_ranges[0].get('min', 0) if price_ranges else None
        max_price = price_ranges[0].get('max', 0) if price_ranges else None
        
        images = event.get('images', [])
        image_url = images[0]['url'] if images else None
        
        return {
            'user_id': user_id,
            'event_id': event.get('id'),
            'artist_name': artist_name,
            'event_name': event.get('name', ''),
            'venue_name': venue.get('name', ''),
            'venue_address': venue.get('address', {}).get('line1', ''),
            'city': venue.get('city', {}).get('name', ''),
            'state': venue.get('state', {}).get('stateCode', ''),
            'date': date,
            'time': time_str,
            'ticket_url': event.get('url', ''),
            'min_price': min_price,
            'max_price': max_price,
            'image_url': image_url,
            'priority_tier': 'MEDIUM',
            'source': 'ticketmaster'  # ADD THIS LINE
        }
    except Exception:
        return None

async def search_seatgeek_async(session, artist_name, client_id, city, state, radius):
    url = "https://api.seatgeek.com/2/events"
    params = {
        "client_id": client_id,
        "q": artist_name,
        "venue.city": city,
        "venue.state": state,
        "range": f"{radius}mi",
        "type": "concert",
        "per_page": 25
    }
    try:
        async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
            if response.status == 200:
                data = await response.json()
                return artist_name, data
            else:
                return artist_name, None
    except Exception:
        return artist_name, None

def parse_seatgeek_concert(event, user_id):
    try:
        performer = event.get('performers', [{}])[0]
        venue = event.get('venue', {})
        date_time = event.get('datetime_local', '')
        date, time_str = (date_time.split('T') + [''])[:2]
        stats = event.get('stats', {})
        return {
            'user_id': user_id,
            'event_id': f"sg_{event['id']}",
            'artist_name': performer.get('name', ''),
            'event_name': event.get('title', ''),
            'venue_name': venue.get('name', ''),
            'venue_address': venue.get('address', ''),
            'city': venue.get('city', ''),
            'state': venue.get('state', ''),
            'date': date,
            'time': time_str,
            'ticket_url': event.get('url', ''),
            'min_price': stats.get('lowest_price'),
            'max_price': stats.get('highest_price'),
            'image_url': performer.get('image'),
            'priority_tier': 'MEDIUM',
            'source': 'seatgeek'
        }
    except Exception:
        return None

async def search_both_apis_async(artists, tm_api_key, sg_client_id, city, state_code, radius, progress_bar, status_text):
    """Search both Ticketmaster AND SeatGeek for all artists in parallel"""
    all_concerts = []
    batch_size = 20
    total = len(artists)
    
    async with aiohttp.ClientSession() as session:
        for i in range(0, total, batch_size):
            batch = artists[i:i + batch_size]
            
            # Create tasks for BOTH Ticketmaster AND SeatGeek
            tm_tasks = [
                search_ticketmaster_async(session, artist, tm_api_key, city, state_code, radius)
                for artist in batch
            ]
            sg_tasks = [
                search_seatgeek_async(session, artist, sg_client_id, city, state_code, radius)
                for artist in batch
            ]
            
            # Run both API calls in parallel
            all_results = await asyncio.gather(*(tm_tasks + sg_tasks))
            
            # Split results back into TM and SG
            tm_results = all_results[:len(batch)]
            sg_results = all_results[len(batch):]
            
            # Process Ticketmaster results
            for artist_name, data in tm_results:
                if data and '_embedded' in data and 'events' in data['_embedded']:
                    for event in data['_embedded']['events']:
                        concert = parse_concert_data(event, artist_name, user.id)
                        if concert:
                            concert['source'] = 'ticketmaster'  # Tag source
                            all_concerts.append(concert)
            
            # Process SeatGeek results
            for artist_name, data in sg_results:
                if data and 'events' in data:
                    for event in data['events']:
                        concert = parse_seatgeek_concert(event, user.id)
                        if concert:
                            all_concerts.append(concert)
            
            # Update progress
            progress = min((i + batch_size) / total, 1.0)
            progress_bar.progress(progress)
            status_text.text(f"Searched {min(i + batch_size, total)}/{total} artists... ({len(all_concerts)} concerts found from both sources)")
            
            # Small delay to respect rate limits
            await asyncio.sleep(0.5)
    
    # Deduplicate concerts (same show on both platforms)
    deduplicated = deduplicate_concerts(all_concerts)
    status_text.text(f"✅ Found {len(all_concerts)} total concerts, {len(deduplicated)} unique after deduplication")
    
    return deduplicated

def deduplicate_concerts(concerts):
    """Remove duplicate concerts based on artist, venue, and date"""
    seen = {}
    unique = []
    
    for concert in concerts:
        # Create key from artist + venue + date
        key = (
            concert['artist_name'].lower().strip(),
            concert['venue_name'].lower().strip(),
            concert['date']
        )
        
        if key not in seen:
            seen[key] = True
            unique.append(concert)
        # If duplicate, keep the one with better pricing info
        else:
            existing = next((c for c in unique if (
                c['artist_name'].lower().strip(),
                c['venue_name'].lower().strip(),
                c['date']
            ) == key), None)
            
            if existing and concert.get('min_price') and not existing.get('min_price'):
                # Replace with one that has pricing
                unique.remove(existing)
                unique.append(concert)
    
    return unique



# Main Page
st.title("🎤 Discover Concerts")
st.write("Find concerts from your favorite Spotify artists")

# Configuration
st.sidebar.header("🎯 Search Settings")
city = st.sidebar.text_input("City", value=st.secrets["ticketmaster"]["CITY"])
state = st.sidebar.text_input("State Code", value=st.secrets["ticketmaster"]["STATE_CODE"])
radius = st.sidebar.slider("Search Radius (miles)", 10, 200, int(st.secrets["ticketmaster"]["SEARCH_RADIUS"]))

# Discovery Button
if st.button("🔍 Discover Concerts", type="primary", use_container_width=True):
    st.session_state.discovering = True

if st.session_state.get('discovering', False):
    try:
        # Step 1: Get Spotify artists
        st.subheader("Step 1: Fetching Your Liked Artists")
        
        # Get valid token (with auto-refresh)
        access_token = get_valid_spotify_token(user.id)
        
        if not access_token:
            st.error("❌ Spotify not connected! Please connect your Spotify first.")
            if st.button("🎵 Go to Connect Spotify"):
                st.switch_page("pages/1_connect_spotify.py")
            st.session_state.discovering = False
            st.stop()
        
        # Create Spotify client with refreshed token
        sp = spotipy.Spotify(auth=access_token)
        
        artists = get_user_liked_artists(sp, limit=None)  # No limit - get ALL
        st.success(f"✅ Found {len(artists)} unique artists!")
        
        # Step 2: Search BOTH Ticketmaster AND SeatGeek (ASYNC!)
        st.subheader("Step 2: Searching for Concerts (Ticketmaster + SeatGeek)")
        st.info("⚡ Searching both Ticketmaster and SeatGeek for maximum coverage!")
        
        progress = st.progress(0)
        status = st.empty()
        
        # Run async search for BOTH APIs in parallel
        concerts_found = asyncio.run(
            search_both_apis_async(
                artists,
                st.secrets["ticketmaster"]["API_KEY"],
                st.secrets["seatgeek"]["CLIENT_ID"],
                city,
                state,
                str(radius),
                progress,
                status
            )
        )
        
        progress.empty()
        status.empty()
        
        # Step 3: Save to Database
        st.subheader("Step 3: Saving Concerts")
        
        if concerts_found:
            # Clear old concerts
            supabase.table("concerts_discovered").delete().eq("user_id", user.id).execute()
            
            # Insert new concerts
            saved_count = 0
            for concert in concerts_found:
                try:
                    supabase.table("concerts_discovered").upsert(concert, on_conflict='event_id').execute()
                    saved_count += 1
                except Exception as e:
                    pass  # Silently skip errors
            
            st.success(f"✅ Saved {saved_count} concerts!")
            st.balloons()
        else:
            st.info(f"No concerts found within {radius} miles of {city}, {state}. Try increasing the search radius.")
        
        st.session_state.discovering = False
        st.rerun()
        
    except Exception as e:
        st.error(f"Error during discovery: {str(e)}")
        import traceback
        st.code(traceback.format_exc())
        st.session_state.discovering = False

# Display Saved Concerts
st.divider()

# Load concerts
concerts = supabase.table("concerts_discovered").select("*").eq("user_id", user.id).order("date").execute()

if concerts.data:
    # FILTERS
    st.subheader("🔍 Filter Concerts")
    
    filter_col1, filter_col2, filter_col3 = st.columns(3)
    
    with filter_col1:
        date_filter = st.selectbox("Date Range", [
            "All Dates",
            "This Month",
            "Next 3 Months",
            "Next 6 Months",
            "2025 Only",
            "2026 Only"
        ])
    
    with filter_col2:
        venue_options = ["All Venues"] + sorted(list(set([c['venue_name'] for c in concerts.data])))
        venue_filter = st.selectbox("Venue", venue_options)
    
    with filter_col3:
        sort_by = st.selectbox("Sort By", ["Date (Earliest)", "Date (Latest)", "Artist Name"])
    
    # Apply filters
    filtered_concerts = concerts.data
    
    # Date filter
    now = datetime.now()
    
    if date_filter == "This Month":
        end_date = (now.replace(day=1) + timedelta(days=32)).replace(day=1)
        filtered_concerts = [c for c in filtered_concerts if c['date'] and c['date'] < end_date.strftime("%Y-%m-%d")]
    elif date_filter == "Next 3 Months":
        end_date = now + timedelta(days=90)
        filtered_concerts = [c for c in filtered_concerts if c['date'] and c['date'] < end_date.strftime("%Y-%m-%d")]
    elif date_filter == "Next 6 Months":
        end_date = now + timedelta(days=180)
        filtered_concerts = [c for c in filtered_concerts if c['date'] and c['date'] < end_date.strftime("%Y-%m-%d")]
    elif date_filter == "2025 Only":
        filtered_concerts = [c for c in filtered_concerts if c['date'] and c['date'].startswith("2025")]
    elif date_filter == "2026 Only":
        filtered_concerts = [c for c in filtered_concerts if c['date'] and c['date'].startswith("2026")]
    
    # Venue filter
    if venue_filter != "All Venues":
        filtered_concerts = [c for c in filtered_concerts if c['venue_name'] == venue_filter]
    
    # Sort
    if sort_by == "Date (Earliest)":
        filtered_concerts = sorted(filtered_concerts, key=lambda x: x['date'] or "9999")
    elif sort_by == "Date (Latest)":
        filtered_concerts = sorted(filtered_concerts, key=lambda x: x['date'] or "0000", reverse=True)
    elif sort_by == "Artist Name":
        filtered_concerts = sorted(filtered_concerts, key=lambda x: x['artist_name'])
    
    st.info(f"Showing {len(filtered_concerts)} of {len(concerts.data)} concerts")
    
    st.divider()
    st.subheader("🎸 Your Discovered Concerts")
    
    # Display filtered concerts
    for concert in filtered_concerts:
        with st.container():
            col1, col2, col3 = st.columns([3, 2, 1])
            
            with col1:
                st.markdown(f"### {concert['event_name']}")
                st.write(f"🎤 **{concert['artist_name']}**")
                st.write(f"📍 {concert['venue_name']}, {concert['city']}, {concert['state']}")
            
            with col2:
                st.write(f"📅 **Date:** {concert['date']}")
                if concert['time']:
                    st.write(f"🕐 **Time:** {concert['time']}")
                if concert['min_price'] and concert['max_price']:
                    st.write(f"💰 **Price:** ${concert['min_price']} - ${concert['max_price']}")
            
            with col3:
                if concert['ticket_url']:
                    st.link_button("🎟️ Get Tickets", concert['ticket_url'])
            
            st.divider()
else:
    st.info("No concerts discovered yet. Click the button above to start discovering!")
