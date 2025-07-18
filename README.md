# 🎭 Kargin Video Archive

A comprehensive search and discovery platform for Kargin comedy episodes, built with Streamlit and powered by AI-assisted fuzzy search.

## 🚀 Quick Access

- **🤖 Telegram Bot**: [@KarginSearchBot](https://t.me/KarginSearchBot)
- **🌐 Web App**: [https://kargin.streamlit.app/](https://kargin.streamlit.app/)

## 📱 Features

### 🔍 Smart Search
- **Fuzzy Text Search**: Find episodes even with typos or partial matches
- **Multi-field Search**: Search through titles, dialogue, actors, and roles
- **Advanced Algorithms**: Levenshtein, Token Sort, Token Set, and Partial matching
- **Intelligent Filtering**: By location, language, and actor count

### 🤖 Telegram Bot
- **Instant Search**: Search episodes directly from Telegram
- **Multiple Commands**: `/search`, `/search_title`, `/search_actors`, `/search_text`
- **Random Episodes**: Get random episode suggestions with `/random`
- **Archive Stats**: View collection statistics with `/stats`
- **Armenian Support**: Full support for Armenian text search

### 📊 Data Analytics
- **Visual Statistics**: Interactive charts and graphs
- **Episode Insights**: Trends, patterns, and distribution analysis
- **Actor Analytics**: Most featured performers and collaboration patterns

### 🎲 Random Discovery
- **Random Episodes**: Discover episodes you might have missed
- **Visual Browsing**: Thumbnail previews and quick access

## 🛠️ Installation Options

### Core Features Only (No YouTube)
```bash
pip install -r requirements-core.txt
streamlit run Home.py
```

### Full Installation (All Features)
```bash
pip install -r requirements.txt
streamlit run Home.py
```

### Interactive Setup
```bash
install_optional.bat
```

## 🔧 Optional Features

The app supports optional YouTube features:
- **Video Thumbnails**: Preview images from YouTube
- **Video Metadata**: Views, likes, duration, publish date
- **Embedded Player**: Watch videos directly in the app

If pytubefix is not installed, the app gracefully falls back to core functionality with custom placeholders.

## 🤖 Telegram Bot Setup

1. Message [@BotFather](https://t.me/BotFather) on Telegram
2. Create a new bot with `/newbot`
3. Get your bot token
4. Set environment variable: `TELEGRAM_BOT_TOKEN=your_token`
5. Run: `python telegram_bot.py`

See [TELEGRAM_BOT_README.md](TELEGRAM_BOT_README.md) for detailed setup instructions.

## 📁 Project Structure

```
Kargin_project/
├── Home.py                      # Main Streamlit app
├── pages/                       # Streamlit pages
│   ├── 1_Search_Episodes.py     # Search functionality
│   ├── 2_Data_Analysis.py       # Analytics dashboard
│   ├── 3_Random_Videos.py       # Random episode discovery
│   └── 4_Info.py               # Project information
├── telegram_bot.py             # Telegram bot implementation
├── youtube_utils.py            # YouTube integration utilities
├── kargin_eng.csv             # Episode database
└── requirements*.txt          # Dependencies
```

## 💡 Development Story

This project was **vibecoded** with GitHub Copilot in just **2 hours** as a rapid prototyping session. The entire application, including the Telegram bot integration, advanced search algorithms, and YouTube features, came together through AI-assisted development.

**What was built in 2 hours:**
- Complete Streamlit web application
- Telegram bot with full search functionality
- Advanced fuzzy search with multiple algorithms
- YouTube integration with graceful fallbacks
- Data analytics dashboard
- Optional dependency system
- Comprehensive documentation

## 🔮 Future Improvements

This is just the beginning! Planned enhancements include:
- **Enhanced Search**: More sophisticated NLP-based search
- **User Accounts**: Favorites, watch history, and personal recommendations
- **Mobile App**: Native mobile application
- **API Endpoints**: RESTful API for third-party integrations
- **Multi-language**: Support for more languages
- **Advanced Analytics**: ML-powered insights and recommendations
- **Video Transcription**: Automatic subtitle generation and search
- **Social Features**: Comments, ratings, and community features

## 🤝 Contributing

This project showcases rapid AI-assisted development. Feel free to contribute improvements, report issues, or suggest new features!

## 📄 License

This project is open source and available under the MIT License.

---

*Built with ❤️ and AI assistance from GitHub Copilot*