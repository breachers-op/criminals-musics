import html
import time
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.constants import ParseMode
from database import get_session, User
from handlers.filters import check_banned

logger = logging.getLogger(__name__)
start_time = time.time()

START_TEXT = (
    "<b>🎵 Criminals Musics Bot</b>\n\n"
    "Hello {name}! I'm a music bot for Telegram voice chats.\n\n"
    "<b>Available Commands:</b>\n"
    "🎵 /play &lt;song name or URL&gt; — Play music in voice chat\n"
    "⏸ /pause — Pause current music\n"
    "▶️ /resume — Resume paused music\n"
    "⏹ /stop — Stop music and leave voice chat\n"
    "⏭ /skip — Skip current song\n"
    "📋 /queue — View current queue\n"
    "📁 /playlist — Manage your playlists\n"
    "⬇️ /download &lt;song name or URL&gt; — Download a song\n"
    "📂 /downloads — View your downloaded songs\n"
    "🏓 /ping — Check bot status"
)

HELP_TEXT = (
    "<b>🎵 Criminals Musics Bot — Help</b>\n\n"
    "<b>Music Commands:</b>\n"
    "• /play &lt;song&gt; — Search YouTube and play in voice chat\n"
    "• /pause — Pause the current song\n"
    "• /resume — Resume the paused song\n"
    "• /stop — Stop playback and clear the queue\n"
    "• /skip — Skip to the next song in queue\n"
    "• /queue — Show the current song queue\n\n"
    "<b>Download Commands:</b>\n"
    "• /download &lt;song&gt; — Download a song as audio file\n"
    "• /downloads — List your recent downloads\n\n"
    "<b>Playlist Commands:</b>\n"
    "• /playlist list — Show your playlists\n"
    "• /playlist create &lt;name&gt; — Create a new playlist\n"
    "• /playlist add &lt;name&gt; | &lt;song&gt; — Add a song to a playlist\n"
    "• /playlist view &lt;name&gt; — View songs in a playlist\n"
    "• /playlist delete &lt;name&gt; — Delete a playlist\n\n"
    "<b>Other:</b>\n"
    "• /ping — Check if the bot is online\n"
    "• /start — Show this welcome message\n"
    "• /help — Show this help message"
)


def _save_user(user_id: int, username: str, first_name: str):
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
    except Exception as e:
        logger.warning(f"save_user error: {e}")
    finally:
        db.close()


def register_start_handlers(app: Application):

    async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not user:
            return
        if await check_banned(user.id):
            return
        _save_user(user.id, user.username or "", user.first_name or "")
        name = html.escape(user.first_name or "there")
        await update.message.reply_text(
            START_TEXT.format(name=name),
            parse_mode=ParseMode.HTML
        )

    async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if user and await check_banned(user.id):
            return
        await update.message.reply_text(HELP_TEXT, parse_mode=ParseMode.HTML)

    async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if user and await check_banned(user.id):
            return
        sent = await update.message.reply_text("🏓 Pinging...")
        elapsed = round((time.time() - start_time) * 1000, 2)
        uptime_seconds = int(time.time() - start_time)
        hours, remainder = divmod(uptime_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_str = f"{hours}h {minutes}m {seconds}s"
        await sent.edit_text(
            f"🏓 <b>Pong!</b>\n"
            f"⚡ Latency: <code>{elapsed}ms</code>\n"
            f"⏱ Uptime: <code>{uptime_str}</code>",
            parse_mode=ParseMode.HTML
        )

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("ping", ping_command))
