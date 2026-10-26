from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User, Event, DeviceHeartbeat, EventCategory
from app.schemas import DashboardOut, QuickStatsOut, HeartbeatOut

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardOut)
def get_dashboard(
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """
    Everything the Home page needs in a single call: live preview
    thumbnail, quick counters, and Pi heartbeat status — so the app
    doesn't have to fan out multiple requests just to render one screen.
    """
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    vehicles_today = (
        db.query(func.count(Event.id))
        .filter(Event.category == EventCategory.traffic, Event.occurred_at >= today_start)
        .scalar()
    ) or 0

    incidents_today = (
        db.query(func.count(Event.id))
        .filter(Event.occurred_at >= today_start)
        .scalar()
    ) or 0

    heartbeats = db.query(DeviceHeartbeat).all()

    # A device counts as "online" if it has phoned home in the last 90s
    stale_cutoff = datetime.utcnow() - timedelta(seconds=90)
    for hb in heartbeats:
        hb.status = "online" if hb.last_seen >= stale_cutoff else "offline"

    return DashboardOut(
        camera_thumbnail_url="/live/thumbnail.jpg",
        quick_stats=QuickStatsOut(
            vehicles_detected_today=vehicles_today,
            incidents_today=incidents_today,
        ),
        device_heartbeats=[HeartbeatOut.model_validate(hb) for hb in heartbeats],
    )
