"""
Userbot client for voice chat streaming.
Requires STRING_SESSION secret to be set (generate with generate_session.py).
"""
from config import API_ID, API_HASH, STRING_SESSION
from pyrogram import Client
import logging

logger = logging.getLogger(__name__)

userbot = None

if STRING_SESSION:
    userbot = Client(
        name="userbot_session",
        api_id=API_ID,
        api_hash=API_HASH,
        session_string=STRING_SESSION,
        in_memory=True,
    )
    logger.info("Userbot client created from STRING_SESSION.")
else:
    logger.warning(
        "STRING_SESSION not set — voice chat streaming disabled. "
        "Run generate_session.py to create one."
    )
