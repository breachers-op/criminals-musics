import html
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.constants import ParseMode
from database import get_session, Playlist, PlaylistSong
from handlers.filters import check_banned

logger = logging.getLogger(__name__)

PLAYLIST_HELP = (
    "📁 <b>Playlist Commands</b>\n\n"
    "• /playlist list — Show all your playlists\n"
    "• /playlist create &lt;name&gt; — Create a new playlist\n"
    "• /playlist add &lt;name&gt; | &lt;song&gt; — Add a song to a playlist\n"
    "• /playlist view &lt;name&gt; — View songs in a playlist\n"
    "• /playlist delete &lt;name&gt; — Delete a playlist"
)


def register_playlist_handlers(app: Application):

    async def playlist_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not user or await check_banned(user.id):
            return
        args = update.message.text.split(None, 2)
        user_id = user.id

        if len(args) < 2:
            await update.message.reply_text(PLAYLIST_HELP, parse_mode=ParseMode.HTML)
            return

        sub = args[1].lower().strip()

        if sub == "list":
            await _playlist_list(update, user_id)
        elif sub == "create":
            if len(args) < 3:
                await update.message.reply_text(
                    "❗ Usage: /playlist create &lt;name&gt;", parse_mode=ParseMode.HTML
                )
                return
            await _playlist_create(update, user_id, args[2].strip())
        elif sub == "add":
            if len(args) < 3 or "|" not in args[2]:
                await update.message.reply_text(
                    "❗ Usage: /playlist add &lt;playlist name&gt; | &lt;song name&gt;\n"
                    "Example: /playlist add My Mix | Blinding Lights",
                    parse_mode=ParseMode.HTML
                )
                return
            parts = args[2].split("|", 1)
            await _playlist_add(update, user_id, parts[0].strip(), parts[1].strip())
        elif sub == "view":
            if len(args) < 3:
                await update.message.reply_text(
                    "❗ Usage: /playlist view &lt;name&gt;", parse_mode=ParseMode.HTML
                )
                return
            await _playlist_view(update, user_id, args[2].strip())
        elif sub == "delete":
            if len(args) < 3:
                await update.message.reply_text(
                    "❗ Usage: /playlist delete &lt;name&gt;", parse_mode=ParseMode.HTML
                )
                return
            await _playlist_delete(update, user_id, args[2].strip())
        else:
            await update.message.reply_text(PLAYLIST_HELP, parse_mode=ParseMode.HTML)

    app.add_handler(CommandHandler("playlist", playlist_command))


async def _playlist_list(update: Update, user_id: int):
    db = get_session()
    try:
        playlists = db.query(Playlist).filter_by(user_id=user_id).all()
    finally:
        db.close()

    if not playlists:
        await update.message.reply_text(
            "📁 You have no playlists yet.\nCreate one with /playlist create &lt;name&gt;",
            parse_mode=ParseMode.HTML
        )
        return

    lines = ["📁 <b>Your Playlists</b>\n"]
    for pl in playlists:
        db2 = get_session()
        try:
            count = db2.query(PlaylistSong).filter_by(playlist_id=pl.playlist_id).count()
        finally:
            db2.close()
        lines.append(f"• <b>{html.escape(pl.playlist_name)}</b> — {count} song(s)")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)


async def _playlist_create(update: Update, user_id: int, name: str):
    if not name:
        await update.message.reply_text("❗ Playlist name cannot be empty.")
        return
    db = get_session()
    try:
        existing = db.query(Playlist).filter_by(user_id=user_id, playlist_name=name).first()
        if existing:
            await update.message.reply_text(
                f"❌ You already have a playlist named <b>{html.escape(name)}</b>.",
                parse_mode=ParseMode.HTML
            )
            return
        pl = Playlist(user_id=user_id, playlist_name=name, created_at=datetime.utcnow())
        db.add(pl)
        db.commit()
    finally:
        db.close()
    await update.message.reply_text(
        f"✅ Playlist <b>{html.escape(name)}</b> created!\n"
        f"Add songs with /playlist add {html.escape(name)} | &lt;song&gt;",
        parse_mode=ParseMode.HTML
    )


async def _playlist_add(update: Update, user_id: int, playlist_name: str, song_query: str):
    if not song_query:
        await update.message.reply_text("❗ Song name cannot be empty.")
        return
    db = get_session()
    try:
        pl = db.query(Playlist).filter_by(user_id=user_id, playlist_name=playlist_name).first()
        if not pl:
            await update.message.reply_text(
                f"❌ Playlist <b>{html.escape(playlist_name)}</b> not found.\n"
                "Create it first with /playlist create &lt;name&gt;",
                parse_mode=ParseMode.HTML
            )
            return
        song = PlaylistSong(
            playlist_id=pl.playlist_id,
            song_title=song_query,
            song_url=f"ytsearch:{song_query}",
            added_at=datetime.utcnow(),
        )
        db.add(song)
        db.commit()
        count = db.query(PlaylistSong).filter_by(playlist_id=pl.playlist_id).count()
    finally:
        db.close()
    await update.message.reply_text(
        f"✅ Added <b>{html.escape(song_query)}</b> to playlist <b>{html.escape(playlist_name)}</b>\n"
        f"📋 Playlist now has {count} song(s).",
        parse_mode=ParseMode.HTML
    )


async def _playlist_view(update: Update, user_id: int, playlist_name: str):
    db = get_session()
    try:
        pl = db.query(Playlist).filter_by(user_id=user_id, playlist_name=playlist_name).first()
        if not pl:
            await update.message.reply_text(
                f"❌ Playlist <b>{html.escape(playlist_name)}</b> not found.",
                parse_mode=ParseMode.HTML
            )
            return
        songs = db.query(PlaylistSong).filter_by(playlist_id=pl.playlist_id).all()
    finally:
        db.close()

    if not songs:
        await update.message.reply_text(
            f"📁 Playlist <b>{html.escape(playlist_name)}</b> is empty.\n"
            f"Add songs with /playlist add {html.escape(playlist_name)} | &lt;song&gt;",
            parse_mode=ParseMode.HTML
        )
        return

    lines = [f"📁 <b>{html.escape(playlist_name)}</b> ({len(songs)} songs)\n"]
    for i, song in enumerate(songs, 1):
        lines.append(f"<code>{i}.</code> {html.escape(song.song_title)}")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)


async def _playlist_delete(update: Update, user_id: int, playlist_name: str):
    db = get_session()
    try:
        pl = db.query(Playlist).filter_by(user_id=user_id, playlist_name=playlist_name).first()
        if not pl:
            await update.message.reply_text(
                f"❌ Playlist <b>{html.escape(playlist_name)}</b> not found.",
                parse_mode=ParseMode.HTML
            )
            return
        db.query(PlaylistSong).filter_by(playlist_id=pl.playlist_id).delete()
        db.delete(pl)
        db.commit()
    finally:
        db.close()
    await update.message.reply_text(
        f"🗑 Playlist <b>{html.escape(playlist_name)}</b> has been deleted.",
        parse_mode=ParseMode.HTML
    )
