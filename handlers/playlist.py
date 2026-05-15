from pyrogram import Client, filters
from pyrogram.types import Message
from database import get_session, Playlist, PlaylistSong
from handlers.filters import not_banned
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

PLAYLIST_HELP = """
📁 **Playlist Commands**

• `/playlist list` — Show all your playlists
• `/playlist create <name>` — Create a new playlist
• `/playlist add <name> | <song>` — Add a song to a playlist
• `/playlist view <name>` — View songs in a playlist
• `/playlist delete <name>` — Delete a playlist
"""


def register_playlist_handlers(app: Client):

    @app.on_message(filters.command("playlist") & (filters.private | filters.group) & not_banned)
    async def playlist_command(client: Client, message: Message):
        args = message.text.split(None, 2)
        user_id = message.from_user.id if message.from_user else 0

        if len(args) < 2:
            await message.reply_text(PLAYLIST_HELP)
            return

        sub = args[1].lower().strip()

        if sub == "list":
            await _playlist_list(message, user_id)
        elif sub == "create":
            if len(args) < 3:
                await message.reply_text("❗ Usage: `/playlist create <name>`")
                return
            await _playlist_create(message, user_id, args[2].strip())
        elif sub == "add":
            if len(args) < 3 or "|" not in args[2]:
                await message.reply_text(
                    "❗ Usage: `/playlist add <playlist name> | <song name>`\n"
                    "Example: `/playlist add My Mix | Blinding Lights`"
                )
                return
            parts = args[2].split("|", 1)
            await _playlist_add(message, user_id, parts[0].strip(), parts[1].strip())
        elif sub == "view":
            if len(args) < 3:
                await message.reply_text("❗ Usage: `/playlist view <name>`")
                return
            await _playlist_view(message, user_id, args[2].strip())
        elif sub == "delete":
            if len(args) < 3:
                await message.reply_text("❗ Usage: `/playlist delete <name>`")
                return
            await _playlist_delete(message, user_id, args[2].strip())
        else:
            await message.reply_text(PLAYLIST_HELP)


async def _playlist_list(message: Message, user_id: int):
    db = get_session()
    try:
        playlists = db.query(Playlist).filter_by(user_id=user_id).all()
    finally:
        db.close()

    if not playlists:
        await message.reply_text("📁 You have no playlists yet.\nCreate one with `/playlist create <name>`")
        return

    lines = ["📁 **Your Playlists**\n"]
    for pl in playlists:
        db2 = get_session()
        try:
            count = db2.query(PlaylistSong).filter_by(playlist_id=pl.playlist_id).count()
        finally:
            db2.close()
        lines.append(f"• **{pl.playlist_name}** — {count} song(s)")
    await message.reply_text("\n".join(lines))


async def _playlist_create(message: Message, user_id: int, name: str):
    if not name:
        await message.reply_text("❗ Playlist name cannot be empty.")
        return
    db = get_session()
    try:
        existing = db.query(Playlist).filter_by(user_id=user_id, playlist_name=name).first()
        if existing:
            await message.reply_text(f"❌ You already have a playlist named **{name}**.")
            return
        pl = Playlist(user_id=user_id, playlist_name=name, created_at=datetime.utcnow())
        db.add(pl)
        db.commit()
    finally:
        db.close()
    await message.reply_text(f"✅ Playlist **{name}** created!\nAdd songs with `/playlist add {name} | <song>`")


async def _playlist_add(message: Message, user_id: int, playlist_name: str, song_query: str):
    if not song_query:
        await message.reply_text("❗ Song name cannot be empty.")
        return
    db = get_session()
    try:
        pl = db.query(Playlist).filter_by(user_id=user_id, playlist_name=playlist_name).first()
        if not pl:
            await message.reply_text(
                f"❌ Playlist **{playlist_name}** not found.\n"
                "Create it first with `/playlist create <name>`"
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
    await message.reply_text(
        f"✅ Added **{song_query}** to playlist **{playlist_name}**\n"
        f"📋 Playlist now has {count} song(s)."
    )


async def _playlist_view(message: Message, user_id: int, playlist_name: str):
    db = get_session()
    try:
        pl = db.query(Playlist).filter_by(user_id=user_id, playlist_name=playlist_name).first()
        if not pl:
            await message.reply_text(f"❌ Playlist **{playlist_name}** not found.")
            return
        songs = db.query(PlaylistSong).filter_by(playlist_id=pl.playlist_id).all()
    finally:
        db.close()

    if not songs:
        await message.reply_text(
            f"📁 Playlist **{playlist_name}** is empty.\n"
            f"Add songs with `/playlist add {playlist_name} | <song>`"
        )
        return

    lines = [f"📁 **{playlist_name}** ({len(songs)} songs)\n"]
    for i, song in enumerate(songs, 1):
        lines.append(f"`{i}.` {song.song_title}")
    await message.reply_text("\n".join(lines))


async def _playlist_delete(message: Message, user_id: int, playlist_name: str):
    db = get_session()
    try:
        pl = db.query(Playlist).filter_by(user_id=user_id, playlist_name=playlist_name).first()
        if not pl:
            await message.reply_text(f"❌ Playlist **{playlist_name}** not found.")
            return
        db.query(PlaylistSong).filter_by(playlist_id=pl.playlist_id).delete()
        db.delete(pl)
        db.commit()
    finally:
        db.close()
    await message.reply_text(f"🗑 Playlist **{playlist_name}** has been deleted.")
