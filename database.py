from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from config import DATABASE_URL

# Create database engine
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)

# Base class for models
Base = declarative_base()

# User Model
class User(Base):
    __tablename__ = "users"
    
    user_id = Column(Integer, primary_key=True, unique=True, index=True)
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    is_sudo = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<User {self.user_id}>"

# Playlist Model
class Playlist(Base):
    __tablename__ = "playlists"
    
    playlist_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, index=True)
    playlist_name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<Playlist {self.playlist_name}>"

# Playlist Songs Model
class PlaylistSong(Base):
    __tablename__ = "playlist_songs"
    
    song_id = Column(Integer, primary_key=True, autoincrement=True)
    playlist_id = Column(Integer, index=True)
    song_title = Column(String, nullable=False)
    song_url = Column(String, nullable=False)
    duration = Column(Integer, nullable=True)  # in seconds
    added_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<PlaylistSong {self.song_title}>"

# Downloaded Songs Model
class DownloadedSong(Base):
    __tablename__ = "downloaded_songs"
    
    download_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, index=True)
    song_title = Column(String, nullable=False)
    song_url = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_size = Column(Integer, nullable=True)  # in bytes
    duration = Column(Integer, nullable=True)  # in seconds
    downloaded_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<DownloadedSong {self.song_title}>"

# Voice Chat Session Model
class VoiceChatSession(Base):
    __tablename__ = "voice_chat_sessions"
    
    session_id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(Integer, index=True)
    is_playing = Column(Boolean, default=False)
    current_song = Column(String, nullable=True)
    current_song_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<VoiceChatSession {self.chat_id}>"

# Create all tables
def init_db():
    Base.metadata.create_all(bind=engine)
    print("Database initialized successfully!")

# Get session
def get_session():
    return SessionLocal()
