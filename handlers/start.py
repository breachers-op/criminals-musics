from pyrogram import Client, filters
from pyrogram.types import Message
from database import get_session, User
from handlers.filters import not_banned
from datetime import datetime
import time

START_TEXT = """
**🎵 Criminals Musics Bot**

Hello {name}! I'm a music bot for Telegram voice chats.

**Available Commands:**
🎵 `/play <song name or URL>` — Play music in voice chat
⏸ `/pause` — Pause current music
▶️ `/resume` — Resume paused music
⏹ `/stop` — Stop music and leave voice chat
⏭ `/skip` — Skip current song
📋 `/queue` — View current queue
📁 `/playlist` — Manage your playlists
⬇️ `/download <song name or URL>` — Download a song
📂 `/downloads` — View your downloaded songs
🏓 `/ping` — Check bot status
"""

HELP_TEXT = """
**🎵 Criminals Musics Bot — Help**

**Music Commands:**
• `/play <song>` — Search YouTube and play in voice chat
• `/pause` — Pause the current song
• `/resume` — Resume the paused song
• `/stop` — Stop playback and clear the queue
• `/skip` — Skip to the next song in queue
• `/queue` — Show the current song queue

**Download Commands:**
• `/download <song>` — Download a song as audio file
• `/downloads` — List your recent downloads

**Playlist Commands:**
• `/playlist list` — Show your playlists
• `/playlist create <name>` — Create a new playlist
• `/playlist add <name> | <song>` — Add a song to a playlist
• `/playlist view <name>` — View songs in a playlist
• `/playlist delete <name>` — Delete a playlist

**Other:**
• `/ping` — Check if the bot is online
• `/start` — Show this welcome message
• `/help` — Show this help message
"""

start_time = time.time()


def save_user(user_id: int, username: str, first_name: str):
    db = get_session()
    try:
        user = db.query(User).filter_by(user_id=user_id).first()
        if user:
            user.username = username
            user.first_name = first_name
            user.last_seen = datetime.utcnow()
        else:
            user = User(
                user_id=user_id,
                username=username,
                first_name=first_name,
                created_at=datetime.utcnow(),
                last_seen=datetime.utcnow(),
            )
            db.add(user)
        db.commit()
    finally:
        db.close()


def register_start_handlers(app: Client):

    @app.on_message(filters.command("start") & (filters.private | filters.group) & not_banned)
    async def start_command(client: Client, message: Message):
        if message.from_user:
            save_user(
                user_id=message.from_user.id,
                username=message.from_user.username or "",
                first_name=message.from_user.first_name or "",
            )
        name = message.from_user.first_name if message.from_user else "there"
        await message.reply_text(START_TEXT.format(name=name))

    @app.on_message(filters.command("help") & (filters.private | filters.group) & not_banned)
    async def help_command(client: Client, message: Message):
        await message.reply_text(HELP_TEXT)

    @app.on_message(filters.command("ping") & (filters.private | filters.group) & not_banned)
    async def ping_command(client: Client, message: Message):
        start = time.time()
        sent = await message.reply_text("🏓 Pinging...")
        elapsed = round((time.time() - start) * 1000, 2)
        uptime_seconds = int(time.time() - start_time)
        hours, remainder = divmod(uptime_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_str = f"{hours}h {minutes}m {seconds}s"
        await sent.edit_text(
            f"🏓 **Pong!**\n"
            f"⚡ Latency: `{elapsed}ms`\n"
            f"⏱ Uptime: `{uptime_str}`"
        )
