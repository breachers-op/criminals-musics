from pyrogram import Client, filters
from pyrogram.types import Message
from database import get_session, User
from config import BOT_OWNER, SUDO_USERS
from handlers.filters import owner_only, not_banned
import logging
import asyncio

logger = logging.getLogger(__name__)


def register_admin_handlers(app: Client):

    @app.on_message(filters.command("banned") & ~not_banned)
    async def banned_reply(client: Client, message: Message):
        db = get_session()
        try:
            user = db.query(User).filter_by(user_id=message.from_user.id).first()
            reason = user.ban_reason if user and user.ban_reason else "No reason provided."
        finally:
            db.close()
        await message.reply_text(
            f"🚫 You are **banned** from using this bot.\n"
            f"**Reason:** {reason}\n\n"
            "Contact the bot owner if you think this is a mistake."
        )

    @app.on_message(filters.command("ban") & filters.private & owner_only)
    async def ban_command(client: Client, message: Message):
        args = message.text.split(None, 2)
        if len(args) < 2:
            await message.reply_text(
                "❗ **Usage:** `/ban <user_id> [reason]`\n"
                "Example: `/ban 123456789 Spamming`"
            )
            return
        try:
            target_id = int(args[1])
        except ValueError:
            await message.reply_text("❌ Invalid user ID. Must be a number.")
            return

        if target_id == BOT_OWNER or target_id in SUDO_USERS:
            await message.reply_text("❌ You cannot ban an owner or sudo user.")
            return

        reason = args[2].strip() if len(args) > 2 else "No reason provided."

        db = get_session()
        try:
            user = db.query(User).filter_by(user_id=target_id).first()
            if not user:
                user = User(user_id=target_id, is_banned=True, ban_reason=reason)
                db.add(user)
            else:
                if user.is_banned:
                    await message.reply_text(
                        f"⚠️ User `{target_id}` is already banned.\n"
                        f"**Current reason:** {user.ban_reason}"
                    )
                    return
                user.is_banned = True
                user.ban_reason = reason
            db.commit()
        finally:
            db.close()

        await message.reply_text(
            f"🚫 **User Banned**\n\n"
            f"👤 User ID: `{target_id}`\n"
            f"📝 Reason: {reason}"
        )
        try:
            await client.send_message(
                target_id,
                f"🚫 You have been **banned** from using this bot.\n"
                f"**Reason:** {reason}"
            )
        except Exception:
            pass

    @app.on_message(filters.command("unban") & filters.private & owner_only)
    async def unban_command(client: Client, message: Message):
        args = message.text.split()
        if len(args) < 2:
            await message.reply_text("❗ **Usage:** `/unban <user_id>`")
            return
        try:
            target_id = int(args[1])
        except ValueError:
            await message.reply_text("❌ Invalid user ID. Must be a number.")
            return

        db = get_session()
        try:
            user = db.query(User).filter_by(user_id=target_id).first()
            if not user or not user.is_banned:
                await message.reply_text(f"❌ User `{target_id}` is not banned.")
                return
            user.is_banned = False
            user.ban_reason = None
            db.commit()
        finally:
            db.close()

        await message.reply_text(
            f"✅ **User Unbanned**\n\n"
            f"👤 User ID: `{target_id}`\n"
            f"They can now use the bot again."
        )
        try:
            await client.send_message(target_id, "✅ You have been **unbanned** and can use the bot again.")
        except Exception:
            pass

    @app.on_message(filters.command("banlist") & filters.private & owner_only)
    async def banlist_command(client: Client, message: Message):
        db = get_session()
        try:
            banned = db.query(User).filter_by(is_banned=True).all()
        finally:
            db.close()

        if not banned:
            await message.reply_text("✅ No users are currently banned.")
            return

        lines = [f"🚫 **Banned Users** ({len(banned)} total)\n"]
        for u in banned:
            name = u.first_name or "Unknown"
            reason = u.ban_reason or "No reason"
            lines.append(f"• **{name}** `{u.user_id}` — {reason}")
        await message.reply_text("\n".join(lines))

    @app.on_message(filters.command("broadcast") & filters.private & owner_only)
    async def broadcast_command(client: Client, message: Message):
        if not message.reply_to_message and len(message.text.split(None, 1)) < 2:
            await message.reply_text(
                "📢 **Broadcast Usage:**\n\n"
                "**Option 1** — Reply to any message and send `/broadcast`\n"
                "**Option 2** — `/broadcast <your message text>`\n\n"
                "The message will be sent to all non-banned users who have used the bot."
            )
            return

        if message.reply_to_message:
            broadcast_msg = message.reply_to_message
            use_forward = True
        else:
            text = message.text.split(None, 1)[1]
            use_forward = False

        db = get_session()
        try:
            users = db.query(User).filter_by(is_banned=False).all()
            user_ids = [u.user_id for u in users]
        finally:
            db.close()

        if not user_ids:
            await message.reply_text("❌ No users in the database yet.")
            return

        status_msg = await message.reply_text(
            f"📢 Starting broadcast to **{len(user_ids)}** user(s)...\nThis may take a moment."
        )

        success = 0
        failed = 0
        for user_id in user_ids:
            try:
                if use_forward:
                    await broadcast_msg.forward(user_id)
                else:
                    await client.send_message(user_id, text)
                success += 1
            except Exception as e:
                logger.warning(f"Broadcast failed for user {user_id}: {e}")
                failed += 1
            await asyncio.sleep(0.05)

        await status_msg.edit_text(
            f"📢 **Broadcast Complete**\n\n"
            f"✅ Sent: {success}\n"
            f"❌ Failed: {failed}\n"
            f"👥 Total: {len(user_ids)}"
        )

    @app.on_message(filters.command("stats") & filters.private & owner_only)
    async def stats_command(client: Client, message: Message):
        db = get_session()
        try:
            total_users = db.query(User).count()
            sudo_users = db.query(User).filter_by(is_sudo=True).count()
            banned_users = db.query(User).filter_by(is_banned=True).count()
        finally:
            db.close()

        bot_info = await client.get_me()
        await message.reply_text(
            f"📊 **Bot Statistics**\n\n"
            f"🤖 Bot: @{bot_info.username}\n"
            f"👥 Total Users: `{total_users}`\n"
            f"🛡 Sudo Users: `{sudo_users}`\n"
            f"🚫 Banned Users: `{banned_users}`"
        )

    @app.on_message(filters.command("addsudo") & filters.private & owner_only)
    async def addsudo_command(client: Client, message: Message):
        args = message.text.split()
        if len(args) < 2:
            await message.reply_text("❗ Usage: `/addsudo <user_id>`")
            return
        try:
            target_id = int(args[1])
        except ValueError:
            await message.reply_text("❌ Invalid user ID. Must be a number.")
            return

        db = get_session()
        try:
            user = db.query(User).filter_by(user_id=target_id).first()
            if not user:
                await message.reply_text("❌ User not found. They must /start the bot first.")
                return
            user.is_sudo = True
            db.commit()
        finally:
            db.close()
        await message.reply_text(f"✅ User `{target_id}` has been granted sudo access.")

    @app.on_message(filters.command("removesudo") & filters.private & owner_only)
    async def removesudo_command(client: Client, message: Message):
        args = message.text.split()
        if len(args) < 2:
            await message.reply_text("❗ Usage: `/removesudo <user_id>`")
            return
        try:
            target_id = int(args[1])
        except ValueError:
            await message.reply_text("❌ Invalid user ID. Must be a number.")
            return

        db = get_session()
        try:
            user = db.query(User).filter_by(user_id=target_id).first()
            if not user:
                await message.reply_text("❌ User not found.")
                return
            user.is_sudo = False
            db.commit()
        finally:
            db.close()
        await message.reply_text(f"✅ Sudo access removed from user `{target_id}`.")

    @app.on_message(filters.command("users") & filters.private & owner_only)
    async def users_command(client: Client, message: Message):
        db = get_session()
        try:
            users = db.query(User).order_by(User.last_seen.desc()).limit(20).all()
            total = db.query(User).count()
        finally:
            db.close()

        if not users:
            await message.reply_text("👥 No users yet.")
            return

        lines = [f"👥 **Recent Users** (showing {len(users)} of {total})\n"]
        for u in users:
            name = u.first_name or "Unknown"
            username = f"@{u.username}" if u.username else "no username"
            tags = ""
            if u.is_sudo:
                tags += " 🛡"
            if u.is_banned:
                tags += " 🚫"
            lines.append(f"• **{name}** ({username}) `{u.user_id}`{tags}")
        await message.reply_text("\n".join(lines))
