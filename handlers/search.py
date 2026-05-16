from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from handlers.filters import not_banned
import yt_dlp
import asyncio
import logging

logger = logging.getLogger(__name__)

search_cache = {}


def format_duration(seconds):
    if not seconds:
        return "?:??"
    minutes, secs = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


async def search_youtube_multi(query: str, count: int = 5):
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
    }
    loop = asyncio.get_event_loop()
    def _search():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch{count}:{query}", download=False)
            results = []
            if info and "entries" in info:
                for entry in info["entries"]:
                    if not entry:
                        continue
                    results.append({
                        "title": entry.get("title", "Unknown"),
                        "duration": entry.get("duration", 0),
                        "webpage_url": f"https://www.youtube.com/watch?v={entry.get('id', '')}",
                        "channel": entry.get("channel") or entry.get("uploader") or "Unknown",
                    })
            return results
    return await loop.run_in_executor(None, _search)


def register_search_handlers(app: Client):

    @app.on_message(filters.command("search") & (filters.private | filters.group) & not_banned)
    async def search_command(client: Client, message: Message):
        args = message.text.split(None, 1)
        if len(args) < 2:
            await message.reply_text(
                "🔎 **Usage:** `/search <song name>`\n"
                "Example: `/search Blinding Lights`"
            )
            return

        query = args[1].strip()
        user_id = message.from_user.id if message.from_user else 0
        chat_id = message.chat.id

        status_msg = await message.reply_text(f"🔎 Searching YouTube for **{query}**...")
        results = await search_youtube_multi(query, count=5)

        if not results:
            await status_msg.edit_text("❌ No results found. Try a different search term.")
            return

        cache_key = f"{user_id}:{chat_id}"
        search_cache[cache_key] = {
            "results": results,
            "query": query,
            "chat_id": chat_id,
            "is_group": message.chat.type.value in ("group", "supergroup"),
        }

        lines = [f"🎵 **Search Results for:** `{query}`\n"]
        for i, r in enumerate(results, 1):
            lines.append(
                f"`{i}.` **{r['title']}**\n"
                f"    👤 {r['channel']} | ⏱ `{format_duration(r['duration'])}`"
            )

        play_buttons = [
            InlineKeyboardButton(f"▶️ {i+1}", callback_data=f"play:{user_id}:{i}")
            for i in range(len(results))
        ]
        dl_buttons = [
            InlineKeyboardButton(f"⬇️ {i+1}", callback_data=f"dl:{user_id}:{i}")
            for i in range(len(results))
        ]
        keyboard = InlineKeyboardMarkup([
            play_buttons,
            dl_buttons,
            [InlineKeyboardButton("❌ Cancel", callback_data=f"cancel:{user_id}")]
        ])

        await status_msg.edit_text(
            "\n".join(lines) + "\n\n▶️ = Add to queue   ⬇️ = Download",
            reply_markup=keyboard
        )

    @app.on_callback_query(filters.regex(r"^(play|dl|cancel):"))
    async def search_callback(client: Client, callback: CallbackQuery):
        data = callback.data.split(":")
        action = data[0]
        requester_id = int(data[1])

        if callback.from_user.id != requester_id:
            await callback.answer("❌ This search was made by someone else.", show_alert=True)
            return

        if action == "cancel":
            await callback.message.edit_text("❌ Search cancelled.")
            await callback.answer()
            return

        index = int(data[2])
        cache_key = f"{requester_id}:{callback.message.chat.id}"
        cached = search_cache.get(cache_key)

        if not cached:
            await callback.answer("⚠️ Search results expired. Please search again.", show_alert=True)
            return

        results = cached["results"]
        if index >= len(results):
            await callback.answer("⚠️ Invalid selection.", show_alert=True)
            return

        chosen = results[index]

        if action == "play":
            if not cached["is_group"]:
                await callback.answer("❗ /play only works in group chats.", show_alert=True)
                return
            from handlers.music import get_queue, update_session
            from handlers.voice import play_in_vc, is_vc_active
            from datetime import datetime
            queue = get_queue(cached["chat_id"])
            queue.append({
                "title": chosen["title"],
                "url": chosen["webpage_url"],
                "duration": chosen["duration"],
                "webpage_url": chosen["webpage_url"],
            })
            position = len(queue)
            update_session(
                cached["chat_id"],
                is_playing=True,
                current_song=chosen["title"],
                current_url=chosen["webpage_url"],
                current_duration=chosen.get("duration", 0),
                started_at=datetime.utcnow() if position == 1 else None,
            )
            vc_note = ""
            if position == 1 and is_vc_active():
                streamed = await play_in_vc(cached["chat_id"], chosen["webpage_url"])
                if not streamed:
                    vc_note = "\n⚠️ Could not join voice chat. Make sure a voice chat is active."
            label = "🎵 **Now Playing**" if position == 1 else f"📋 **Added to Queue** (#{position})"
            await callback.message.edit_text(
                f"{label}\n\n"
                f"🎶 **{chosen['title']}**\n"
                f"👤 {chosen['channel']}\n"
                f"⏱ `{format_duration(chosen['duration'])}`\n"
                f"🔗 [Watch on YouTube]({chosen['webpage_url']})"
                + vc_note
            )
            await callback.answer("Added to queue!")

        elif action == "dl":
            await callback.answer("⬇️ Starting download...")
            await callback.message.edit_text(f"⬇️ Downloading **{chosen['title']}**...\nThis may take a moment.")
            try:
                from handlers.download import download_audio, format_duration as fd, format_size
                from config import DOWNLOAD_DIR, AUDIO_QUALITY
                from database import get_session, DownloadedSong
                from datetime import datetime
                import os

                result = await download_audio(chosen["webpage_url"], DOWNLOAD_DIR, AUDIO_QUALITY)
                filepath = result["filename"]

                if not os.path.exists(filepath):
                    await callback.message.edit_text("❌ Download failed. File could not be saved.")
                    return

                file_size = os.path.getsize(filepath)
                db = get_session()
                try:
                    record = DownloadedSong(
                        user_id=requester_id,
                        song_title=result["title"],
                        song_url=chosen["webpage_url"],
                        file_path=filepath,
                        file_size=file_size,
                        duration=result["duration"],
                        downloaded_at=datetime.utcnow(),
                    )
                    db.add(record)
                    db.commit()
                finally:
                    db.close()

                await callback.message.edit_text(f"📤 Uploading **{result['title']}**...")
                await callback.message.reply_audio(
                    audio=filepath,
                    title=result["title"],
                    duration=result["duration"],
                    caption=(
                        f"🎵 **{result['title']}**\n"
                        f"⏱ Duration: `{fd(result['duration'])}`\n"
                        f"📦 Size: `{format_size(file_size)}`"
                    ),
                )
                await callback.message.delete()
            except Exception as e:
                logger.error(f"Search download error: {e}")
                await callback.message.edit_text(f"❌ Download failed.\n`{str(e)[:200]}`")

        search_cache.pop(cache_key, None)
