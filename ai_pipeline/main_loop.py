# """
# Main entrypoint. Wires the pieces together exactly as in the
# architecture diagram:

#   frame -> RollingClipBuffer.push()
#         -> Tier 1 (MobileNet Sentinel): person present?
#              no  -> loop
#              yes -> Tier 2 (YOLOv8 + MediaPipe): behavior analysis
#         -> Traffic monitor (always-on, independent of Tier 1)
#         -> confirmed event -> export clip (pre + post trigger) -> report to backend

# Run with:  python main_loop.py
# """
# import time

# import cv2

# import config
# from tier1_passive import PersonPresenceDetector
# from tier2_active import ActiveAnalyzer
# from traffic_monitor import TrafficRuleMonitor
# from clip_buffer import RollingClipBuffer
# from event_reporter import report_event


# def main():
#     cap = cv2.VideoCapture(config.STREAM_URL)
#     if not cap.isOpened():
#         raise RuntimeError(f"Could not open stream: {config.STREAM_URL}")

#     passive_detector = PersonPresenceDetector()
#     active_analyzer = ActiveAnalyzer()
#     traffic_monitor = TrafficRuleMonitor()
#     clip_buffer = RollingClipBuffer()

#     tier2_active_until = 0.0
#     # Simple de-dup so the same confirmed event type isn't re-reported every frame
#     recent_event_types: dict[str, float] = {}
#     DEDUP_WINDOW_SECONDS = 30

#     print(f"Pipeline started on {config.STREAM_URL} (camera_id={config.CAMERA_ID})")

#     while True:
#         ok, frame = cap.read()
#         if not ok:
#             print("[WARN] stream read failed, retrying in 2s...")
#             time.sleep(2)
#             cap.open(config.STREAM_URL)
#             continue

#         clip_buffer.push(frame)
#         confirmed_events = []

#         # --- Tier 1 gate ---
#         person_present = passive_detector.check(frame)
#         if person_present:
#             tier2_active_until = time.time() + config.TIER2_COOLDOWN_SECONDS

#         # --- Tier 2, only while "awake" ---
#         if time.time() < tier2_active_until:
#             confirmed_events.extend(active_analyzer.analyze(frame))

#         # --- Traffic monitor, always on ---
#         confirmed_events.extend(traffic_monitor.analyze(frame))

#         # --- Report, with basic de-dup ---
#         now = time.time()
#         for event in confirmed_events:
#             last_seen = recent_event_types.get(event["event_type"], 0)
#             if now - last_seen < DEDUP_WINDOW_SECONDS:
#                 continue
#             recent_event_types[event["event_type"]] = now

#             print(f"[EVENT] {event['event_type']} — {event.get('description', '')}")
#             clip_bytes = clip_buffer.export_clip()
#             report_event(event, clip_bytes)


# if __name__ == "__main__":
#     main()

"""
Main entrypoint. Wires the pieces together exactly as in the
architecture diagram:

  frame -> RollingClipBuffer.push()
        -> Tier 1 (MobileNet Sentinel): person present?
             no  -> loop
             yes -> Tier 2 (YOLOv8 + MediaPipe): behavior analysis
        -> Traffic monitor (always-on, independent of Tier 1)
        -> confirmed event -> export clip (pre + post trigger) -> report to backend

Run with:  python main_loop.py

STREAM_URL can be:
  - an RTSP URL (real camera, via go2rtc)
  - a plain integer as a string, e.g. "0" (webcam index - for testing without hardware)
  - a local file path, e.g. "C:/videos/sample.mp4" (test video - loops automatically)
"""
import time

import cv2

import config
from tier1_passive import PersonPresenceDetector
from tier2_active import ActiveAnalyzer
from traffic_monitor import TrafficRuleMonitor
from clip_buffer import RollingClipBuffer
from event_reporter import report_event


def open_capture(source: str):
    """Webcam index if numeric, otherwise treat as RTSP URL or file path."""
    if source.isdigit():
        return cv2.VideoCapture(int(source))
    return cv2.VideoCapture(source)


def is_live_stream(source: str) -> bool:
    """True for RTSP/webcam (reconnect on failure); False for a file (loop on failure)."""
    return source.isdigit() or source.startswith("rtsp://")


def main():
    cap = open_capture(config.STREAM_URL)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open stream: {config.STREAM_URL}")

    passive_detector = PersonPresenceDetector()
    active_analyzer = ActiveAnalyzer()
    traffic_monitor = TrafficRuleMonitor()
    clip_buffer = RollingClipBuffer()

    tier2_active_until = 0.0
    recent_event_types: dict[str, float] = {}
    DEDUP_WINDOW_SECONDS = 30

    print(f"Pipeline started on {config.STREAM_URL} (camera_id={config.CAMERA_ID})")

    while True:
        ok, frame = cap.read()
        if not ok:
            if is_live_stream(config.STREAM_URL):
                print("[WARN] stream read failed, retrying in 2s...")
                time.sleep(2)
                cap.open(config.STREAM_URL if not config.STREAM_URL.isdigit() else int(config.STREAM_URL))
            else:
                # End of a test video file - loop back to the start instead of stopping
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            continue

        clip_buffer.push(frame)
        confirmed_events = []

        # --- Tier 1 gate ---
        person_present = passive_detector.check(frame)
        if person_present:
            tier2_active_until = time.time() + config.TIER2_COOLDOWN_SECONDS

        # --- Tier 2, only while "awake" ---
        if time.time() < tier2_active_until:
            confirmed_events.extend(active_analyzer.analyze(frame))

        # --- Traffic monitor, always on ---
        confirmed_events.extend(traffic_monitor.analyze(frame))

        # --- Report, with basic de-dup ---
        now = time.time()
        for event in confirmed_events:
            last_seen = recent_event_types.get(event["event_type"], 0)
            if now - last_seen < DEDUP_WINDOW_SECONDS:
                continue
            recent_event_types[event["event_type"]] = now

            print(f"[EVENT] {event['event_type']} — {event.get('description', '')}")
            clip_bytes = clip_buffer.export_clip()
            report_event(event, clip_bytes)


if __name__ == "__main__":
    main()