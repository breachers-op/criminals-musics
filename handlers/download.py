from pyrogram import Client, filters
from pyrogram.types import Message
from database import get_session, DownloadedSong, User
from config import DOWNLOAD_DIR, AUDIO_QUALITY
from handlers.filters import not_banned
from datetime import datetime
import yt_dlp
import asyncio
import os
import logging

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
            info = ydl.extract_info(f"ytsearch1:{query}" if not query.startswith("http") else query, download=True)
            if "entries" in info:
                info = info["entries"][0]
            title = info.get("title", "Unknown")
            duration = info.get("duration", 0)
            filename = ydl.prepare_filename(info).rsplit(".", 1)[0] + ".mp3"
            return {"title": title, "duration": duration, "filename": filename, "webpage_url": info.get("webpage_url", "")}
    return await loop.run_in_executor(None, _download)


def register_download_handlers(app: Client):

    @app.on_message(filters.command("download") & (filters.private | filters.group) & not_banned)
    async def download_command(client: Client, message: Message):
        args = message.text.split(None, 1)
        if len(args) < 2:
            await message.reply_text(
                "⬇️ **Usage:** `/download <song name or YouTube URL>`\n"
                "Example: `/download Bohemian Rhapsody`"
            )
            return

        query = args[1].strip()
        user_id = message.from_user.id if message.from_user else 0
        status_msg = await message.reply_text(f"⬇️ Downloading **{query}**...\nThis may take a moment.")

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

            await status_msg.edit_text(f"📤 Uploading **{result['title']}**...")
            await message.reply_audio(
                audio=filepath,
                title=result["title"],
                duration=result["duration"],
                caption=(
                    f"🎵 **{result['title']}**\n"
                    f"⏱ Duration: `{format_duration(result['duration'])}`\n"
                    f"📦 Size: `{format_size(file_size)}`"
                ),
            )
            await status_msg.delete()

        except Exception as e:
            logger.error(f"Download error: {e}")
            await status_msg.edit_text(f"❌ Failed to download.\n`{str(e)[:200]}`")

    @app.on_message(filters.command("downloads") & (filters.private | filters.group) & not_banned)
    async def downloads_command(client: Client, message: Message):
        user_id = message.from_user.id if message.from_user else 0
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
            await message.reply_text(
                "📂 You have no downloaded songs yet.\n"
                "Use `/download <song>` to download music!"
            )
            return

        lines = ["📂 **Your Recent Downloads** (last 10)\n"]
        for i, song in enumerate(songs, 1):
            lines.append(
                f"`{i}.` **{song.song_title}**\n"
                f"    ⏱ `{format_duration(song.duration)}` | 📦 `{format_size(song.file_size)}`"
            )
        await message.reply_text("\n".join(lines))
