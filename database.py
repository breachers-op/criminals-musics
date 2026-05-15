from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from config import DATABASE_URL

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    user_id = Column(Integer, primary_key=True, unique=True, index=True)
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    is_sudo = Column(Boolean, default=False)
    is_banned = Column(Boolean, default=False)
    ban_reason = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow)
    def __repr__(self): return f"<User {self.user_id}>"

class Playlist(Base):
    __tablename__ = "playlists"
    playlist_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, index=True)
    playlist_name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    def __repr__(self): return f"<Playlist {self.playlist_name}>"

class PlaylistSong(Base):
    __tablename__ = "playlist_songs"
    song_id = Column(Integer, primary_key=True, autoincrement=True)
    playlist_id = Column(Integer, index=True)
    song_title = Column(String, nullable=False)
    song_url = Column(String, nullable=False)
    duration = Column(Integer, nullable=True)
    added_at = Column(DateTime, default=datetime.utcnow)
    def __repr__(self): return f"<PlaylistSong {self.song_title}>"

class DownloadedSong(Base):
    __tablename__ = "downloaded_songs"
    download_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, index=True)
    song_title = Column(String, nullable=False)
    song_url = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_size = Column(Integer, nullable=True)
    duration = Column(Integer, nullable=True)
    downloaded_at = Column(DateTime, default=datetime.utcnow)
    def __repr__(self): return f"<DownloadedSong {self.song_title}>"

class VoiceChatSession(Base):
    __tablename__ = "voice_chat_sessions"
    session_id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(Integer, index=True)
    is_playing = Column(Boolean, default=False)
    current_song = Column(String, nullable=True)
    current_song_url = Column(String, nullable=True)
    current_duration = Column(Integer, nullable=True)
    started_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    def __repr__(self): return f"<VoiceChatSession {self.chat_id}>"

def init_db():
    Base.metadata.create_all(bind=engine)
    _migrate()
    print("Database initialized successfully!")

def _migrate():
    with engine.connect() as conn:
        for sql in [
            "ALTER TABLE users ADD COLUMN is_banned BOOLEAN DEFAULT FALSE",
            "ALTER TABLE users ADD COLUMN ban_reason VARCHAR",
            "ALTER TABLE voice_chat_sessions ADD COLUMN current_duration INTEGER",
            "ALTER TABLE voice_chat_sessions ADD COLUMN started_at TIMESTAMP",
        ]:
            try:
                conn.execute(__import__("sqlalchemy").text(sql))
                conn.commit()
            except Exception:
                pass

def get_session():
    return SessionLocal()
