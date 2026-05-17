from database import get_session, User
from config import BOT_OWNER, SUDO_USERS
import logging

logger = logging.getLogger(__name__)


def is_owner_or_sudo(user_id: int) -> bool:
    return user_id == BOT_OWNER or user_id in SUDO_USERS


async def check_banned(user_id: int) -> bool:
    """Returns True if user is banned (and not owner/sudo)."""
    if is_owner_or_sudo(user_id):
        return False
    try:
        db = get_session()
        try:
            user = db.query(User).filter_by(user_id=user_id).first()
            return bool(user and user.is_banned)
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"check_banned DB error: {e}")
        return False
