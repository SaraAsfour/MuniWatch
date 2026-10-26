from datetime import datetime
from typing import Optional, Literal

from pydantic import BaseModel, EmailStr, Field


# ---------- Auth ----------

class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class RefreshRequest(BaseModel):
    refresh_token: str


class UserCreate(BaseModel):
    username: str
    email: Optional[EmailStr] = None
    password: str = Field(min_length=8)
    role: Literal["admin", "operator"] = "operator"


class UserOut(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    role: str
    is_active: bool

    class Config:
        from_attributes = True


# ---------- Dashboard ----------

class HeartbeatOut(BaseModel):
    device_id: str
    status: str
    last_seen: datetime

    class Config:
        from_attributes = True


class QuickStatsOut(BaseModel):
    vehicles_detected_today: int
    incidents_today: int


class DashboardOut(BaseModel):
    camera_thumbnail_url: str
    quick_stats: QuickStatsOut
    device_heartbeats: list[HeartbeatOut]


# ---------- Live feed ----------

class LiveStreamTokenOut(BaseModel):
    webrtc_url: str
    stream_token: str
    expires_in: int


# ---------- Events / Evidence log ----------

class EventOut(BaseModel):
    id: int
    camera_id: str
    category: str
    event_type: str
    description: Optional[str] = None
    confidence: Optional[int] = None
    occurred_at: datetime
    has_clip: bool

    class Config:
        from_attributes = True


# ---------- Analytics ----------

class HourlyFlowPoint(BaseModel):
    hour: int  # 0-23
    vehicle_count: int


class AnalyticsOut(BaseModel):
    date: str
    hourly_flow: list[HourlyFlowPoint]
    peak_hour: int
    total_incidents: int
