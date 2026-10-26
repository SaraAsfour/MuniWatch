# AI Detection Pipeline (Tier 1 + Tier 2 + Traffic Monitor)

Runs on your laptop/server, pulling the stream from go2rtc and pushing
confirmed events to the FastAPI backend. All models are **pretrained** —
nothing here needs to be trained from scratch.

## Setup

```bash
cd ai_pipeline
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Must match the backend's INTERNAL_API_KEY
export INTERNAL_API_KEY=<same value as backend's setting>
export BACKEND_URL=http://localhost:8000
export STREAM_URL=rtsp://<go2rtc-host>:8554/hikvision-01

python main_loop.py
```

First run will auto-download `yolov8n.pt` and `yolov8s.pt` (~6MB and
~22MB) via `ultralytics`. MediaPipe's pose model downloads automatically
on first `import mediapipe`.

## What runs where

| Component | File | Always-on? | Model(s) |
|---|---|---|---|
| Tier 1 — Passive (MobileNet Sentinel) | `tier1_passive.py` | Yes | YOLOv8n (person-only) or classic MobileNet-SSD |
| Tier 2 — Active (Behavior & Pose) | `tier2_active.py` | Only while Tier 1 is triggered | YOLOv8s (tracking) + MediaPipe Pose |
| Traffic Sentinel | `traffic_monitor.py` | Yes, independent of Tier 1 | YOLOv8s (vehicle tracking) + zone rules |
| Rolling buffer | `clip_buffer.py` | Yes | — (just frame storage) |

## Accuracy tuning — read this before demoing

Nothing here needed custom training, but the **thresholds** in
`config.py` absolutely need tuning against your actual camera:

- **`PASSIVE_CONFIDENCE_THRESHOLD` / `ACTIVE_CONFIDENCE_THRESHOLD`** —
  raise if you're getting false positives, lower if people are being missed.
- **`FALL_ASPECT_RATIO_THRESHOLD`** — depends heavily on camera mounting
  angle. Log the actual aspect ratio for a person standing vs. lying
  down in your footage and set the threshold between them.
- **`FIGHT_PROXIMITY_PX` / `FIGHT_KEYPOINT_VELOCITY_THRESHOLD`** — scale
  with your camera's resolution and distance to subjects; there's no
  universal value. Print the computed displacement values during a test
  clip of normal walking vs. a staged "fight" and pick a threshold
  between the two.
- **`zones.json`** — draw your actual polygon coordinates against a
  frame grabbed from your camera (e.g. `cv2.imwrite` a frame, open it in
  an image editor, read off pixel coordinates for the junction boundary).
- **Speed estimation** requires `METERS_PER_PIXEL` calibration (measure
  a known real-world distance visible in frame, divide by its pixel
  length). Leave it `None` to skip speeding checks entirely — U-turn and
  wrong-way detection don't need this calibration.

## Improving accuracy further (optional, still no training required)

- Swap `yolov8s.pt` → `yolov8m.pt` or `yolov8l.pt` in `config.py` for
  higher accuracy if your hardware can keep up (has a real GPU).
- Add ByteTrack/BoT-SORT tuning via `model.track(..., tracker="botsort.yaml")`
  if IDs are switching between nearby people/vehicles.
- If pretrained accuracy genuinely isn't enough for a specific class
  (e.g. detecting a particular type of weapon), that's the one case
  where fine-tuning YOLOv8 on a small custom-labeled dataset
  (Roboflow + `yolo train`) would help — but it's not needed for the
  person/vehicle detection this project is built around.

## How an event becomes a stored clip

1. Every frame is pushed into `RollingClipBuffer` (10s ring, in memory only).
2. Tier 1 gates Tier 2; Tier 2 and the traffic monitor return confirmed
   events with a type/category/confidence.
3. On a confirmed (and de-duplicated) event, the buffer is exported to
   MP4 bytes and POSTed to `POST /internal/events` on the backend along
   with metadata.
4. The backend encrypts the clip (AES-256-GCM) and stores it as BYTEA —
   this pipeline never writes plaintext video to disk.

## Backend changes made to support this

- `app/internal_auth.py` — static API-key auth for the pipeline (separate
  from user JWT auth).
- `app/routers/internal.py` — `POST /internal/events`, `POST /internal/heartbeat`.
- `INTERNAL_API_KEY` added to `app/config.py` — set the same value as an
  env var on both sides.
