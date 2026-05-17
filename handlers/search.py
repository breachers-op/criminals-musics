import html
import asyncio
import logging
import yt_dlp
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.constants import ParseMode
from handlers.filters import check_banned

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
    ydl_opts = {"quiet": True, "no_warnings": True, "extract_flat": True}
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


def register_search_handlers(app: Application):

    async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        chat = update.effective_chat
        if not user or await check_banned(user.id):
            return
        args = update.message.text.split(None, 1)
        if len(args) < 2:
            await update.message.reply_text(
                "🔎 <b>Usage:</b> /search &lt;song name&gt;\nExample: /search Blinding Lights",
                parse_mode=ParseMode.HTML
            )
            return

        query = args[1].strip()
        user_id = user.id
        chat_id = chat.id

        status_msg = await update.message.reply_text(
            f"🔎 Searching YouTube for <b>{html.escape(query)}</b>...",
            parse_mode=ParseMode.HTML
        )
        results = await search_youtube_multi(query, count=5)

        if not results:
            await status_msg.edit_text("❌ No results found. Try a different search term.")
            return

        cache_key = f"{user_id}:{chat_id}"
        search_cache[cache_key] = {
            "results": results,
            "query": query,
            "chat_id": chat_id,
            "is_group": chat.type in ("group", "supergroup"),
        }

        lines = [f"🎵 <b>Search Results for:</b> <code>{html.escape(query)}</code>\n"]
        for i, r in enumerate(results, 1):
            lines.append(
                f"<code>{i}.</code> <b>{html.escape(r['title'])}</b>\n"
                f"    👤 {html.escape(r['channel'])} | ⏱ <code>{format_duration(r['duration'])}</code>"
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
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML,
        )

    async def search_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        data = query.data.split(":")
        action = data[0]
        requester_id = int(data[1])

        if query.from_user.id != requester_id:
            await query.answer("❌ This search was made by someone else.", show_alert=True)
            return

        if action == "cancel":
            await query.message.edit_text("❌ Search cancelled.")
            await query.answer()
            return

        index = int(data[2])
        cache_key = f"{requester_id}:{query.message.chat.id}"
        cached = search_cache.get(cache_key)

        if not cached:
            await query.answer("⚠️ Search results expired. Please search again.", show_alert=True)
            return

        results = cached["results"]
        if index >= len(results):
            await query.answer("⚠️ Invalid selection.", show_alert=True)
            return

        chosen = results[index]
        title_safe = html.escape(chosen["title"])
        channel_safe = html.escape(chosen["channel"])

        if action == "play":
            if not cached["is_group"]:
                await query.answer("❗ /play only works in group chats.", show_alert=True)
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
            label = "🎵 <b>Now Playing</b>" if position == 1 else f"📋 <b>Added to Queue</b> (#{position})"
            await query.message.edit_text(
                f"{label}\n\n"
                f"🎶 <b>{title_safe}</b>\n"
                f"👤 {channel_safe}\n"
                f"⏱ <code>{format_duration(chosen['duration'])}</code>\n"
                f"🔗 <a href=\"{chosen['webpage_url']}\">Watch on YouTube</a>"
                + vc_note,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
            )
            await query.answer("Added to queue!")

        elif action == "dl":
            await query.answer("⬇️ Starting download...")
            await query.message.edit_text(
                f"⬇️ Downloading <b>{title_safe}</b>...\nThis may take a moment.",
                parse_mode=ParseMode.HTML
            )
            try:
                from handlers.download import download_audio, format_duration as fd, format_size
                from config import DOWNLOAD_DIR, AUDIO_QUALITY
                from database import get_session as gs, DownloadedSong
                from datetime import datetime
                import os

                result = await download_audio(chosen["webpage_url"], DOWNLOAD_DIR, AUDIO_QUALITY)
                filepath = result["filename"]

                if not os.path.exists(filepath):
                    await query.message.edit_text("❌ Download failed. File could not be saved.")
                    return

                file_size = os.path.getsize(filepath)
                db = gs()
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

                await query.message.edit_text(
                    f"📤 Uploading <b>{html.escape(result['title'])}</b>...",
                    parse_mode=ParseMode.HTML
                )
                with open(filepath, "rb") as f:
                    await query.message.reply_audio(
                        audio=f,
                        title=result["title"],
                        duration=result["duration"],
                        caption=(
                            f"🎵 <b>{html.escape(result['title'])}</b>\n"
                            f"⏱ Duration: <code>{fd(result['duration'])}</code>\n"
                            f"📦 Size: <code>{format_size(file_size)}</code>"
                        ),
                        parse_mode=ParseMode.HTML,
                    )
                await query.message.delete()
            except Exception as e:
                logger.error(f"Search download error: {e}")
                await query.message.edit_text(f"❌ Download failed.\n<code>{html.escape(str(e)[:200])}</code>", parse_mode=ParseMode.HTML)

        search_cache.pop(cache_key, None)

    app.add_handler(CommandHandler("search", search_command))
    app.add_handler(CallbackQueryHandler(search_callback, pattern=r"^(play|dl|cancel):"))
