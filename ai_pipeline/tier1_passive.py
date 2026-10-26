"""
Tier 1 (Passive) — MobileNet Sentinel.

Runs on every frame. Its only question: "is a person in this frame?"
Cheap enough to leave running 24/7; wakes Tier 2 up only when needed.

Two interchangeable backends:
  - "yolov8n": easiest to set up (pip install ultralytics; weights
    auto-download on first use). Comparable speed to MobileNet-SSD.
  - "mobilenet_ssd": the classic OpenCV DNN MobileNet-SSD, if you'd
    rather use that specifically (needs prototxt + caffemodel files).
"""
import numpy as np

import config


class PersonPresenceDetector:
    def __init__(self, backend: str = config.PASSIVE_BACKEND):
        self.backend = backend
        self._consecutive_hits = 0

        if backend == "yolov8n":
            from ultralytics import YOLO
            self.model = YOLO("yolov8n.pt")
            self.person_class_id = 0  # COCO class 0 == 'person'

        elif backend == "mobilenet_ssd":
            import cv2
            self.net = cv2.dnn.readNetFromCaffe(config.MOBILENET_PROTOTXT, config.MOBILENET_WEIGHTS)
            # MobileNet-SSD (VOC-trained) class 15 == 'person'
            self.person_class_id = 15

        else:
            raise ValueError(f"Unknown PASSIVE_BACKEND: {backend}")

    def _person_present_single_frame(self, frame: np.ndarray) -> bool:
        if self.backend == "yolov8n":
            results = self.model.predict(
                frame, classes=[self.person_class_id],
                conf=config.PASSIVE_CONFIDENCE_THRESHOLD, verbose=False,
            )
            return len(results[0].boxes) > 0

        else:  # mobilenet_ssd
            import cv2
            blob = cv2.dnn.blobFromImage(frame, 0.007843, (300, 300), 127.5)
            self.net.setInput(blob)
            detections = self.net.forward()
            for i in range(detections.shape[2]):
                confidence = detections[0, 0, i, 2]
                class_id = int(detections[0, 0, i, 1])
                if confidence > config.PASSIVE_CONFIDENCE_THRESHOLD and class_id == self.person_class_id:
                    return True
            return False

    def check(self, frame: np.ndarray) -> bool:
        """
        Feed one frame at a time. Returns True only after
        PASSIVE_TRIGGER_FRAMES consecutive person-positive frames,
        so Tier 2 doesn't wake up on a single flicker/false positive.
        """
        if self._person_present_single_frame(frame):
            self._consecutive_hits += 1
        else:
            self._consecutive_hits = 0

        return self._consecutive_hits >= config.PASSIVE_TRIGGER_FRAMES
