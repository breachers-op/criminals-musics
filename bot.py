import logging
import asyncio
from config import BOT_TOKEN, check_config
from database import init_db
from userbot import userbot
from telegram import BotCommand
from telegram.ext import Application

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    check_config()
    logger.info("Configuration check passed!")

    init_db()
    logger.info("Database initialized!")

    ptb_app = Application.builder().token(BOT_TOKEN).build()

    from handlers.start import register_start_handlers
    from handlers.music import register_music_handlers
    from handlers.download import register_download_handlers
    from handlers.playlist import register_playlist_handlers
    from handlers.admin import register_admin_handlers
    from handlers.search import register_search_handlers
    from handlers.lyrics import register_lyrics_handlers
    from handlers.nowplaying import register_nowplaying_handlers

    register_start_handlers(ptb_app)
    register_music_handlers(ptb_app)
    register_download_handlers(ptb_app)
    register_playlist_handlers(ptb_app)
    register_admin_handlers(ptb_app)
    register_search_handlers(ptb_app)
    register_lyrics_handlers(ptb_app)
    register_nowplaying_handlers(ptb_app)

    if userbot:
        await userbot.start()
        me = await userbot.get_me()
        logger.info(f"Userbot started as: {me.first_name} (@{me.username})")

        from handlers.voice import call_py
        if call_py:
            await call_py.start()
            logger.info("PyTgCalls started — voice streaming enabled!")

    await ptb_app.initialize()
    await ptb_app.start()
    await ptb_app.updater.start_polling(drop_pending_updates=True)
    logger.info("Bot started via HTTP polling!")

    try:
        await ptb_app.bot.set_my_commands([
            BotCommand("start", "Start the bot"),
            BotCommand("help", "Get help"),
            BotCommand("play", "Play music in voice chat"),
            BotCommand("pause", "Pause music"),
            BotCommand("resume", "Resume music"),
            BotCommand("stop", "Stop music"),
            BotCommand("skip", "Skip current song"),
            BotCommand("queue", "View queue"),
            BotCommand("search", "Search YouTube"),
            BotCommand("playlist", "Manage playlists"),
            BotCommand("download", "Download a song as MP3"),
            BotCommand("downloads", "View your downloads"),
            BotCommand("lyrics", "Get lyrics for a song"),
            BotCommand("ping", "Check bot status"),
        ])
        logger.info("Bot commands set successfully!")
    except Exception as e:
        logger.error(f"Error setting commands: {e}")

    try:
        await asyncio.Event().wait()
    finally:
        await ptb_app.updater.stop()
        await ptb_app.stop()
        await ptb_app.shutdown()
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


if __name__ == "__main__":
    asyncio.run(main())
