from fastapi import Header, HTTPException, status

from app.config import settings


def require_internal_service(x_internal_api_key: str = Header(...)):
    """
    Authenticates the detection pipeline (a trusted backend service, not
    a phone-app user) so it can push confirmed events. Deliberately
    separate from the user JWT flow — the pipeline has no "login".
    """
    if x_internal_api_key != settings.INTERNAL_API_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid internal API key")
