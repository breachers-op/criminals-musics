import html
import asyncio
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.constants import ParseMode
from database import get_session, User
from config import BOT_OWNER, SUDO_USERS
from handlers.filters import check_banned, is_owner_or_sudo

logger = logging.getLogger(__name__)


def register_admin_handlers(app: Application):

    async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not user or not is_owner_or_sudo(user.id):
            return
        args = update.message.text.split(None, 2)
        if len(args) < 2:
            await update.message.reply_text(
                "❗ <b>Usage:</b> /ban &lt;user_id&gt; [reason]\n"
                "Example: /ban 123456789 Spamming",
                parse_mode=ParseMode.HTML
            )
            return
        try:
            target_id = int(args[1])
        except ValueError:
            await update.message.reply_text("❌ Invalid user ID. Must be a number.")
            return

        if target_id == BOT_OWNER or target_id in SUDO_USERS:
            await update.message.reply_text("❌ You cannot ban an owner or sudo user.")
            return

        reason = args[2].strip() if len(args) > 2 else "No reason provided."

        db = get_session()
        try:
            db_user = db.query(User).filter_by(user_id=target_id).first()
            if not db_user:
                db_user = User(user_id=target_id, is_banned=True, ban_reason=reason)
                db.add(db_user)
            else:
                if db_user.is_banned:
                    await update.message.reply_text(
                        f"⚠️ User <code>{target_id}</code> is already banned.\n"
                        f"<b>Current reason:</b> {html.escape(db_user.ban_reason or '')}",
                        parse_mode=ParseMode.HTML
                    )
                    return
                db_user.is_banned = True
                db_user.ban_reason = reason
            db.commit()
        finally:
            db.close()

        await update.message.reply_text(
            f"🚫 <b>User Banned</b>\n\n"
            f"👤 User ID: <code>{target_id}</code>\n"
            f"📝 Reason: {html.escape(reason)}",
            parse_mode=ParseMode.HTML
        )
        try:
            await context.bot.send_message(
                target_id,
                f"🚫 You have been <b>banned</b> from using this bot.\n"
                f"<b>Reason:</b> {html.escape(reason)}",
                parse_mode=ParseMode.HTML
            )
        except Exception:
            pass

    async def unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not user or not is_owner_or_sudo(user.id):
            return
        args = update.message.text.split()
        if len(args) < 2:
            await update.message.reply_text("❗ <b>Usage:</b> /unban &lt;user_id&gt;", parse_mode=ParseMode.HTML)
            return
        try:
            target_id = int(args[1])
        except ValueError:
            await update.message.reply_text("❌ Invalid user ID. Must be a number.")
            return

        db = get_session()
        try:
            db_user = db.query(User).filter_by(user_id=target_id).first()
            if not db_user or not db_user.is_banned:
                await update.message.reply_text(
                    f"❌ User <code>{target_id}</code> is not banned.", parse_mode=ParseMode.HTML
                )
                return
            db_user.is_banned = False
            db_user.ban_reason = None
            db.commit()
        finally:
            db.close()

        await update.message.reply_text(
            f"✅ <b>User Unbanned</b>\n\n"
            f"👤 User ID: <code>{target_id}</code>\n"
            "They can now use the bot again.",
            parse_mode=ParseMode.HTML
        )
        try:
            await context.bot.send_message(
                target_id,
                "✅ You have been <b>unbanned</b> and can use the bot again.",
                parse_mode=ParseMode.HTML
            )
        except Exception:
            pass

    async def banlist_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not user or not is_owner_or_sudo(user.id):
            return
        db = get_session()
        try:
            banned = db.query(User).filter_by(is_banned=True).all()
        finally:
            db.close()

        if not banned:
            await update.message.reply_text("✅ No users are currently banned.")
            return

        lines = [f"🚫 <b>Banned Users</b> ({len(banned)} total)\n"]
        for u in banned:
            name = html.escape(u.first_name or "Unknown")
            reason = html.escape(u.ban_reason or "No reason")
            lines.append(f"• <b>{name}</b> <code>{u.user_id}</code> — {reason}")
        await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)

    async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not user or not is_owner_or_sudo(user.id):
            return
        msg = update.message
        has_reply = msg.reply_to_message is not None
        args = msg.text.split(None, 1)
        if not has_reply and len(args) < 2:
            await msg.reply_text(
                "📢 <b>Broadcast Usage:</b>\n\n"
                "<b>Option 1</b> — Reply to any message and send /broadcast\n"
                "<b>Option 2</b> — /broadcast &lt;your message text&gt;\n\n"
                "The message will be sent to all non-banned users who have used the bot.",
                parse_mode=ParseMode.HTML
            )
            return

        db = get_session()
        try:
            users = db.query(User).filter_by(is_banned=False).all()
            user_ids = [u.user_id for u in users]
        finally:
            db.close()

        if not user_ids:
            await msg.reply_text("❌ No users in the database yet.")
            return

        status_msg = await msg.reply_text(
            f"📢 Starting broadcast to <b>{len(user_ids)}</b> user(s)...\nThis may take a moment.",
            parse_mode=ParseMode.HTML
        )

        success = 0
        failed = 0
        for uid in user_ids:
            try:
                if has_reply:
                    await context.bot.forward_message(
                        chat_id=uid,
                        from_chat_id=msg.chat_id,
                        message_id=msg.reply_to_message.message_id
                    )
                else:
                    await context.bot.send_message(uid, args[1], parse_mode=ParseMode.HTML)
                success += 1
            except Exception as e:
                logger.warning(f"Broadcast failed for {uid}: {e}")
                failed += 1
            await asyncio.sleep(0.05)

        await status_msg.edit_text(
            f"📢 <b>Broadcast Complete</b>\n\n"
            f"✅ Sent: {success}\n"
            f"❌ Failed: {failed}\n"
            f"👥 Total: {len(user_ids)}",
            parse_mode=ParseMode.HTML
        )

    async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not user or not is_owner_or_sudo(user.id):
            return
        db = get_session()
        try:
            total_users = db.query(User).count()
            sudo_users = db.query(User).filter_by(is_sudo=True).count()
            banned_users = db.query(User).filter_by(is_banned=True).count()
        finally:
            db.close()

        bot_info = await context.bot.get_me()
        await update.message.reply_text(
            f"📊 <b>Bot Statistics</b>\n\n"
            f"🤖 Bot: @{html.escape(bot_info.username or '')}\n"
            f"👥 Total Users: <code>{total_users}</code>\n"
            f"🛡 Sudo Users: <code>{sudo_users}</code>\n"
            f"🚫 Banned Users: <code>{banned_users}</code>",
            parse_mode=ParseMode.HTML
        )

    async def addsudo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not user or not is_owner_or_sudo(user.id):
            return
        args = update.message.text.split()
        if len(args) < 2:
            await update.message.reply_text("❗ Usage: /addsudo &lt;user_id&gt;", parse_mode=ParseMode.HTML)
            return
        try:
            target_id = int(args[1])
        except ValueError:
            await update.message.reply_text("❌ Invalid user ID. Must be a number.")
            return

        db = get_session()
        try:
            db_user = db.query(User).filter_by(user_id=target_id).first()
            if not db_user:
                await update.message.reply_text(
                    "❌ User not found. They must /start the bot first."
                )
                return
            db_user.is_sudo = True
            db.commit()
        finally:
            db.close()
        await update.message.reply_text(
            f"✅ User <code>{target_id}</code> has been granted sudo access.",
            parse_mode=ParseMode.HTML
        )

    async def removesudo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not user or not is_owner_or_sudo(user.id):
            return
        args = update.message.text.split()
        if len(args) < 2:
            await update.message.reply_text("❗ Usage: /removesudo &lt;user_id&gt;", parse_mode=ParseMode.HTML)
            return
        try:
            target_id = int(args[1])
        except ValueError:
            await update.message.reply_text("❌ Invalid user ID. Must be a number.")
            return

        db = get_session()
        try:
            db_user = db.query(User).filter_by(user_id=target_id).first()
            if not db_user:
                await update.message.reply_text("❌ User not found.")
                return
            db_user.is_sudo = False
            db.commit()
        finally:
            db.close()
        await update.message.reply_text(
            f"✅ Sudo access removed from user <code>{target_id}</code>.",
            parse_mode=ParseMode.HTML
        )

    async def users_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not user or not is_owner_or_sudo(user.id):
            return
        db = get_session()
        try:
            users = db.query(User).order_by(User.last_seen.desc()).limit(20).all()
            total = db.query(User).count()
        finally:
            db.close()

        if not users:
            await update.message.reply_text("👥 No users yet.")
            return

        lines = [f"👥 <b>Recent Users</b> (showing {len(users)} of {total})\n"]
        for u in users:
            name = html.escape(u.first_name or "Unknown")
            username = f"@{html.escape(u.username)}" if u.username else "no username"
            tags = ""
            if u.is_sudo:
                tags += " 🛡"
            if u.is_banned:
                tags += " 🚫"
            lines.append(f"• <b>{name}</b> ({username}) <code>{u.user_id}</code>{tags}")
        await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)

    app.add_handler(CommandHandler("ban", ban_command))
    app.add_handler(CommandHandler("unban", unban_command))
    app.add_handler(CommandHandler("banlist", banlist_command))
    app.add_handler(CommandHandler("broadcast", broadcast_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("addsudo", addsudo_command))
    app.add_handler(CommandHandler("removesudo", removesudo_command))
    app.add_handler(CommandHandler("users", users_command))
