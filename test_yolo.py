"""Test the pre-trained YOLOv8 fight/violence detection weights.

Adapted from testing_code.ipynb (cell 5) for local paths.

Usage:
    python test_yolo.py video <input.mp4> [--weights nano|small]
    python test_yolo.py webcam [camera_index] [--weights nano|small]
    python test_yolo.py eval [--weights nano|small] [--n 10] [--stride 5]
"""
import argparse
import random
from pathlib import Path

import cv2
from ultralytics import YOLO

ROOT = Path(__file__).parent
WEIGHTS_DIR = ROOT / "fight-violence-detection-YOLOv8-main" / "Fight-Violence-detection-yolov8-main"
WEIGHTS = {
    "nano": WEIGHTS_DIR / "Yolo_nano_weights.pt",
    "small": WEIGHTS_DIR / "yolo_small_weights.pt",
}
RWF_VAL = Path(r"C:\Users\Lenovo\Desktop\Fyp1\data\kagglehub\datasets\vulamnguyen\rwf2000\versions\1\RWF-2000\val")
OUTPUT_DIR = ROOT / "outputs"
VIOLENCE_CLASS = 1


def detect_class_in_video(model, video_path, output_path, conf=0.25):
    """Draw boxes for class 1 (violence) on every frame and save the video."""
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise FileNotFoundError(f"Could not open video: {video_path}")

    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(cap.get(cv2.CAP_PROP_FPS)) or 25

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(str(output_path), fourcc, fps, (frame_width, frame_height))

    frames = violent_frames = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frames += 1

        results = model(frame, conf=conf, verbose=False)
        found = False
        for detection in results[0].boxes:
            class_id = int(detection.cls)
            confidence = float(detection.conf)
            if class_id == VIOLENCE_CLASS:
                found = True
                x1, y1, x2, y2 = map(int, detection.xyxy[0])
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
                cv2.putText(frame, f"Violence {confidence:.2f}", (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
        violent_frames += found
        out.write(frame)

    cap.release()
    out.release()
    print(f"Processed video saved at {output_path}")
    print(f"Frames with violence detected: {violent_frames}/{frames}")


def run_webcam(model, camera=0, conf=0.25):
    """Live violence detection on the webcam. Press 'q' to quit."""
    cap = cv2.VideoCapture(camera, cv2.CAP_DSHOW)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open webcam {camera}")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        results = model(frame, conf=conf, verbose=False)
        found = False
        for detection in results[0].boxes:
            if int(detection.cls) == VIOLENCE_CLASS:
                found = True
                x1, y1, x2, y2 = map(int, detection.xyxy[0])
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
                cv2.putText(frame, f"Violence {float(detection.conf):.2f}", (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

        status, color = ("VIOLENCE", (0, 0, 255)) if found else ("No violence", (0, 200, 0))
        cv2.putText(frame, status, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
        cv2.putText(frame, "Press q to quit", (10, frame.shape[0] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.imshow("YOLOv8 Violence Detection", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()


def violence_ratio(model, video_path, stride, conf):
    """Fraction of sampled frames that contain at least one violence box."""
    cap = cv2.VideoCapture(str(video_path))
    sampled = hits = idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if idx % stride == 0:
            sampled += 1
            boxes = model(frame, conf=conf, verbose=False)[0].boxes
            hits += any(int(b.cls) == VIOLENCE_CLASS for b in boxes)
        idx += 1
    cap.release()
    return hits / sampled if sampled else 0.0


def evaluate(model, n, stride, conf, threshold, seed=0):
    """Video-level accuracy on a random sample of RWF-2000 val clips."""
    random.seed(seed)
    tp = fn = tn = fp = 0
    for label in ("Fight", "NonFight"):
        videos = sorted((RWF_VAL / label).glob("*.avi"))
        for v in random.sample(videos, min(n, len(videos))):
            ratio = violence_ratio(model, v, stride, conf)
            pred_fight = ratio >= threshold
            if label == "Fight":
                tp += pred_fight
                fn += not pred_fight
            else:
                fp += pred_fight
                tn += not pred_fight
            print(f"{label:9s} {v.name:20s} violence-frames={ratio:5.0%} -> "
                  f"{'Fight' if pred_fight else 'NonFight'}")

    total = tp + tn + fp + fn
    print(f"\nAccuracy: {(tp + tn) / total:.0%} ({tp + tn}/{total})")
    print(f"Fight recall: {tp}/{tp + fn}   NonFight correct: {tn}/{tn + fp}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=["video", "webcam", "eval"])
    p.add_argument("source", nargs="?")
    p.add_argument("--weights", choices=WEIGHTS, default="nano")
    p.add_argument("--conf", type=float, default=0.25)
    p.add_argument("--n", type=int, default=10, help="clips per class for eval")
    p.add_argument("--stride", type=int, default=5, help="analyse every Nth frame in eval")
    p.add_argument("--threshold", type=float, default=0.3,
                   help="fraction of violent frames to call a clip a Fight")
    args = p.parse_args()

    model = YOLO(str(WEIGHTS[args.weights]))
    print(f"Loaded {args.weights} model, classes: {model.names}")

    if args.mode == "video":
        if not args.source:
            p.error("video mode needs a source path")
        OUTPUT_DIR.mkdir(exist_ok=True)
        out = OUTPUT_DIR / f"{Path(args.source).stem}_{args.weights}.mp4"
        detect_class_in_video(model, args.source, out, args.conf)
    elif args.mode == "webcam":
        run_webcam(model, int(args.source or 0), args.conf)
    else:
        evaluate(model, args.n, args.stride, args.conf, args.threshold)


if __name__ == "__main__":
    main()
