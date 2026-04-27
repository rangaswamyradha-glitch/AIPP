# src/database.py
"""
SQLite database — stores trips, photos, scores, ratings.
Single source of truth for all app state.
"""
from sqlalchemy import (
    create_engine, Column, String, Float,
    Integer, Boolean, DateTime, Text, JSON
)
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
import os

DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "data", "db", "picker.db"
)

engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
Base = declarative_base()
Session = sessionmaker(bind=engine)


class Trip(Base):
    __tablename__ = "trips"
    id           = Column(String, primary_key=True)
    name         = Column(String, nullable=False)
    location     = Column(String)
    folder_path  = Column(String)
    photo_count  = Column(Integer, default=0)
    processed    = Column(Boolean, default=False)
    created_at   = Column(DateTime, default=datetime.now)
    processed_at = Column(DateTime)


class Photo(Base):
    __tablename__ = "photos"
    id               = Column(String, primary_key=True)
    trip_id          = Column(String, nullable=False)
    filename         = Column(String, nullable=False)
    filepath         = Column(String, nullable=False)
    thumbnail_path   = Column(String)

    # Classification
    category         = Column(String)
    ai_confidence    = Column(Float, default=0.0)

    # Scores (0–100)
    blur_score       = Column(Float, default=0.0)
    exposure_score   = Column(Float, default=0.0)
    composition_score= Column(Float, default=0.0)
    ai_score         = Column(Float, default=0.0)
    composite_score  = Column(Float, default=0.0)

    # Score breakdown
    score_breakdown  = Column(JSON)

    # Tier
    tier             = Column(String)  # great/good/review/delete
    needs_review     = Column(Boolean, default=False)
    auto_deleted     = Column(Boolean, default=False)
    skip_reason      = Column(String)

    # AI outputs
    ai_explanation   = Column(Text)
    edit_suggestions = Column(JSON)

    # EXIF
    exif_iso         = Column(Integer)
    exif_aperture    = Column(Float)
    exif_shutter     = Column(String)
    exif_focal_len   = Column(Float)
    exif_camera      = Column(String)
    exif_lens        = Column(String)
    exif_date        = Column(String)
    image_width      = Column(Integer)
    image_height     = Column(Integer)

    # User
    user_rating      = Column(String)  # great/good/delete/None
    user_notes       = Column(Text)
    rated_at         = Column(DateTime)

    created_at       = Column(DateTime, default=datetime.now)


class TasteModel(Base):
    __tablename__ = "taste_models"
    id              = Column(String, primary_key=True)
    version         = Column(Integer, default=1)
    trained_at      = Column(DateTime)
    accuracy        = Column(Float)
    sample_size     = Column(Integer)
    feature_weights = Column(JSON)


def init_db():
    """Create all tables."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    Base.metadata.create_all(engine)


def get_session():
    return Session()