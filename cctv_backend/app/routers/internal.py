from datetime import datetime

from fastapi import APIRouter, Depends, Form, UploadFile, File
from sqlalchemy.orm import Session

from app.database import get_db
from app.internal_auth import require_internal_service
from app.crypto_clips import encrypt_clip
from app.models import Event, EventCategory, DeviceHeartbeat

router = APIRouter(prefix="/internal", tags=["internal"])


@router.post("/events", status_code=201)
async def ingest_event(
    camera_id: str = Form(...),
    category: EventCategory = Form(...),
    event_type: str = Form(...),
    description: str = Form(None),
    confidence: int = Form(None),
    clip: UploadFile = File(None),
    db: Session = Depends(get_db),
    _svc=Depends(require_internal_service),
):
    """
    Called by the Tier 1/Tier 2 detection pipeline (running on your
    laptop/server) whenever it confirms an event worth logging. If a
    clip is attached (the 10s rolling buffer, pre-trigger included),
    it's encrypted with AES-256-GCM here before touching the DB —
    the plaintext video never gets written to disk on this side either.
    """
    clip_encrypted, clip_iv = (None, None)
    if clip is not None:
        raw_bytes = await clip.read()
        clip_encrypted, clip_iv = encrypt_clip(raw_bytes)

    event = Event(
        camera_id=camera_id,
        category=category,
        event_type=event_type,
        description=description,
        confidence=confidence,
        clip_encrypted=clip_encrypted,
        clip_iv=clip_iv,
        occurred_at=datetime.utcnow(),
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return {"id": event.id, "stored": True}


@router.post("/heartbeat", status_code=200)
def ingest_heartbeat(
    device_id: str = Form(...),
    db: Session = Depends(get_db),
    _svc=Depends(require_internal_service),
):
    """Upserts the latest heartbeat for an edge device (Raspberry Pi), fed by the MQTT subscriber."""
    hb = db.query(DeviceHeartbeat).filter(DeviceHeartbeat.device_id == device_id).first()
    if hb is None:
        hb = DeviceHeartbeat(device_id=device_id)
        db.add(hb)
    hb.status = "online"
    hb.last_seen = datetime.utcnow()
    db.commit()
    return {"ok": True}
