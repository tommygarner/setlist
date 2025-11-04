# 🎵 The Setlist

**Your personalized concert planner**

AI-powered concert discovery that matches your music taste with upcoming shows in your city.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.9+-blue.svg)
![Streamlit](https://img.shields.io/badge/streamlit-1.28+-red.svg)

## ✨ Features

- 🎵 **Smart Artist Discovery**: Tinder-style swipe interface to build your music preferences
- 📊 **Personalized Dashboard**: Concert recommendations based on your taste
- 🎸 **Spotify Integration**: Auto-sync your favorite artists and listening history
- 🎟️ **Live Concert Data**: Real-time updates from Ticketmaster API
- 📝 **Concert Diary**: Track and review shows you've attended
- 👥 **Social Features**: Find friends attending the same concerts (coming soon)

## 🚀 Tech Stack

- **Frontend**: Streamlit
- **APIs**: Spotify Web API, Ticketmaster Discovery API
- **Data Processing**: Pandas, NumPy
- **Storage**: JSON, Excel (migrating to database)

## 📦 Installation

### Prerequisites
- Python 3.9 or higher
- Spotify API credentials
- Ticketmaster API key

### Setup

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/the-setlist.git
cd the-setlist
```

2. **Create virtual environment**
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Set up environment variables**
```bash
# Copy example env file
cp .env.example .env

# Edit .env and add your API keys
```

5. **Run the app**
```bash
streamlit run app.py
```

The app will open at `http://localhost:8501`

## 🔑 Getting API Keys

### Spotify API
1. Go to https://developer.spotify.com/dashboard
2. Create an app
3. Copy Client ID and Client Secret

### Ticketmaster API
1. Go to https://developer.ticketmaster.com
2. Sign up for a free account
3. Get your API key

## 📂 Project Structure

```
the-setlist/
├── app.py                    # Main Streamlit app
├── pages/                    # Multi-page app pages
│   └── artist_swipe.py      # Artist preference swipe interface
├── utils/                    # Helper functions (coming soon)
│   ├── spotify.py           # Spotify API integration
│   └── ticketmaster.py      # Ticketmaster API integration
├── notebooks/               # Jupyter notebooks
│   └── concert_scraper.ipynb # Concert data collection
├── data/                    # Data files (gitignored)
├── assets/                  # Images, CSS, etc.
├── .gitignore              # Git ignore rules
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

## 🎯 Roadmap

- [x] Concert discovery dashboard
- [x] Artist preference swipe interface
- [x] Spotify API integration
- [x] Ticketmaster data integration
- [ ] User authentication
- [ ] Database migration (PostgreSQL/Supabase)
- [ ] Friend system
- [ ] Concert diary with reviews
- [ ] Multi-city support
- [ ] Mobile app

## 🤝 Contributing

This is a personal project, but feedback and suggestions are welcome!

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 👤 Author

**[Your Name]**
- GitHub: [@yourusername](https://github.com/yourusername)
- LinkedIn: [Your Profile](https://linkedin.com/in/yourprofile)

---

**The Setlist** - Build your perfect lineup 🎸
