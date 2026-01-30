"""
Demo Mode Data for The Setlist

Provides mock data for demonstrations when API keys are unavailable.
Enable demo mode by setting DEMO_MODE=true in environment or secrets.
"""

import random
from datetime import datetime, timedelta

# Sample artists for demo
DEMO_ARTISTS = [
    {"name": "Arctic Monkeys", "genres": ["rock", "indie rock", "alternative"], "followers": 25000000, "image": "https://i.scdn.co/image/ab6761610000e5eb7da39dea0a72f581535fb11f"},
    {"name": "Tame Impala", "genres": ["psychedelic rock", "indie", "synth-pop"], "followers": 12000000, "image": "https://i.scdn.co/image/ab6761610000e5eb5a9b4a1e7b36b2a3f0e7e8d9"},
    {"name": "The 1975", "genres": ["pop rock", "indie pop", "alternative"], "followers": 8500000, "image": "https://i.scdn.co/image/ab6761610000e5eb1234567890abcdef12345678"},
    {"name": "Khruangbin", "genres": ["funk", "psychedelic", "world"], "followers": 3200000, "image": "https://i.scdn.co/image/ab6761610000e5ebabcdef1234567890abcdef12"},
    {"name": "Japanese Breakfast", "genres": ["indie pop", "dream pop", "indie rock"], "followers": 1800000, "image": "https://i.scdn.co/image/ab6761610000e5eb0987654321fedcba09876543"},
    {"name": "Turnstile", "genres": ["hardcore punk", "post-hardcore", "alternative"], "followers": 950000, "image": "https://i.scdn.co/image/ab6761610000e5ebfedcba0987654321fedcba09"},
    {"name": "boygenius", "genres": ["indie rock", "folk rock", "alternative"], "followers": 2100000, "image": "https://i.scdn.co/image/ab6761610000e5eb1122334455667788aabbccdd"},
    {"name": "Fontaines D.C.", "genres": ["post-punk", "rock", "indie"], "followers": 1200000, "image": "https://i.scdn.co/image/ab6761610000e5ebaabbccdd11223344556677"},
    {"name": "Mitski", "genres": ["indie rock", "art pop", "indie pop"], "followers": 4500000, "image": "https://i.scdn.co/image/ab6761610000e5eb5566778899aabbccddeeff00"},
    {"name": "Mac DeMarco", "genres": ["indie rock", "jangle pop", "slacker rock"], "followers": 5800000, "image": "https://i.scdn.co/image/ab6761610000e5eb99aabbccddeeff0011223344"},
]

# Demo venues in Austin
DEMO_VENUES = [
    {"name": "ACL Live at The Moody Theater", "address": "310 W Willie Nelson Blvd", "city": "Austin", "state": "TX"},
    {"name": "Stubb's BBQ", "address": "801 Red River St", "city": "Austin", "state": "TX"},
    {"name": "Emo's Austin", "address": "2015 E Riverside Dr", "city": "Austin", "state": "TX"},
    {"name": "The Parish", "address": "214 E 6th St", "city": "Austin", "state": "TX"},
    {"name": "Mohawk", "address": "912 Red River St", "city": "Austin", "state": "TX"},
    {"name": "Scoot Inn", "address": "1308 E 4th St", "city": "Austin", "state": "TX"},
    {"name": "Empire Control Room", "address": "606 E 7th St", "city": "Austin", "state": "TX"},
    {"name": "3TEN ACL Live", "address": "310 W Willie Nelson Blvd", "city": "Austin", "state": "TX"},
]


def generate_demo_concerts(num_concerts: int = 20, user_id: str = "demo-user") -> list:
    """Generate mock concert data for demo mode."""
    concerts = []
    base_date = datetime.now()
    
    for i in range(num_concerts):
        artist = random.choice(DEMO_ARTISTS)
        venue = random.choice(DEMO_VENUES)
        
        # Generate date within next 6 months
        days_ahead = random.randint(7, 180)
        concert_date = base_date + timedelta(days=days_ahead)
        
        # Random time between 7pm and 10pm
        hour = random.choice([19, 20, 21, 22])
        
        # Random price range
        min_price = random.choice([25, 35, 45, 55, 65, 75])
        max_price = min_price + random.choice([20, 30, 40, 50])
        
        concert = {
            "user_id": user_id,
            "event_id": f"demo_{i}_{random.randint(1000, 9999)}",
            "artist_name": artist["name"],
            "event_name": f"{artist['name']} Live in Austin",
            "venue_name": venue["name"],
            "venue_address": venue["address"],
            "city": venue["city"],
            "state": venue["state"],
            "date": concert_date.strftime("%Y-%m-%d"),
            "time": f"{hour}:00:00",
            "ticket_url": "https://example.com/tickets",
            "min_price": min_price,
            "max_price": max_price,
            "image_url": artist["image"],
            "priority_tier": random.choice(["HIGH", "MEDIUM", "LOW"]),
            "source": random.choice(["ticketmaster", "seatgeek"])
        }
        concerts.append(concert)
    
    # Sort by date
    concerts.sort(key=lambda x: x["date"])
    return concerts


def generate_demo_preferences(user_id: str = "demo-user") -> dict:
    """Generate mock user preferences for demo mode."""
    artists = [a["name"] for a in DEMO_ARTISTS]
    random.shuffle(artists)
    
    # Split into liked and disliked
    split_point = len(artists) // 2
    liked = artists[:split_point]
    disliked = artists[split_point:]
    
    return {
        "liked": liked,
        "disliked": disliked,
        "swipe_history": []
    }


def get_demo_artist_info(artist_name: str) -> dict:
    """Get demo artist info by name."""
    for artist in DEMO_ARTISTS:
        if artist["name"].lower() == artist_name.lower():
            return {
                "name": artist["name"],
                "image": artist["image"],
                "genres": artist["genres"],
                "popularity": random.randint(60, 95),
                "followers": artist["followers"],
                "spotify_url": f"https://open.spotify.com/artist/demo",
                "spotify_id": f"demo_{artist['name'].lower().replace(' ', '_')}"
            }
    return None


def get_demo_top_tracks(artist_name: str) -> list:
    """Generate demo top tracks for an artist."""
    track_templates = [
        "Midnight Dreams", "Electric Soul", "Neon Lights", "Ocean Drive",
        "Summer Haze", "City Lights", "Velvet Sky", "Golden Hour",
        "Moonlit Road", "Crystal Waters"
    ]
    
    tracks = []
    for i, track_name in enumerate(track_templates[:5]):
        tracks.append({
            "name": f"{track_name}",
            "artist": artist_name,
            "preview_url": None,  # No preview in demo
            "album_image": None,
            "spotify_url": "https://open.spotify.com/track/demo",
            "album_name": f"Album {i // 2 + 1}"
        })
    
    return tracks


def get_demo_friends() -> list:
    """Generate demo friends list."""
    return [
        {"id": "demo-friend-1", "username": "music_lover_42", "email": "demo1@example.com"},
        {"id": "demo-friend-2", "username": "concert_king", "email": "demo2@example.com"},
        {"id": "demo-friend-3", "username": "indie_vibes", "email": "demo3@example.com"},
    ]


def get_demo_messages(user_id: str, friend_id: str) -> list:
    """Generate demo conversation messages."""
    messages = [
        {"sender_id": friend_id, "receiver_id": user_id, "message": "Hey! Did you see Arctic Monkeys is coming?", "read": True, "created_at": "2024-01-15T10:30:00Z"},
        {"sender_id": user_id, "receiver_id": friend_id, "message": "Yes!! I already got tickets!", "read": True, "created_at": "2024-01-15T10:35:00Z"},
        {"sender_id": friend_id, "receiver_id": user_id, "message": "Nice! Want to go together?", "read": True, "created_at": "2024-01-15T10:40:00Z"},
        {"sender_id": user_id, "receiver_id": friend_id, "message": "Definitely! Let's do it 🎸", "read": True, "created_at": "2024-01-15T10:45:00Z"},
    ]
    return messages


# Demo mode check
def is_demo_mode() -> bool:
    """Check if demo mode is enabled."""
    import streamlit as st
    import os
    
    # Check environment variable first
    if os.environ.get("DEMO_MODE", "").lower() == "true":
        return True
    
    # Check Streamlit secrets
    try:
        return st.secrets.get("demo_mode", False)
    except:
        return False


class DemoUser:
    """Mock user object for demo mode."""
    def __init__(self):
        self.id = "demo-user-id"
        self.email = "demo@thesetlist.app"
