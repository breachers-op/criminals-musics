"""
Voice chat streaming manager using pytgcalls + userbot.
All functions return True on success, False if disabled or on error.
"""
import asyncio
import logging
import yt_dlp
from userbot import userbot

logger = logging.getLogger(__name__)

call_py = None

if userbot:
    try:
        from pytgcalls import PyTgCalls
        from pytgcalls.types import MediaStream, AudioQuality
        call_py = PyTgCalls(userbot)
        logger.info("PyTgCalls instance created.")
    except ImportError:
        logger.error("py-tgcalls not installed. Run: pip install py-tgcalls")


def _make_stream(stream_url: str):
    from pytgcalls.types import MediaStream, AudioQuality
    return MediaStream(stream_url, audio_parameters=AudioQuality.STUDIO)


async def _get_audio_url(youtube_url: str) -> str | None:
    loop = asyncio.get_event_loop()
    def _fetch():
        ydl_opts = {
            "format": "bestaudio[ext=m4a]/bestaudio/best",
            "quiet": True,
            "no_warnings": True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=False)
            if not info:
                return None
            if "url" in info:
                return info["url"]
            formats = info.get("formats", [])
            if formats:
                return formats[-1].get("url")
            return None
    return await loop.run_in_executor(None, _fetch)


async def play_in_vc(chat_id: int, youtube_url: str) -> bool:
    if not call_py:
        return False
    try:
        stream_url = await _get_audio_url(youtube_url)
        if not stream_url:
            logger.error(f"Could not get stream URL for {youtube_url}")
            return False
        await call_py.play(chat_id, _make_stream(stream_url))
        logger.info(f"Streaming started in chat {chat_id}")
        return True
    except Exception as e:
        logger.error(f"play_in_vc error [{chat_id}]: {e}")
        return False


async def skip_in_vc(chat_id: int, youtube_url: str) -> bool:
    if not call_py:
        return False
    try:
        stream_url = await _get_audio_url(youtube_url)
        if not stream_url:
            return False
        await call_py.change_stream(chat_id, _make_stream(stream_url))
        logger.info(f"Stream changed in chat {chat_id}")
        return True
    except Exception as e:
        logger.error(f"skip_in_vc error [{chat_id}]: {e}")
        return False


async def pause_in_vc(chat_id: int) -> bool:
    if not call_py:
        return False
    try:
        await call_py.pause_stream(chat_id)
        return True
    except Exception as e:
        logger.error(f"pause_in_vc error [{chat_id}]: {e}")
        return False


async def resume_in_vc(chat_id: int) -> bool:
    if not call_py:
        return False
    try:
        await call_py.resume_stream(chat_id)
        return True
    except Exception as e:
        logger.error(f"resume_in_vc error [{chat_id}]: {e}")
        return False


async def stop_in_vc(chat_id: int) -> bool:
    if not call_py:
        return False
    try:
        await call_py.leave_group_call(chat_id)
        logger.info(f"Left voice chat in {chat_id}")
        return True
    except Exception as e:
        logger.error(f"stop_in_vc error [{chat_id}]: {e}")
        return False


def is_vc_active() -> bool:
    return call_py is not None
