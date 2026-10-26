import enum
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, DateTime, Boolean, Enum, LargeBinary, Text
)

from app.database import Base


class UserRole(str, enum.Enum):
    admin = "admin"
    operator = "operator"


class User(Base):
    """Authorized personnel who may log into the app."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, index=True, nullable=False)
    email = Column(String(128), unique=True, index=True, nullable=True)
    hashed_password = Column(String(255), nullable=False)  # Argon2id hash
    role = Column(Enum(UserRole), default=UserRole.operator, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Basic brute-force protection
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)


class EventCategory(str, enum.Enum):
    crime = "crime"
    traffic = "traffic"


# class Event(Base):
#     """
#     An AI-verified event (Tier 1/Tier 2 detection) with its encrypted
#     10-second evidence clip. clip_encrypted stores AES-256 ciphertext
#     as BYTEA/BLOB, per the persistence layer design.
#     """
#     __tablename__ = "events"

#     id = Column(Integer, primary_key=True, index=True)
#     camera_id = Column(String(64), nullable=False, default="hikvision-01")
#     category = Column(Enum(EventCategory), nullable=False)
#     event_type = Column(String(128), nullable=False)  # e.g. "Illegal U-Turn", "Fighting"
#     description = Column(Text, nullable=True)
#     confidence = Column(Integer, nullable=True)  # 0-100

#     clip_encrypted = Column(LargeBinary, nullable=True)  # AES-256 ciphertext
#     clip_iv = Column(LargeBinary, nullable=True)          # AES-GCM/CBC IV/nonce

#     occurred_at = Column(DateTime, default=datetime.utcnow, index=True)

class Event(Base):
    """
    An AI-verified event with its encrypted 10-second evidence clip.
    Stored as a TimescaleDB hypertable partitioned by occurred_at.
    """
    __tablename__ = "events"

    # Composite primary key (id, occurred_at): TimescaleDB requires the
    # time column to be part of any unique/primary key on a hypertable.
    id = Column(Integer, primary_key=True, autoincrement=True)
    occurred_at = Column(DateTime, primary_key=True, default=datetime.utcnow)

    camera_id = Column(String(64), nullable=False, default="hikvision-01")
    category = Column(Enum(EventCategory), nullable=False)
    event_type = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)
    confidence = Column(Integer, nullable=True)  # 0-100

    clip_encrypted = Column(LargeBinary, nullable=True)  # AES-256-GCM ciphertext
    clip_iv = Column(LargeBinary, nullable=True)          # nonce

class DeviceHeartbeat(Base):
    """Latest MQTT heartbeat status for an edge device (Raspberry Pi)."""
    __tablename__ = "device_heartbeats"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String(64), unique=True, index=True, nullable=False)
    status = Column(String(16), default="offline", nullable=False)  # "online" / "offline"
    last_seen = Column(DateTime, default=datetime.utcnow)
