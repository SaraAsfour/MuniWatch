"""
Configuration for the detection pipeline. Runs on your laptop/server
(not the Raspberry Pi) — the Pi only handles the camera/PTZ, this
process pulls the stream and does the heavy inference.
"""
import os

# --- Stream source ---
# Point this at go2rtc's restreamed RTSP/HTTP output (not the raw
# camera URL), so go2rtc's buffering/reconnect handling covers you too.
CAMERA_ID = os.getenv("CAMERA_ID", "hikvision-01")
STREAM_URL = os.getenv("STREAM_URL", "cctv video test.mp4") #"rtsp://localhost:8554/hikvision-01"

# --- Tier 1 passive gate ---
# "yolov8n" is the easiest to get running (auto-downloads via ultralytics,
# ~6MB, near-MobileNet-SSD speed). Set to "mobilenet_ssd" to use the
# classic Caffe MobileNet-SSD instead if you have the model files.
PASSIVE_BACKEND = os.getenv("PASSIVE_BACKEND", "yolov8n")
PASSIVE_CONFIDENCE_THRESHOLD = 0.5
# How many consecutive person-positive frames before waking Tier 2 —
# avoids triggering on a single noisy frame.
PASSIVE_TRIGGER_FRAMES = 3

# MobileNet-SSD file paths (only used if PASSIVE_BACKEND == "mobilenet_ssd")
# Download from: https://github.com/chuanqi305/MobileNet-SSD
MOBILENET_PROTOTXT = os.getenv("MOBILENET_PROTOTXT", "models/MobileNetSSD_deploy.prototxt")
MOBILENET_WEIGHTS = os.getenv("MOBILENET_WEIGHTS", "models/MobileNetSSD_deploy.caffemodel")

# --- Tier 2 active analysis ---
# Larger = more accurate, slower. yolov8s is a good accuracy/speed
# balance for a server with a decent CPU/GPU; use yolov8n if it's laggy.
# ACTIVE_YOLO_MODEL = os.getenv("ACTIVE_YOLO_MODEL", "yolov8s.pt")
# ACTIVE_CONFIDENCE_THRESHOLD = 0.5
# # Seconds of continued inactivity (no person) before Tier 2 goes back to sleep
# TIER2_COOLDOWN_SECONDS = 15

# # Behavior heuristics (tune these against your own footage)
# FALL_ASPECT_RATIO_THRESHOLD = 1.4      # bbox width/height ratio above which a person is "lying down"
# FALL_CONFIRM_FRAMES = 5                # consecutive frames before confirming a fall (vs. bending over)
# FIGHT_PROXIMITY_PX = 80                # bbox-edge distance below which two people are "close"
# FIGHT_KEYPOINT_VELOCITY_THRESHOLD = 35 # avg landmark pixel-displacement/frame indicating rapid motion
# FIGHT_CONFIRM_FRAMES = 8

# --- Tier 2 active analysis ---
ACTIVE_YOLO_MODEL = os.getenv("ACTIVE_YOLO_MODEL", "yolov8s.pt")
ACTIVE_CONFIDENCE_THRESHOLD = 0.3  # Lowered from 0.5 for distant CCTV tracking
TIER2_COOLDOWN_SECONDS = 15

# Behavior heuristics (tuned for CCTV fight detection)
FALL_ASPECT_RATIO_THRESHOLD = 1.4
FALL_CONFIRM_FRAMES = 5
FIGHT_PROXIMITY_PX = 180                 # Increased from 80 px (wider bounding box proximity)
FIGHT_KEYPOINT_VELOCITY_THRESHOLD = 2.5  # Lowered from 35 (matches actual frame-to-frame pixel shifts)
FIGHT_CONFIRM_FRAMES = 3                 # Lowered from 8 frames for faster trigger




# --- Traffic monitor (always-on, separate from the person-gated tiers) ---
TRAFFIC_YOLO_MODEL = os.getenv("TRAFFIC_YOLO_MODEL", "yolov8s.pt")
TRAFFIC_CONFIDENCE_THRESHOLD = 0.5
VEHICLE_CLASSES = {"car", "truck", "bus", "motorcycle"}
# Load named polygonal zones + allowed direction per zone from a JSON file
# you draw against a snapshot of your actual camera view.
ZONES_CONFIG_PATH = os.getenv("ZONES_CONFIG_PATH", "zones.json")
UTURN_ANGLE_DEG_THRESHOLD = 135   # heading change over the tracked window that counts as a U-turn
UTURN_WINDOW_FRAMES = 20
WRONG_WAY_DOT_THRESHOLD = -0.3    # velocity·allowed_direction below this = against traffic

# Optional speed estimation (needs calibration; leave None to skip speeding checks)
METERS_PER_PIXEL = None  # e.g. 0.05 if you've calibrated your camera's FOV
SPEED_LIMIT_KMH = 50

# --- Evidence clip buffer ---
BUFFER_SECONDS = 10       # matches the "10-Second Rolling RAM Buffer"
POST_EVENT_SECONDS = 3    # keep recording a few seconds after trigger before cutting the clip
TARGET_FPS = 15           # downsample stored clips to save memory/bandwidth

# --- Backend connection ---
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY", "CHANGE_ME_PIPELINE_KEY")  # must match backend's setting
