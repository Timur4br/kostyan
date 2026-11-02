from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))


class Location(Base):
    __tablename__ = 'locations'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default='')


class Camera(Base):
    __tablename__ = 'cameras'
    id: Mapped[int] = mapped_column(primary_key=True)
    location_id: Mapped[int] = mapped_column(ForeignKey('locations.id'))
    name: Mapped[str] = mapped_column(String(120))
    resolution: Mapped[str] = mapped_column(String(30))
    fps: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(30), default='demo')


class ObjectType(Base):
    __tablename__ = 'object_types'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    aliases: Mapped[str] = mapped_column(Text)


class TrackedObject(Base):
    __tablename__ = 'objects'
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    object_type_id: Mapped[int] = mapped_column(ForeignKey('object_types.id'))
    name: Mapped[str] = mapped_column(String(120))
    color: Mapped[str] = mapped_column(String(20))
    demo_x: Mapped[int] = mapped_column(Integer)
    demo_y: Mapped[int] = mapped_column(Integer)


class VideoSegment(Base):
    __tablename__ = 'video_segments'
    id: Mapped[int] = mapped_column(primary_key=True)
    camera_id: Mapped[int] = mapped_column(ForeignKey('cameras.id'))
    duration_seconds: Mapped[float] = mapped_column(Float)
    source_kind: Mapped[str] = mapped_column(String(30), default='synthetic')
    storage_reference: Mapped[str | None] = mapped_column(Text, nullable=True)


class EventType(Base):
    __tablename__ = 'event_types'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)


class DetectionEvent(Base):
    __tablename__ = 'events'
    __table_args__ = (UniqueConstraint('object_id', 'camera_id', 'observed_at', name='uq_detection'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    object_id: Mapped[str] = mapped_column(ForeignKey('objects.id'), index=True)
    camera_id: Mapped[int] = mapped_column(ForeignKey('cameras.id'), index=True)
    location_id: Mapped[int] = mapped_column(ForeignKey('locations.id'))
    event_type_id: Mapped[int] = mapped_column(ForeignKey('event_types.id'))
    video_segment_id: Mapped[int] = mapped_column(ForeignKey('video_segments.id'))
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    confidence: Mapped[float] = mapped_column(Float)
    description: Mapped[str] = mapped_column(Text)


class SearchHistory(Base):
    __tablename__ = 'search_history'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    query: Mapped[str] = mapped_column(String(300))
    result_count: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
