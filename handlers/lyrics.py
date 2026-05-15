from pyrogram import Client, filters
from pyrogram.types import Message
from handlers.filters import not_banned
from database import get_session, VoiceChatSession
import asyncio
import requests
import logging
import re

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
            data = resp.json()
            return data.get("lyrics")
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


def register_lyrics_handlers(app: Client):

    @app.on_message(filters.command("lyrics") & (filters.private | filters.group) & not_banned)
    async def lyrics_command(client: Client, message: Message):
        args = message.text.split(None, 1)
        query = None
        source_label = None

        if len(args) >= 2:
            query = args[1].strip()
            source_label = query
        else:
            if message.chat.type.value in ("group", "supergroup"):
                db = get_session()
                try:
                    record = db.query(VoiceChatSession).filter_by(
                        chat_id=message.chat.id
                    ).first()
                    if record and record.current_song:
                        query = record.current_song
                        source_label = record.current_song
                except Exception:
                    pass
                finally:
                    db.close()

            if not query:
                await message.reply_text(
                    "🎵 **Usage:**\n"
                    "• `/lyrics <song name>` — Get lyrics for any song\n"
                    "• `/lyrics` in a group — Get lyrics for the currently playing song"
                )
                return

        status_msg = await message.reply_text(f"🔎 Fetching lyrics for **{source_label}**...")

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
                f"❌ Lyrics not found for **{source_label}**.\n\n"
                "Try using the format: `/lyrics Artist - Song Title`"
            )
            return

        lyrics = lyrics.strip()
        header = f"🎵 **{display_title}**"
        if display_artist:
            header += f"\n👤 **{display_artist}**"
        header += "\n" + "─" * 30 + "\n\n"

        chunks = chunk_text(lyrics)

        await status_msg.edit_text(header + chunks[0])

        for chunk in chunks[1:]:
            await message.reply_text(chunk)
