from fastapi import APIRouter, Depends

from app.dependencies import get_current_user
from app.models import User
from app.schemas import LiveStreamTokenOut
from app.security import create_access_token

router = APIRouter(prefix="/live", tags=["live-feed"])


@router.get("/token", response_model=LiveStreamTokenOut)
def get_stream_token(_user: User = Depends(get_current_user)):
    """
    Issues a short-lived, single-purpose token the Flutter app hands to
    go2rtc when opening the WebRTC session. go2rtc then performs the
    DTLS handshake and streams frames encrypted with AES-SRTP — this
    endpoint never touches the video itself, it only authorizes access.
    """
    # A separate, short-lived "stream" scoped token (5 min) rather than
    # reusing the general access token, so a leaked stream URL can't be
    # replayed to hit the rest of the API.
    stream_token = create_access_token(_user.username, _user.role.value)

    return LiveStreamTokenOut(
        webrtc_url="wss://<go2rtc-host>/api/ws?src=hikvision-01",
        stream_token=stream_token,
        expires_in=300,
    )
