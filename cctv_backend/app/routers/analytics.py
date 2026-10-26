from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User, Event, EventCategory
from app.schemas import AnalyticsOut, HourlyFlowPoint

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("", response_model=AnalyticsOut)
def get_analytics(
    date: str = Query(None, description="YYYY-MM-DD, defaults to today"),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """
    Data Intelligence page: aggregates event metadata (not the raw
    clips) into an hourly vehicle-flow chart, so patterns like peak
    traffic hours or high-risk windows become visible for resource
    planning.
    """
    day = datetime.strptime(date, "%Y-%m-%d") if date else datetime.utcnow().replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(days=1)

    rows = (
        db.query(
            func.extract("hour", Event.occurred_at).label("hour"),
            func.count(Event.id).label("count"),
        )
        .filter(
            Event.category == EventCategory.traffic,
            Event.occurred_at >= day_start,
            Event.occurred_at < day_end,
        )
        .group_by("hour")
        .all()
    )
    counts_by_hour = {int(r.hour): r.count for r in rows}
    hourly_flow = [
        HourlyFlowPoint(hour=h, vehicle_count=counts_by_hour.get(h, 0)) for h in range(24)
    ]
    peak_hour = max(hourly_flow, key=lambda p: p.vehicle_count).hour if hourly_flow else 0

    total_incidents = (
        db.query(func.count(Event.id))
        .filter(Event.occurred_at >= day_start, Event.occurred_at < day_end)
        .scalar()
    ) or 0

    return AnalyticsOut(
        date=day_start.strftime("%Y-%m-%d"),
        hourly_flow=hourly_flow,
        peak_hour=peak_hour,
        total_incidents=total_incidents,
    )
