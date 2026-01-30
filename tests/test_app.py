"""
Tests for The Setlist Application

Run with: pytest tests/ -v
"""

import pytest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestDemoData:
    """Tests for demo data generation."""
    
    def test_generate_demo_concerts(self):
        """Test that demo concerts are generated correctly."""
        from utils.demo_data import generate_demo_concerts
        
        concerts = generate_demo_concerts(num_concerts=10)
        
        assert len(concerts) == 10
        assert all("artist_name" in c for c in concerts)
        assert all("venue_name" in c for c in concerts)
        assert all("date" in c for c in concerts)
        assert all("event_id" in c for c in concerts)
    
    def test_demo_concerts_have_required_fields(self):
        """Test that demo concerts have all required fields."""
        from utils.demo_data import generate_demo_concerts
        
        required_fields = [
            "user_id", "event_id", "artist_name", "event_name",
            "venue_name", "city", "state", "date"
        ]
        
        concerts = generate_demo_concerts(num_concerts=5)
        
        for concert in concerts:
            for field in required_fields:
                assert field in concert, f"Missing field: {field}"
    
    def test_demo_concerts_sorted_by_date(self):
        """Test that demo concerts are sorted by date."""
        from utils.demo_data import generate_demo_concerts
        
        concerts = generate_demo_concerts(num_concerts=10)
        dates = [c["date"] for c in concerts]
        
        assert dates == sorted(dates), "Concerts should be sorted by date"
    
    def test_generate_demo_preferences(self):
        """Test that demo preferences are generated correctly."""
        from utils.demo_data import generate_demo_preferences
        
        prefs = generate_demo_preferences()
        
        assert "liked" in prefs
        assert "disliked" in prefs
        assert isinstance(prefs["liked"], list)
        assert isinstance(prefs["disliked"], list)
        assert len(prefs["liked"]) > 0
    
    def test_get_demo_artist_info(self):
        """Test getting demo artist info."""
        from utils.demo_data import get_demo_artist_info
        
        # Test with known artist
        info = get_demo_artist_info("Arctic Monkeys")
        
        assert info is not None
        assert info["name"] == "Arctic Monkeys"
        assert "genres" in info
        assert "followers" in info
    
    def test_get_demo_artist_info_not_found(self):
        """Test that unknown artist returns None."""
        from utils.demo_data import get_demo_artist_info
        
        info = get_demo_artist_info("Unknown Artist XYZ")
        
        assert info is None
    
    def test_get_demo_top_tracks(self):
        """Test getting demo top tracks."""
        from utils.demo_data import get_demo_top_tracks
        
        tracks = get_demo_top_tracks("Test Artist")
        
        assert len(tracks) == 5
        assert all("name" in t for t in tracks)
        assert all("artist" in t for t in tracks)
    
    def test_get_demo_friends(self):
        """Test getting demo friends."""
        from utils.demo_data import get_demo_friends
        
        friends = get_demo_friends()
        
        assert len(friends) >= 1
        assert all("id" in f for f in friends)
        assert all("username" in f for f in friends)
    
    def test_demo_user_class(self):
        """Test DemoUser class."""
        from utils.demo_data import DemoUser
        
        user = DemoUser()
        
        assert hasattr(user, "id")
        assert hasattr(user, "email")
        assert user.id is not None


class TestAppStructure:
    """Tests for application structure and imports."""
    
    def test_app_file_exists(self):
        """Test that main app.py exists."""
        app_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app.py")
        assert os.path.exists(app_path), "app.py should exist"
    
    def test_pages_directory_exists(self):
        """Test that pages directory exists."""
        pages_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "pages")
        assert os.path.isdir(pages_path), "pages/ directory should exist"
    
    def test_required_pages_exist(self):
        """Test that all required page files exist."""
        pages_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "pages")
        
        required_pages = [
            "1_connect_spotify.py",
            "2_discover_concerts.py",
            "3_artist_swipe.py",
        ]
        
        for page in required_pages:
            page_file = os.path.join(pages_path, page)
            assert os.path.exists(page_file), f"Page {page} should exist"
    
    def test_requirements_file_exists(self):
        """Test that requirements.txt exists."""
        req_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "requirements.txt")
        assert os.path.exists(req_path), "requirements.txt should exist"
    
    def test_dockerfile_exists(self):
        """Test that Dockerfile exists."""
        dockerfile_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Dockerfile")
        assert os.path.exists(dockerfile_path), "Dockerfile should exist"


class TestDataValidation:
    """Tests for data validation logic."""
    
    def test_concert_date_format(self):
        """Test that concert dates are in correct format."""
        from utils.demo_data import generate_demo_concerts
        import re
        
        concerts = generate_demo_concerts(num_concerts=5)
        date_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}$")
        
        for concert in concerts:
            assert date_pattern.match(concert["date"]), f"Invalid date format: {concert['date']}"
    
    def test_concert_prices_valid(self):
        """Test that concert prices are valid."""
        from utils.demo_data import generate_demo_concerts
        
        concerts = generate_demo_concerts(num_concerts=10)
        
        for concert in concerts:
            if concert.get("min_price") and concert.get("max_price"):
                assert concert["min_price"] > 0, "Min price should be positive"
                assert concert["max_price"] >= concert["min_price"], "Max price should be >= min price"


# Integration test placeholder
class TestIntegration:
    """Integration tests (require API keys - skipped in CI)."""
    
    @pytest.mark.skip(reason="Requires API keys - run manually")
    def test_spotify_connection(self):
        """Test Spotify API connection."""
        pass
    
    @pytest.mark.skip(reason="Requires API keys - run manually")
    def test_supabase_connection(self):
        """Test Supabase connection."""
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
