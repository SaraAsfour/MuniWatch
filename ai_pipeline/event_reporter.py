import requests

import config


def report_event(event: dict, clip_bytes: bytes | None = None):
    """POSTs a confirmed event to the backend. Backend encrypts the clip on arrival."""
    data = {
        "camera_id": config.CAMERA_ID,
        "category": event["category"],
        "event_type": event["event_type"],
        "description": event.get("description", ""),
        "confidence": event.get("confidence", 0),
    }
    files = {"clip": ("clip.mp4", clip_bytes, "video/mp4")} if clip_bytes else None

    try:
        resp = requests.post(
            f"{config.BACKEND_URL}/internal/events",
            data=data, files=files,
            headers={"X-Internal-Api-Key": config.INTERNAL_API_KEY},
            timeout=10,
        )
        resp.raise_for_status()
        print(f"[reported] {event['event_type']} -> {resp.json()}")
    except requests.RequestException as e:
        print(f"[WARN] failed to report event to backend: {e}")


def report_heartbeat(device_id: str):
    try:
        requests.post(
            f"{config.BACKEND_URL}/internal/heartbeat",
            data={"device_id": device_id},
            headers={"X-Internal-Api-Key": config.INTERNAL_API_KEY},
            timeout=5,
        )
    except requests.RequestException as e:
        print(f"[WARN] failed to report heartbeat: {e}")
