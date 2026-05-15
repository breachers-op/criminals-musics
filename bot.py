import logging
from pyrogram import Client, idle
from pyrogram.types import BotCommand
from config import BOT_TOKEN, API_ID, API_HASH, check_config
from database import init_db
from handlers.start import register_start_handlers
from handlers.music import register_music_handlers
from handlers.download import register_download_handlers
from handlers.playlist import register_playlist_handlers
from handlers.admin import register_admin_handlers
from handlers.search import register_search_handlers
from handlers.lyrics import register_lyrics_handlers
from handlers.nowplaying import register_nowplaying_handlers
from userbot import userbot

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Client(
    "criminals_musics",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    workers=24
)

COMMANDS = [
    BotCommand("start", "Start the bot"),
    BotCommand("help", "Get help"),
    BotCommand("play", "Play music in voice chat"),
    BotCommand("pause", "Pause current music"),
    BotCommand("resume", "Resume music"),
    BotCommand("stop", "Stop music and leave voice chat"),
    BotCommand("skip", "Skip current song"),
    BotCommand("queue", "View current queue"),
    BotCommand("playlist", "Manage playlists"),
    BotCommand("download", "Download music"),
    BotCommand("downloads", "View downloaded songs"),
    BotCommand("search", "Search YouTube and pick a result"),
    BotCommand("nowplaying", "Show current song details"),
    BotCommand("lyrics", "Get lyrics for a song"),
    BotCommand("ping", "Check bot status"),
]

register_start_handlers(app)
register_music_handlers(app)
register_download_handlers(app)
register_playlist_handlers(app)
register_admin_handlers(app)
register_search_handlers(app)
register_lyrics_handlers(app)
register_nowplaying_handlers(app)


async def set_commands():
    try:
        await app.set_bot_commands(COMMANDS)
        logger.info("Bot commands set successfully!")
    except Exception as e:
        logger.error(f"Error setting commands: {e}")


async def main():
    try:
        check_config()
        logger.info("Configuration check passed!")

        init_db()
        logger.info("Database initialized!")

        await app.start()
        logger.info("Bot started successfully!")

        if userbot:
            await userbot.start()
            me = await userbot.get_me()
            logger.info(f"Userbot started as: {me.first_name} (@{me.username})")

            from handlers.voice import call_py
            if call_py:
                await call_py.start()
                logger.info("PyTgCalls started — voice streaming enabled!")

        await set_commands()
        await idle()

    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        raise
    finally:
        if userbot:
            from handlers.voice import call_py
            if call_py:
                try:
                    await call_py.stop()
                except Exception:
                    pass
            try:
                await userbot.stop()
            except Exception:
                pass
        await app.stop()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
