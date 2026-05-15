from pyrogram import Client, filters
from pyrogram.types import Message
from database import get_session, VoiceChatSession
from handlers.filters import not_banned
from datetime import datetime
import yt_dlp
import asyncio
import os
import logging

logger = logging.getLogger(__name__)

music_queues = {}


def get_queue(chat_id: int):
    if chat_id not in music_queues:
        music_queues[chat_id] = []
    return music_queues[chat_id]


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
    finally:
        session.close()


def register_music_handlers(app: Client):

    @app.on_message(filters.command("play") & filters.group & not_banned)
    async def play_command(client: Client, message: Message):
        from handlers.voice import play_in_vc, is_vc_active
        chat_id = message.chat.id
        args = message.text.split(None, 1)
        if len(args) < 2:
            await message.reply_text(
                "🎵 **Usage:** `/play <song name or YouTube URL>`\n"
                "Example: `/play Shape of You`"
            )
            return

        query = args[1].strip()
        status_msg = await message.reply_text(f"🔍 Searching for **{query}**...")

        result = await search_youtube(query)
        if not result:
            await status_msg.edit_text("❌ Could not find that song. Try a different search term.")
            return

        queue = get_queue(chat_id)
        queue.append(result)
        position = len(queue)

        update_session(
            chat_id,
            is_playing=True,
            current_song=result["title"],
            current_url=result["webpage_url"],
            current_duration=result.get("duration", 0),
            started_at=datetime.utcnow() if position == 1 else None,
        )

        vc_note = ""
        if position == 1 and is_vc_active():
            streamed = await play_in_vc(chat_id, result["webpage_url"])
            if not streamed:
                vc_note = "\n⚠️ Could not join voice chat. Make sure a voice chat is active."

        if position == 1:
            await status_msg.edit_text(
                f"🎵 **Now Playing**\n\n"
                f"🎶 **{result['title']}**\n"
                f"⏱ Duration: `{format_duration(result['duration'])}`\n"
                f"🔗 [Watch on YouTube]({result['webpage_url']})"
                + vc_note
            )
        else:
            await status_msg.edit_text(
                f"📋 **Added to Queue** (#{position})\n\n"
                f"🎶 **{result['title']}**\n"
                f"⏱ Duration: `{format_duration(result['duration'])}`\n"
                f"🔗 [Watch on YouTube]({result['webpage_url']})"
            )

    @app.on_message(filters.command("play") & filters.private & not_banned)
    async def play_private(client: Client, message: Message):
        await message.reply_text("❗ The `/play` command only works in group chats with a voice chat.")

    @app.on_message(filters.command("pause") & filters.group & not_banned)
    async def pause_command(client: Client, message: Message):
        from handlers.voice import pause_in_vc
        chat_id = message.chat.id
        session = get_session()
        try:
            record = session.query(VoiceChatSession).filter_by(chat_id=chat_id).first()
            if not record or not record.is_playing:
                await message.reply_text("❌ Nothing is currently playing.")
                return
            update_session(chat_id, is_playing=False)
            await pause_in_vc(chat_id)
            await message.reply_text("⏸ **Paused** the music.")
        finally:
            session.close()

    @app.on_message(filters.command("resume") & filters.group & not_banned)
    async def resume_command(client: Client, message: Message):
        from handlers.voice import resume_in_vc
        chat_id = message.chat.id
        session = get_session()
        try:
            record = session.query(VoiceChatSession).filter_by(chat_id=chat_id).first()
            if not record or not record.current_song:
                await message.reply_text("❌ Nothing is paused.")
                return
            update_session(chat_id, is_playing=True)
            await resume_in_vc(chat_id)
            await message.reply_text(f"▶️ **Resumed**\n🎶 {record.current_song}")
        finally:
            session.close()

    @app.on_message(filters.command("stop") & filters.group & not_banned)
    async def stop_command(client: Client, message: Message):
        from handlers.voice import stop_in_vc
        chat_id = message.chat.id
        queue = get_queue(chat_id)
        queue.clear()
        update_session(chat_id, is_playing=False, current_song="", current_url="")
        await stop_in_vc(chat_id)
        await message.reply_text("⏹ **Stopped** playback and cleared the queue.")

    @app.on_message(filters.command("skip") & filters.group & not_banned)
    async def skip_command(client: Client, message: Message):
        from handlers.voice import skip_in_vc, stop_in_vc, is_vc_active
        chat_id = message.chat.id
        queue = get_queue(chat_id)
        if not queue:
            await message.reply_text("❌ The queue is empty, nothing to skip.")
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
            await message.reply_text(
                f"⏭ **Skipped:** {skipped['title']}\n\n"
                f"🎵 **Now Playing:** {next_song['title']}\n"
                f"🔗 [YouTube]({next_song['webpage_url']})"
            )
        else:
            update_session(chat_id, is_playing=False, current_song="", current_url="")
            if is_vc_active():
                await stop_in_vc(chat_id)
            await message.reply_text(
                f"⏭ **Skipped:** {skipped['title']}\n\n"
                "📋 The queue is now empty."
            )

    @app.on_message(filters.command("queue") & (filters.private | filters.group) & not_banned)
    async def queue_command(client: Client, message: Message):
        chat_id = message.chat.id
        queue = get_queue(chat_id)
        if not queue:
            await message.reply_text("📋 The queue is currently empty.\nUse `/play <song>` to add music!")
            return

        lines = ["📋 **Current Queue**\n"]
        for i, song in enumerate(queue):
            icon = "🎵" if i == 0 else f"`{i + 1}.`"
            label = " ← *Now Playing*" if i == 0 else ""
            lines.append(f"{icon} **{song['title']}** `[{format_duration(song['duration'])}]`{label}")
        lines.append(f"\n**Total:** {len(queue)} song(s)")
        await message.reply_text("\n".join(lines))
