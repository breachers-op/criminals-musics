import html
import asyncio
import os
import logging
from datetime import datetime
import yt_dlp
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.constants import ParseMode
from database import get_session, DownloadedSong
from config import DOWNLOAD_DIR, AUDIO_QUALITY
from handlers.filters import check_banned

logger = logging.getLogger(__name__)


def format_duration(seconds):
    if not seconds:
        return "Unknown"
    minutes, secs = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def format_size(size_bytes):
    if not size_bytes:
        return "Unknown"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes / (1024 * 1024):.1f} MB"


async def download_audio(query: str, output_dir: str, quality: str = "192"):
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(output_dir, "%(title)s.%(ext)s"),
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": quality,
        }],
        "quiet": True,
        "no_warnings": True,
        "default_search": "ytsearch1",
    }
    loop = asyncio.get_event_loop()

    def _download():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(
                f"ytsearch1:{query}" if not query.startswith("http") else query,
                download=True
            )
            if "entries" in info:
                info = info["entries"][0]
            title = info.get("title", "Unknown")
            duration = info.get("duration", 0)
            filename = ydl.prepare_filename(info).rsplit(".", 1)[0] + ".mp3"
            return {
                "title": title,
                "duration": duration,
                "filename": filename,
                "webpage_url": info.get("webpage_url", ""),
            }

    return await loop.run_in_executor(None, _download)


def register_download_handlers(app: Application):

    async def download_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not user or await check_banned(user.id):
            return
        args = update.message.text.split(None, 1)
        if len(args) < 2:
            await update.message.reply_text(
                "⬇️ <b>Usage:</b> /download &lt;song name or YouTube URL&gt;\n"
                "Example: /download Bohemian Rhapsody",
                parse_mode=ParseMode.HTML
            )
            return

        query = args[1].strip()
        user_id = user.id
        status_msg = await update.message.reply_text(
            f"⬇️ Downloading <b>{html.escape(query)}</b>...\nThis may take a moment.",
            parse_mode=ParseMode.HTML
        )

        try:
            result = await download_audio(query, DOWNLOAD_DIR, AUDIO_QUALITY)
            filepath = result["filename"]

            if not os.path.exists(filepath):
                await status_msg.edit_text("❌ Download failed. The file could not be saved.")
                return

            file_size = os.path.getsize(filepath)

            db = get_session()
            try:
                record = DownloadedSong(
                    user_id=user_id,
                    song_title=result["title"],
                    song_url=result["webpage_url"],
                    file_path=filepath,
                    file_size=file_size,
                    duration=result["duration"],
                    downloaded_at=datetime.utcnow(),
                )
                db.add(record)
                db.commit()
            finally:
                db.close()

            await status_msg.edit_text(
                f"📤 Uploading <b>{html.escape(result['title'])}</b>...",
                parse_mode=ParseMode.HTML
            )
            with open(filepath, "rb") as f:
                await update.message.reply_audio(
                    audio=f,
                    title=result["title"],
                    duration=result["duration"],
                    caption=(
                        f"🎵 <b>{html.escape(result['title'])}</b>\n"
                        f"⏱ Duration: <code>{format_duration(result['duration'])}</code>\n"
                        f"📦 Size: <code>{format_size(file_size)}</code>"
                    ),
                    parse_mode=ParseMode.HTML,
                )
            await status_msg.delete()

        except Exception as e:
            logger.error(f"Download error: {e}")
            await status_msg.edit_text(
                f"❌ Failed to download.\n<code>{html.escape(str(e)[:200])}</code>",
                parse_mode=ParseMode.HTML
            )

    async def downloads_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not user or await check_banned(user.id):
            return
        user_id = user.id
        db = get_session()
        try:
            songs = (
                db.query(DownloadedSong)
                .filter_by(user_id=user_id)
                .order_by(DownloadedSong.downloaded_at.desc())
                .limit(10)
                .all()
            )
        finally:
            db.close()

        if not songs:
            await update.message.reply_text(
                "📂 You have no downloaded songs yet.\n"
                "Use /download &lt;song&gt; to download music!",
                parse_mode=ParseMode.HTML
            )
            return

        lines = ["📂 <b>Your Recent Downloads</b> (last 10)\n"]
        for i, song in enumerate(songs, 1):
            lines.append(
                f"<code>{i}.</code> <b>{html.escape(song.song_title)}</b>\n"
                f"    ⏱ <code>{format_duration(song.duration)}</code> | 📦 <code>{format_size(song.file_size)}</code>"
            )
        await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)

    app.add_handler(CommandHandler("download", download_command))
    app.add_handler(CommandHandler("downloads", downloads_command))
