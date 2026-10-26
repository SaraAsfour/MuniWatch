# """
# Matches the "10-Second Rolling RAM Buffer" block in the architecture
# diagram. Frames live in memory only (a deque), never written to disk
# until an event actually fires — keeping storage and I/O low.
# """
# import time
# from collections import deque

# import cv2
# import numpy as np

# import config


# class RollingClipBuffer:
#     def __init__(self):
#         maxlen = config.BUFFER_SECONDS * config.TARGET_FPS
#         self._frames: deque = deque(maxlen=maxlen)

#     def push(self, frame: np.ndarray):
#         self._frames.append((time.time(), frame))

#     def export_clip(self, extra_frames: list[np.ndarray] | None = None) -> bytes:
#         """
#         Encodes the current buffer (pre-trigger) plus any post-trigger
#         frames collected after the event fired, to MP4 bytes in memory.
#         """
#         import tempfile, os

#         frames = [f for _, f in self._frames]
#         if extra_frames:
#             frames.extend(extra_frames)
#         if not frames:
#             return b""

#         h, w = frames[0].shape[:2]
#         with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
#             path = tmp.name
#         writer = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"mp4v"), config.TARGET_FPS, (w, h))
#         for f in frames:
#             writer.write(f)
#         writer.release()

#         with open(path, "rb") as f:
#             data = f.read()
#         os.remove(path)
#         return data

"""
10-second rolling in-memory frame buffer for pre-trigger evidence clips.
Clips are re-encoded to H.264 (+faststart) so browsers and phones can play them.
"""
import os
import subprocess
import tempfile
import time
from collections import deque

import cv2
import numpy as np

import config


class RollingClipBuffer:
    def __init__(self):
        maxlen = config.BUFFER_SECONDS * config.TARGET_FPS
        self._frames: deque = deque(maxlen=maxlen)

    def push(self, frame: np.ndarray):
        self._frames.append((time.time(), frame))

    def export_clip(self, extra_frames: list[np.ndarray] | None = None) -> bytes:
        frames = [f for _, f in self._frames]
        if extra_frames:
            frames.extend(extra_frames)
        if not frames:
            return b""

        h, w = frames[0].shape[:2]
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
            raw_path = tmp.name
        h264_path = raw_path.replace(".mp4", "_h264.mp4")

        writer = cv2.VideoWriter(
            raw_path, cv2.VideoWriter_fourcc(*"mp4v"), config.TARGET_FPS, (w, h)
        )
        for f in frames:
            writer.write(f)
        writer.release()

        out_path = raw_path
        try:
            import imageio_ffmpeg

            subprocess.run(
                [
                    imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error",
                    "-i", raw_path,
                    "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
                    "-c:v", "libx264", "-preset", "veryfast",
                    "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                    h264_path,
                ],
                check=True,
                timeout=60,
            )
            out_path = h264_path
        except Exception as e:
            print(f"[WARN] H.264 transcode failed, sending raw mp4v clip: {e}")

        with open(out_path, "rb") as f:
            data = f.read()
        for p in (raw_path, h264_path):
            if os.path.exists(p):
                os.remove(p)
        return data
