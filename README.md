# 🎵 Criminals Musics - Telegram Music Bot

A powerful Telegram music bot built with PyroTGfork that plays music in voice chats, manages playlists, downloads songs, and includes sudo/admin features.

## ✨ Features

- 🎶 **Play Music in Voice Chat** - Stream music directly to voice chats using yt-dlp
- 📻 **Playlist Management** - Create, view, and manage playlists
- ⬇️ **Download Music** - Download songs for offline access
- 👑 **Sudo Features** - Admin-only commands for bot control
- ⏸️ **Playback Controls** - Play, pause, resume, skip, stop
- 🔄 **Queue Management** - Manage song queue
- 💾 **SQLite Database** - Persistent storage for playlists and user data
- 🔍 **YouTube Search** - Search and play songs from YouTube

## 🚀 Installation

### Prerequisites
- Python 3.8 or higher
- FFmpeg installed on your system
- A Telegram bot token (get it from [@BotFather](https://t.me/botfather))
- Your Telegram API ID and Hash (get from [my.telegram.org](https://my.telegram.org))

# 🔐 Pyrogram Session Generator

Generate Pyrogram session strings directly on Replit.

## 🚀 Run on Replit

[![Run on Replit](https://replit.com/badge/github/breachers-op/criminals-musics)](https://replit.com/github/breachers-op/criminals-musics)

### Setup Steps

1. **Clone the repository:**
   ```bash
   git clone https://github.com/breachers-op/criminals-musics.git
   cd criminals-musics
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Create `.env` file:**
   ```bash
   cp .env.example .env
   ```
   Edit `.env` and fill in your credentials:
   - `API_ID`: Your Telegram API ID
   - `API_HASH`: Your Telegram API Hash
   - `BOT_TOKEN`: Your bot token from @BotFather
   - `SUDO_USERS`: Your user ID for admin commands

5. **Run the bot:**
   ```bash
   python bot.py
   ```

## 📝 Commands

### Basic Commands
- `/play <song name or URL>` - Play a song from YouTube
- `/stop` - Stop playing music
- `/pause` - Pause the current song
- `/resume` - Resume the paused song
- `/skip` - Skip to the next song

### Playlist Commands
- `/playlist add <song name>` - Add song to playlist
- `/playlist remove <song name>` - Remove song from playlist
- `/playlist view` - View all saved playlists
- `/playlist clear` - Clear current playlist

### Download Commands
- `/download <song name or URL>` - Download a song
- `/downloads` - View downloaded songs

### Sudo Commands (Owner Only)
- `/sudoers` - List all sudo users
- `/addsudo <user_id>` - Add sudo user
- `/removesudo <user_id>` - Remove sudo user
- `/stats` - Bot statistics
- `/restart` - Restart the bot

## 🏗️ Project Structure

```
criminals-musics/
├── bot.py                 # Main bot entry point
├── config/
│   └── config.py         # Configuration management
├── database/
│   ├── __init__.py
│   ├── models.py         # Database models (SQLite)
│   └── db.py             # Database operations
├── handlers/
│   ├── __init__.py
│   ├── music.py          # Music playing commands
│   ├── playlist.py       # Playlist management
│   ├── download.py       # Download commands
│   └── admin.py          # Sudo/admin commands
├── utils/
│   ├── __init__.py
│   ├── helpers.py        # Helper functions
│   ├── ytdlp.py          # yt-dlp integration
│   └── logger.py         # Logging setup
├── requirements.txt      # Project dependencies
├── .env.example          # Environment variables template
├── .gitignore            # Git ignore rules
└── README.md             # This file
```

## 🔧 Configuration

Edit `.env` file to configure:
- **API Credentials** - Your Telegram API credentials
- **Bot Token** - From @BotFather
- **Sudo Users** - User IDs with admin access
- **Database** - SQLite database location
- **Music Directory** - Where to save downloads

## 📦 Dependencies

- **pyrogram** - Telegram client library
- **yt-dlp** - YouTube and other sites downloader
- **sqlalchemy** - ORM for database
- **python-dotenv** - Environment variables management

## 🤝 Contributing

Feel free to fork this project and submit pull requests for improvements!

## ⚠️ Disclaimer

This bot is for educational purposes. Users are responsible for respecting copyright laws and Telegram's terms of service. The creator is not responsible for any misuse.

## 📄 License

MIT License - Feel free to use this project for your own purposes.

## 👨‍💻 Author

**breachers-op** - [GitHub Profile](https://github.com/breachers-op)

## 🙏 Support

If you find this project helpful, consider giving it a ⭐ on GitHub!

---

**Happy Listening! 🎵**
