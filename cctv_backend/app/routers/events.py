# import io
# from typing import Optional

# from fastapi import APIRouter, Depends, HTTPException, Query, status
# from fastapi.responses import StreamingResponse
# from sqlalchemy.orm import Session

# from app.database import get_db
# from app.dependencies import get_current_user
# from app.crypto_clips import decrypt_clip
# from app.models import User, Event, EventCategory
# from app.schemas import EventOut

# router = APIRouter(prefix="/events", tags=["events"])


# @router.get("", response_model=list[EventOut])
# def list_events(
#     category: Optional[EventCategory] = Query(
#         None, description="Filter: 'crime' or 'traffic'"
#     ),
#     limit: int = Query(50, le=200),
#     db: Session = Depends(get_db),
#     _user: User = Depends(get_current_user),
# ):
#     """
#     The Evidence Log page: browse AI-verified events, optionally
#     filtered to just Crimes or just Traffic violations.
#     """
#     q = db.query(Event)
#     if category is not None:
#         q = q.filter(Event.category == category)
#     events = q.order_by(Event.occurred_at.desc()).limit(limit).all()

#     return [
#         EventOut(
#             id=e.id,
#             camera_id=e.camera_id,
#             category=e.category.value,
#             event_type=e.event_type,
#             description=e.description,
#             confidence=e.confidence,
#             occurred_at=e.occurred_at,
#             has_clip=e.clip_encrypted is not None,
#         )
#         for e in events
#     ]


# @router.get("/{event_id}/clip")
# def play_decrypted_clip(
#     event_id: int,
#     db: Session = Depends(get_db),
#     _user: User = Depends(get_current_user),
# ):
#     """
#     'Play Decrypted Clip': fetch the encrypted BYTEA blob, decrypt it
#     in server memory (AES-256-GCM), and stream the plaintext MP4 bytes
#     straight back to the app. The decrypted video is never persisted
#     to disk on the server.
#     """
#     event = db.query(Event).filter(Event.id == event_id).first()
#     if event is None:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
#     if event.clip_encrypted is None or event.clip_iv is None:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No clip stored for this event")

#     try:
#         plaintext = decrypt_clip(event.clip_encrypted, event.clip_iv)
#     except Exception:
#         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Clip decryption failed")

#     return StreamingResponse(
#         io.BytesIO(plaintext),
#         media_type="video/mp4",
#         headers={"Content-Disposition": f'inline; filename="event_{event_id}.mp4"'},
#     )

from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.orm import Session

from app.config import settings
from app.crypto_clips import decrypt_clip
from app.database import get_db
from app.dependencies import get_current_user
from app.models import Event, EventCategory, User
from app.schemas import EventOut
from app.security import decode_token

router = APIRouter(prefix="/events", tags=["events"])

CLIP_TOKEN_SECONDS = 120


@router.get("", response_model=list[EventOut])
def list_events(
    category: Optional[EventCategory] = Query(None, description="Filter: 'crime' or 'traffic'"),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    q = db.query(Event)
    if category is not None:
        q = q.filter(Event.category == category)
    events = q.order_by(Event.occurred_at.desc()).limit(limit).all()

    return [
        EventOut(
            id=e.id,
            camera_id=e.camera_id,
            category=e.category.value,
            event_type=e.event_type,
            description=e.description,
            confidence=e.confidence,
            occurred_at=e.occurred_at,
            has_clip=e.clip_encrypted is not None,
        )
        for e in events
    ]


@router.get("/{event_id}/clip-token")
def get_clip_token(
    event_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    A video player can't attach an Authorization header, so the app asks for a
    short-lived token scoped to ONE event's clip and puts it in the URL.
    """
    if db.query(Event.id).filter(Event.id == event_id).first() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "sub": user.username,
            "type": "clip",
            "event_id": event_id,
            "iat": now,
            "exp": now + timedelta(seconds=CLIP_TOKEN_SECONDS),
        },
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    return {"url": f"/events/{event_id}/clip?t={token}", "expires_in": CLIP_TOKEN_SECONDS}


@router.get("/{event_id}/clip")
def play_decrypted_clip(
    event_id: int,
    request: Request,
    t: Optional[str] = Query(None, description="Short-lived clip token"),
    db: Session = Depends(get_db),
):
    """
    Decrypts the AES-256-GCM clip in server memory and serves it with HTTP Range
    support (video players need that). Accepts either a clip token (?t=) or a
    normal Bearer access token.
    """
    username = None
    if t:
        payload = decode_token(t)
        if payload and payload.get("type") == "clip" and payload.get("event_id") == event_id:
            username = payload.get("sub")
    else:
        auth = request.headers.get("authorization", "")
        if auth.lower().startswith("bearer "):
            payload = decode_token(auth[7:])
            if payload and payload.get("type") == "access":
                username = payload.get("sub")

    user = db.query(User).filter(User.username == username).first() if username else None
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    event = db.query(Event).filter(Event.id == event_id).first()
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    if event.clip_encrypted is None or event.clip_iv is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No clip stored for this event")

    try:
        plaintext = decrypt_clip(event.clip_encrypted, event.clip_iv)
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Clip decryption failed")

    total = len(plaintext)
    headers = {
        "Accept-Ranges": "bytes",
        "Cache-Control": "no-store",
        "Content-Disposition": f'inline; filename="event_{event_id}.mp4"',
    }

    range_header = request.headers.get("range")
    if range_header and range_header.startswith("bytes="):
        try:
            start_s, _, end_s = range_header[6:].partition("-")
            if start_s == "":
                start = max(total - int(end_s), 0)
                end = total - 1
            else:
                start = int(start_s)
                end = int(end_s) if end_s else total - 1
            end = min(end, total - 1)
            if start > end:
                raise ValueError
        except ValueError:
            return Response(status_code=416, headers={"Content-Range": f"bytes */{total}"})
        return Response(
            content=plaintext[start : end + 1],
            status_code=206,
            media_type="video/mp4",
            headers={**headers, "Content-Range": f"bytes {start}-{end}/{total}"},
        )

    return Response(content=plaintext, media_type="video/mp4", headers=headers)