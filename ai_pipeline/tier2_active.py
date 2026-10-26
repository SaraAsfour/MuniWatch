"""
Tier 2 (Active) — Behavior & Pose Analysis.

Only runs while Tier 1 says a person is present. Combines:
  - YOLOv8: detects + tracks each person (persistent ID across frames)
  - MediaPipe Pose: per-person skeletal keypoints, used for posture heuristics

Behavior classification here is rule-based on top of pretrained models —
no custom training required. The heuristics (fall aspect-ratio, fight
proximity/velocity) are tunable in config.py; expect to adjust thresholds
once you test against your own camera's footage and mounting height/angle.
"""
from collections import defaultdict, deque

import numpy as np
import cv2
import mediapipe as mp
from ultralytics import YOLO

import config

mp_pose = mp.solutions.pose


class ActiveAnalyzer:
    def __init__(self):
        self.yolo = YOLO(config.ACTIVE_YOLO_MODEL)
        self.pose = mp_pose.Pose(
            static_image_mode=False,
            model_complexity=1,
            min_detection_confidence=0.3, #0.5
            min_tracking_confidence=0.3,  #0.5
        )
        # Per-track-ID rolling history for velocity/consistency checks
        self._keypoint_history: dict[int, deque] = defaultdict(lambda: deque(maxlen=6))
        self._fall_streak: dict[int, int] = defaultdict(int)
        self._fight_streak = 0

    def _extract_pose(self, crop: np.ndarray):
        if crop.size == 0:
            return None
        rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
        result = self.pose.process(rgb)
        if not result.pose_landmarks:
            return None
        h, w = crop.shape[:2]
        return np.array([[lm.x * w, lm.y * h] for lm in result.pose_landmarks.landmark])

    def _check_fall(self, track_id: int, box) -> bool:
        x1, y1, x2, y2 = box
        width, height = (x2 - x1), max(y2 - y1, 1)
        aspect_ratio = width / height

        if aspect_ratio >= config.FALL_ASPECT_RATIO_THRESHOLD:
            self._fall_streak[track_id] += 1
        else:
            self._fall_streak[track_id] = 0

        return self._fall_streak[track_id] >= config.FALL_CONFIRM_FRAMES

    def _check_fight(self, boxes_by_id: dict, keypoints_by_id: dict) -> bool:
        """Two people close together + both moving rapidly => possible fight."""
        ids = list(boxes_by_id.keys())
        rapid_movers = set()

        for track_id, keypoints in keypoints_by_id.items():
            history = self._keypoint_history[track_id]
            history.append(keypoints)
            if len(history) >= 2 and history[-2] is not None and keypoints is not None:
                displacement = np.linalg.norm(keypoints - history[-2], axis=1).mean()
                if displacement >= config.FIGHT_KEYPOINT_VELOCITY_THRESHOLD:
                    rapid_movers.add(track_id)

        found_pair = False
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                id_a, id_b = ids[i], ids[j]
                if id_a in rapid_movers and id_b in rapid_movers:
                    if self._boxes_close(boxes_by_id[id_a], boxes_by_id[id_b]):
                        found_pair = True

        self._fight_streak = self._fight_streak + 1 if found_pair else 0
        return self._fight_streak >= config.FIGHT_CONFIRM_FRAMES

    @staticmethod
    def _boxes_close(box_a, box_b) -> bool:
        ax1, ay1, ax2, ay2 = box_a
        bx1, by1, bx2, by2 = box_b
        gap_x = max(bx1 - ax2, ax1 - bx2, 0)
        gap_y = max(by1 - ay2, ay1 - by2, 0)
        return (gap_x ** 2 + gap_y ** 2) ** 0.5 <= config.FIGHT_PROXIMITY_PX

    def analyze(self, frame: np.ndarray) -> list[dict]:
        """
        Returns a list of confirmed behavior events for this frame, e.g.
        [{"event_type": "Person Fall Detected", "confidence": 82, ...}]
        Empty list if nothing confirmed yet.
        """
        events = []
        results = self.yolo.track(
            frame, classes=[0], persist=True,
            conf=config.ACTIVE_CONFIDENCE_THRESHOLD, verbose=False,
        )

        boxes_by_id, keypoints_by_id = {}, {}
        r = results[0]
        if r.boxes.id is not None:
            for box, track_id in zip(r.boxes.xyxy.cpu().numpy(), r.boxes.id.cpu().numpy().astype(int)):
                x1, y1, x2, y2 = box
                boxes_by_id[track_id] = (x1, y1, x2, y2)

                crop = frame[int(y1):int(y2), int(x1):int(x2)]
                keypoints_by_id[track_id] = self._extract_pose(crop)

                if self._check_fall(track_id, box):
                    events.append({
                        "event_type": "Person Fall Detected",
                        "category": "crime",  # or a dedicated "safety" category if you add one
                        "confidence": 75,
                        "description": f"Sustained horizontal posture for tracked person #{track_id}",
                    })
        print(f"[DEBUG Tier 2] Persons detected: {len(boxes_by_id)}")

        if self._check_fight(boxes_by_id, keypoints_by_id):
            events.append({
                "event_type": "Possible Altercation",
                "category": "crime",
                "confidence": 70,
                "description": "Two tracked individuals in close proximity with rapid movement",
            })

        return events
    
