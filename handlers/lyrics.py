import html
import asyncio
import logging
import re
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.constants import ParseMode
from database import get_session, VoiceChatSession
from handlers.filters import check_banned

logger = logging.getLogger(__name__)

LYRICS_API = "https://api.lyrics.ovh/v1/{artist}/{title}"
SUGGEST_API = "https://api.lyrics.ovh/suggest/{query}"


def _parse_title(raw: str):
    cleaned = re.sub(r"\(.*?\)|\[.*?\]", "", raw).strip()
    for sep in [" - ", " – ", " — "]:
        if sep in cleaned:
            parts = cleaned.split(sep, 1)
            return parts[0].strip(), parts[1].strip()
    return None, cleaned.strip()


def _fetch_lyrics(artist: str, title: str):
    try:
        url = LYRICS_API.format(
            artist=requests.utils.quote(artist),
            title=requests.utils.quote(title)
        )
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            return resp.json().get("lyrics")
    except Exception as e:
        logger.warning(f"Lyrics fetch error ({artist} - {title}): {e}")
    return None


def _search_and_fetch(query: str):
    try:
        resp = requests.get(
            SUGGEST_API.format(query=requests.utils.quote(query)),
            timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            hits = data.get("data", [])
            if hits:
                best = hits[0]
                artist = best.get("artist", {}).get("name", "")
                title = best.get("title", "")
                lyrics = _fetch_lyrics(artist, title)
                return artist, title, lyrics
    except Exception as e:
        logger.warning(f"Lyrics suggest error ({query}): {e}")
    return None, query, None


def chunk_text(text: str, size: int = 4000):
    lines = text.split("\n")
    chunks = []
    current = []
    current_len = 0
    for line in lines:
        if current_len + len(line) + 1 > size:
            chunks.append("\n".join(current))
            current = [line]
            current_len = len(line)
        else:
            current.append(line)
            current_len += len(line) + 1
    if current:
        chunks.append("\n".join(current))
    return chunks


def register_lyrics_handlers(app: Application):

    async def lyrics_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        chat = update.effective_chat
        if not user or await check_banned(user.id):
            return

        args = update.message.text.split(None, 1)
        query = None
        source_label = None

        if len(args) >= 2:
            query = args[1].strip()
            source_label = query
        else:
            if chat.type in ("group", "supergroup"):
                db = get_session()
                try:
                    record = db.query(VoiceChatSession).filter_by(chat_id=chat.id).first()
                    if record and record.current_song:
                        query = record.current_song
                        source_label = record.current_song
                except Exception:
                    pass
                finally:
                    db.close()

            if not query:
                await update.message.reply_text(
                    "🎵 <b>Usage:</b>\n"
                    "• /lyrics &lt;song name&gt; — Get lyrics for any song\n"
                    "• /lyrics in a group — Get lyrics for the currently playing song",
                    parse_mode=ParseMode.HTML
                )
                return

        status_msg = await update.message.reply_text(
            f"🔎 Fetching lyrics for <b>{html.escape(source_label)}</b>...",
            parse_mode=ParseMode.HTML
        )

        loop = asyncio.get_event_loop()
        artist, title = _parse_title(query)

        lyrics = None
        display_artist = artist
        display_title = title

        if artist:
            lyrics = await loop.run_in_executor(None, _fetch_lyrics, artist, title)

        if not lyrics:
            display_artist, display_title, lyrics = await loop.run_in_executor(
                None, _search_and_fetch, query
            )

        if not lyrics:
            await status_msg.edit_text(
                f"❌ Lyrics not found for <b>{html.escape(source_label)}</b>.\n\n"
                "Try using the format: /lyrics Artist - Song Title",
                parse_mode=ParseMode.HTML
            )
            return

        lyrics = lyrics.strip()
        header = f"🎵 <b>{html.escape(display_title or '')}</b>"
        if display_artist:
            header += f"\n👤 <b>{html.escape(display_artist)}</b>"
        header += "\n" + "─" * 30 + "\n\n"

        chunks = chunk_text(html.escape(lyrics))

        await status_msg.edit_text(header + chunks[0], parse_mode=ParseMode.HTML)

        for chunk in chunks[1:]:
            await update.message.reply_text(chunk, parse_mode=ParseMode.HTML)

    app.add_handler(CommandHandler("lyrics", lyrics_command))
