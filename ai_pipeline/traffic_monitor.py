"""
Tier 1 (Passive) - Ultralytics Sentinel — Traffic Rule Monitor.

Always-on lane, independent of the person-presence gate. Tracks
vehicles with YOLOv8's built-in tracker and checks each track's
trajectory against zones you define in a JSON file (drawn against a
snapshot of your actual camera view). No custom training needed —
COCO's pretrained vehicle classes are already accurate; the "rules"
are geometry, not a model.

zones.json format:
{
  "zones": [
    {
      "name": "main_junction",
      "polygon": [[120,300],[500,300],[500,600],[120,600]],
      "allowed_direction": [0, 1]   // unit-ish vector; downward in image coords
    }
  ]
}
"""
import json
import math
import time
from collections import defaultdict, deque

import numpy as np
from ultralytics import YOLO

import config


def _point_in_polygon(point, polygon) -> bool:
    import cv2
    return cv2.pointPolygonTest(np.array(polygon, dtype=np.int32), point, False) >= 0


def _load_zones():
    try:
        with open(config.ZONES_CONFIG_PATH) as f:
            return json.load(f)["zones"]
    except FileNotFoundError:
        return []  # runs fine with zero zones defined; just won't flag anything until you add some


class TrafficRuleMonitor:
    def __init__(self):
        self.yolo = YOLO(config.TRAFFIC_YOLO_MODEL)
        self.zones = _load_zones()
        # Per-track-ID position history: deque of (x, y, timestamp)
        self._track_history: dict[int, deque] = defaultdict(lambda: deque(maxlen=config.UTURN_WINDOW_FRAMES))
        self._flagged_uturn: set[int] = set()
        self._flagged_wrong_way: set[int] = set()

    def _zone_for_point(self, point):
        for zone in self.zones:
            if _point_in_polygon(point, zone["polygon"]):
                return zone
        return None

    def _check_uturn(self, track_id, history) -> bool:
        if len(history) < config.UTURN_WINDOW_FRAMES:
            return False
        (x0, y0, _), (x1, y1, _) = history[0], history[-1]
        mid = history[len(history) // 2]
        (xm, ym, _) = mid

        v1 = np.array([xm - x0, ym - y0])
        v2 = np.array([x1 - xm, y1 - ym])
        if np.linalg.norm(v1) < 5 or np.linalg.norm(v2) < 5:
            return False  # not moving enough to judge heading reliably

        cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
        angle_deg = math.degrees(math.acos(np.clip(cos_angle, -1, 1)))
        return angle_deg >= config.UTURN_ANGLE_DEG_THRESHOLD

    def _check_wrong_way(self, history, allowed_direction) -> bool:
        if len(history) < 2:
            return False
        (x0, y0, _), (x1, y1, _) = history[-2], history[-1]
        velocity = np.array([x1 - x0, y1 - y0])
        if np.linalg.norm(velocity) < 2:
            return False
        v_norm = velocity / np.linalg.norm(velocity)
        d_norm = np.array(allowed_direction) / (np.linalg.norm(allowed_direction) or 1)
        return np.dot(v_norm, d_norm) <= config.WRONG_WAY_DOT_THRESHOLD

    def _check_speeding(self, history) -> float | None:
        if config.METERS_PER_PIXEL is None or len(history) < 2:
            return None
        (x0, y0, t0), (x1, y1, t1) = history[-2], history[-1]
        dt = t1 - t0
        if dt <= 0:
            return None
        pixel_dist = math.hypot(x1 - x0, y1 - y0)
        meters = pixel_dist * config.METERS_PER_PIXEL
        kmh = (meters / dt) * 3.6
        return kmh if kmh > config.SPEED_LIMIT_KMH else None

    def analyze(self, frame: np.ndarray) -> list[dict]:
        events = []
        results = self.yolo.track(
            frame, classes=[2, 3, 5, 7],  # COCO: car, motorcycle, bus, truck
            persist=True, conf=config.TRAFFIC_CONFIDENCE_THRESHOLD, verbose=False,
        )
        r = results[0]
        if r.boxes.id is None:
            return events

        now = time.time()
        for box, track_id in zip(r.boxes.xyxy.cpu().numpy(), r.boxes.id.cpu().numpy().astype(int)):
            x1, y1, x2, y2 = box
            center = ((x1 + x2) / 2, (y1 + y2) / 2)
            self._track_history[track_id].append((center[0], center[1], now))
            history = self._track_history[track_id]

            zone = self._zone_for_point(center)

            if track_id not in self._flagged_uturn and self._check_uturn(track_id, history):
                self._flagged_uturn.add(track_id)
                events.append({
                    "event_type": "Illegal U-Turn",
                    "category": "traffic",
                    "confidence": 65,
                    "description": f"Vehicle #{track_id} reversed heading" + (f" in zone '{zone['name']}'" if zone else ""),
                })

            if zone and "allowed_direction" in zone and track_id not in self._flagged_wrong_way:
                if self._check_wrong_way(history, zone["allowed_direction"]):
                    self._flagged_wrong_way.add(track_id)
                    events.append({
                        "event_type": "Wrong Way Driving",
                        "category": "traffic",
                        "confidence": 70,
                        "description": f"Vehicle #{track_id} moving against traffic in zone '{zone['name']}'",
                    })

            speed = self._check_speeding(history)
            if speed is not None:
                events.append({
                    "event_type": "Speeding",
                    "category": "traffic",
                    "confidence": 60,
                    "description": f"Vehicle #{track_id} estimated at {speed:.0f} km/h",
                })

        return events
