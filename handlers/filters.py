from pyrogram import filters
from pyrogram.types import Message
from database import get_session, User
from config import BOT_OWNER, SUDO_USERS


def is_owner_or_sudo(user_id: int) -> bool:
    return user_id == BOT_OWNER or user_id in SUDO_USERS


def not_banned_filter(_, __, message: Message) -> bool:
    if not message.from_user:
        return True
    if is_owner_or_sudo(message.from_user.id):
        return True
    db = get_session()
    try:
        user = db.query(User).filter_by(user_id=message.from_user.id).first()
        if user and user.is_banned:
            return False
    finally:
        db.close()
    return True


def owner_filter(_, __, message: Message) -> bool:
    if not message.from_user:
        return False
    return is_owner_or_sudo(message.from_user.id)


not_banned = filters.create(not_banned_filter)
owner_only = filters.create(owner_filter)
