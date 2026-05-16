from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from handlers.filters import not_banned
from database import get_session, VoiceChatSession
from datetime import datetime
import re
import logging

logger = logging.getLogger(__name__)


def _extract_video_id(url: str):
    if not url:
        return None
    m = re.search(r"(?:v=|youtu\.be/|/v/|/embed/)([A-Za-z0-9_-]{11})", url)
    return m.group(1) if m else None


def _progress_bar(elapsed: float, total: float, width: int = 18):
    if not total or total <= 0:
        return "░" * width
    ratio = min(elapsed / total, 1.0)
    filled = int(ratio * width)
    return "▓" * filled + "░" * (width - filled)


def _fmt(seconds):
    if not seconds or seconds < 0:
        return "0:00"
    seconds = int(seconds)
    minutes, secs = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def register_nowplaying_handlers(app: Client):

    @app.on_message(filters.command("nowplaying") & (filters.private | filters.group) & not_banned)
    async def nowplaying_command(client: Client, message: Message):
        chat_id = message.chat.id

        db = get_session()
        try:
            record = db.query(VoiceChatSession).filter_by(chat_id=chat_id).first()
        finally:
            db.close()

        if not record or not record.current_song:
            await message.reply_text(
                "🎵 Nothing is currently playing.\n"
                "Use `/play <song>` to start the music!"
            )
            return

        status = "▶️ Playing" if record.is_playing else "⏸ Paused"
        title = record.current_song or "Unknown"
        url = record.current_song_url or ""
        duration = record.current_duration or 0
        started_at = record.started_at

        now = datetime.utcnow()
        elapsed = (now - started_at).total_seconds() if started_at else 0
        elapsed = max(0, min(elapsed, duration)) if duration else elapsed

        bar = _progress_bar(elapsed, duration)
        elapsed_str = _fmt(elapsed)
        total_str = _fmt(duration)

        video_id = _extract_video_id(url)
        thumbnail_url = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg" if video_id else None

        caption_lines = [
            f"{status}", f"",
            f"🎶 **{title}**", f"",
            f"`{elapsed_str}` {bar} `{total_str}`",
        ]
        if url:
            caption_lines.append(f"\n🔗 [Watch on YouTube]({url})")

        caption = "\n".join(caption_lines)
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("⏮ Queue", callback_data="np:queue"),
            InlineKeyboardButton("⏭ Skip", callback_data="np:skip"),
            InlineKeyboardButton("🎵 Lyrics", callback_data="np:lyrics"),
        ]])

        if thumbnail_url:
            try:
                await message.reply_photo(photo=thumbnail_url, caption=caption, reply_markup=keyboard)
                return
            except Exception as e:
                logger.warning(f"Could not send thumbnail: {e}")

        await message.reply_text(caption, reply_markup=keyboard)

    @app.on_callback_query(filters.regex(r"^np:"))
    async def nowplaying_callback(client, callback):
        action = callback.data.split(":")[1]
        chat_id = callback.message.chat.id

        if action == "queue":
            from handlers.music import get_queue, format_duration
            queue = get_queue(chat_id)
            if not queue:
                await callback.answer("📋 The queue is empty.", show_alert=True)
                return
            lines = ["📋 **Current Queue**\n"]
            for i, song in enumerate(queue):
                icon = "🎵" if i == 0 else f"`{i + 1}.`"
                label = " ← Now Playing" if i == 0 else ""
                lines.append(f"{icon} **{song['title']}** `[{format_duration(song['duration'])}]`{label}")
            await callback.answer()
            await callback.message.reply_text("\n".join(lines))

        elif action == "skip":
            from handlers.music import get_queue, update_session
            from handlers.voice import skip_in_vc, stop_in_vc, is_vc_active
            queue = get_queue(chat_id)
            if not queue:
                await callback.answer("❌ Queue is empty.", show_alert=True)
                return
            skipped = queue.pop(0)
            if queue:
                nxt = queue[0]
                update_session(
                    chat_id, is_playing=True, current_song=nxt["title"],
                    current_url=nxt["webpage_url"], current_duration=nxt.get("duration", 0),
                    started_at=datetime.utcnow(),
                )
                if is_vc_active():
                    await skip_in_vc(chat_id, nxt["webpage_url"])
                await callback.answer(f"⏭ Skipped! Now: {nxt['title']}", show_alert=False)
            else:
                update_session(chat_id, is_playing=False, current_song="", current_url="")
                if is_vc_active():
                    await stop_in_vc(chat_id)
                await callback.answer("⏭ Skipped! Queue is now empty.", show_alert=False)
            await callback.message.delete()

        elif action == "lyrics":
            db = get_session()
            try:
                record = db.query(VoiceChatSession).filter_by(chat_id=chat_id).first()
                song = record.current_song if record else None
            finally:
                db.close()
            if not song:
                await callback.answer("❌ Nothing is playing.", show_alert=True)
                return
            await callback.answer("🎵 Fetching lyrics...", show_alert=False)
            await callback.message.reply_text("Use `/lyrics` to get lyrics for the current song.")
