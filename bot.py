import logging
from pyrogram import Client
from pyrogram.types import BotCommand
from config import BOT_TOKEN, API_ID, API_HASH, check_config
from database import init_db

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize bot
app = Client(
    "criminals_musics",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    workers=24
)

# Bot commands
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
    BotCommand("ping", "Check bot status"),
]

@app.on_message()
async def handle_start(client, message):
    """Placeholder for message handling"""
    pass

async def set_commands():
    """Set bot commands"""
    try:
        await app.set_bot_commands(COMMANDS)
        logger.info("Bot commands set successfully!")
    except Exception as e:
        logger.error(f"Error setting commands: {e}")

async def main():
    """Main bot function"""
    try:
        # Check configuration
        check_config()
        logger.info("Configuration check passed!")
        
        # Initialize database
        init_db()
        logger.info("Database initialized!")
        
        # Start the bot
        await app.start()
        logger.info("🤖 Bot started successfully!")
        
        # Set bot commands
        await set_commands()
        
        # Keep bot running
        await app.idle()
        
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        raise
    finally:
        await app.stop()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
