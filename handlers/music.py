import html
import asyncio
import logging
from datetime import datetime
import yt_dlp
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.constants import ParseMode
from database import get_session, VoiceChatSession
from handlers.filters import check_banned

logger = logging.getLogger(__name__)

music_queues = {}


def get_queue(chat_id: int):
    if chat_id not in music_queues:
        music_queues[chat_id] = []
    return music_queues[chat_id]


def format_duration(seconds):
    if not seconds:
        return "Unknown"
    minutes, secs = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def update_session(chat_id, is_playing=None, current_song=None, current_url=None,
                   current_duration=None, started_at=None):
    session = get_session()
    try:
        record = session.query(VoiceChatSession).filter_by(chat_id=chat_id).first()
        if not record:
            record = VoiceChatSession(chat_id=chat_id)
            session.add(record)
        if is_playing is not None:
            record.is_playing = is_playing
        if current_song is not None:
            record.current_song = current_song
        if current_url is not None:
            record.current_song_url = current_url
        if current_duration is not None:
            record.current_duration = current_duration
        if started_at is not None:
            record.started_at = started_at
        record.updated_at = datetime.utcnow()
        session.commit()
    except Exception as e:
        logger.warning(f"update_session error: {e}")
    finally:
        session.close()


async def search_youtube(query: str):
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "default_search": "ytsearch1",
    }
    loop = asyncio.get_event_loop()

    def _search():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch1:{query}", download=False)
            if info and "entries" in info and info["entries"]:
                entry = info["entries"][0]
                return {
                    "title": entry.get("title", "Unknown"),
                    "url": entry.get("url") or f"https://www.youtube.com/watch?v={entry.get('id', '')}",
                    "duration": entry.get("duration", 0),
                    "webpage_url": f"https://www.youtube.com/watch?v={entry.get('id', '')}",
                }
        return None

    return await loop.run_in_executor(None, _search)


def register_music_handlers(app: Application):

    async def play_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        from handlers.voice import play_in_vc, is_vc_active
        user = update.effective_user
        chat = update.effective_chat
        if not user or await check_banned(user.id):
            return
        if chat.type not in ("group", "supergroup"):
            await update.message.reply_text(
                "❗ The /play command only works in group chats with a voice chat."
            )
            return
        chat_id = chat.id
        args = update.message.text.split(None, 1)
        if len(args) < 2:
            await update.message.reply_text(
                "🎵 <b>Usage:</b> /play &lt;song name or YouTube URL&gt;\n"
                "Example: /play Shape of You",
                parse_mode=ParseMode.HTML
            )
            return

        query = args[1].strip()
        status_msg = await update.message.reply_text(
            f"🔍 Searching for <b>{html.escape(query)}</b>...",
            parse_mode=ParseMode.HTML
        )

        result = await search_youtube(query)
        if not result:
            await status_msg.edit_text("❌ Could not find that song. Try a different search term.")
            return

        queue = get_queue(chat_id)
        queue.append(result)
        position = len(queue)
        title_safe = html.escape(result["title"])
        url = result["webpage_url"]

        update_session(
            chat_id,
            is_playing=True,
            current_song=result["title"],
            current_url=url,
            current_duration=result.get("duration", 0),
            started_at=datetime.utcnow() if position == 1 else None,
        )

        vc_note = ""
        if position == 1 and is_vc_active():
            streamed = await play_in_vc(chat_id, url)
            if not streamed:
                vc_note = "\n⚠️ Could not join voice chat. Make sure a voice chat is active."

        if position == 1:
            await status_msg.edit_text(
                f"🎵 <b>Now Playing</b>\n\n"
                f"🎶 <b>{title_safe}</b>\n"
                f"⏱ Duration: <code>{format_duration(result['duration'])}</code>\n"
                f"🔗 <a href=\"{url}\">Watch on YouTube</a>"
                + vc_note,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
            )
        else:
            await status_msg.edit_text(
                f"📋 <b>Added to Queue</b> (#{position})\n\n"
                f"🎶 <b>{title_safe}</b>\n"
                f"⏱ Duration: <code>{format_duration(result['duration'])}</code>\n"
                f"🔗 <a href=\"{url}\">Watch on YouTube</a>",
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
            )

    async def pause_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        from handlers.voice import pause_in_vc
        user = update.effective_user
        chat = update.effective_chat
        if not user or await check_banned(user.id):
            return
        if chat.type not in ("group", "supergroup"):
            return
        chat_id = chat.id
        session = get_session()
        try:
            record = session.query(VoiceChatSession).filter_by(chat_id=chat_id).first()
            if not record or not record.is_playing:
                await update.message.reply_text("❌ Nothing is currently playing.")
                return
            update_session(chat_id, is_playing=False)
            await pause_in_vc(chat_id)
            await update.message.reply_text("⏸ <b>Paused</b> the music.", parse_mode=ParseMode.HTML)
        finally:
            session.close()

    async def resume_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        from handlers.voice import resume_in_vc
        user = update.effective_user
        chat = update.effective_chat
        if not user or await check_banned(user.id):
            return
        if chat.type not in ("group", "supergroup"):
            return
        chat_id = chat.id
        session = get_session()
        try:
            record = session.query(VoiceChatSession).filter_by(chat_id=chat_id).first()
            if not record or not record.current_song:
                await update.message.reply_text("❌ Nothing is paused.")
                return
            update_session(chat_id, is_playing=True)
            await resume_in_vc(chat_id)
            await update.message.reply_text(
                f"▶️ <b>Resumed</b>\n🎶 {html.escape(record.current_song)}",
                parse_mode=ParseMode.HTML
            )
        finally:
            session.close()

    async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        from handlers.voice import stop_in_vc
        user = update.effective_user
        chat = update.effective_chat
        if not user or await check_banned(user.id):
            return
        if chat.type not in ("group", "supergroup"):
            return
        chat_id = chat.id
        queue = get_queue(chat_id)
        queue.clear()
        update_session(chat_id, is_playing=False, current_song="", current_url="")
        await stop_in_vc(chat_id)
        await update.message.reply_text("⏹ <b>Stopped</b> playback and cleared the queue.", parse_mode=ParseMode.HTML)

    async def skip_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        from handlers.voice import skip_in_vc, play_in_vc, stop_in_vc, is_vc_active
        user = update.effective_user
        chat = update.effective_chat
        if not user or await check_banned(user.id):
            return
        if chat.type not in ("group", "supergroup"):
            return
        chat_id = chat.id
        queue = get_queue(chat_id)
        if not queue:
            await update.message.reply_text("❌ The queue is empty, nothing to skip.")
            return
        skipped = queue.pop(0)
        if queue:
            next_song = queue[0]
            update_session(
                chat_id,
                is_playing=True,
                current_song=next_song["title"],
                current_url=next_song["webpage_url"],
                current_duration=next_song.get("duration", 0),
                started_at=datetime.utcnow(),
            )
            if is_vc_active():
                await skip_in_vc(chat_id, next_song["webpage_url"])
            await update.message.reply_text(
                f"⏭ <b>Skipped:</b> {html.escape(skipped['title'])}\n\n"
                f"🎵 <b>Now Playing:</b> {html.escape(next_song['title'])}\n"
                f"🔗 <a href=\"{next_song['webpage_url']}\">YouTube</a>",
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
            )
        else:
            update_session(chat_id, is_playing=False, current_song="", current_url="")
            if is_vc_active():
                await stop_in_vc(chat_id)
            await update.message.reply_text(
                f"⏭ <b>Skipped:</b> {html.escape(skipped['title'])}\n\n"
                "📋 The queue is now empty.",
                parse_mode=ParseMode.HTML
            )

    async def queue_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not user or await check_banned(user.id):
            return
        chat_id = update.effective_chat.id
        queue = get_queue(chat_id)
        if not queue:
            await update.message.reply_text(
                "📋 The queue is currently empty.\nUse /play &lt;song&gt; to add music!",
                parse_mode=ParseMode.HTML
            )
            return
        lines = ["📋 <b>Current Queue</b>\n"]
        for i, song in enumerate(queue):
            icon = "🎵" if i == 0 else f"{i + 1}."
            label = " ← <i>Now Playing</i>" if i == 0 else ""
            lines.append(f"{icon} <b>{html.escape(song['title'])}</b> <code>[{format_duration(song['duration'])}]</code>{label}")
        lines.append(f"\n<b>Total:</b> {len(queue)} song(s)")
        await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)

    app.add_handler(CommandHandler("play", play_command))
    app.add_handler(CommandHandler("pause", pause_command))
    app.add_handler(CommandHandler("resume", resume_command))
    app.add_handler(CommandHandler("stop", stop_command))
    app.add_handler(CommandHandler("skip", skip_command))
    app.add_handler(CommandHandler("queue", queue_command))
