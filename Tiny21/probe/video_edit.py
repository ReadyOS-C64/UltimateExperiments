"""Edit physical VIC footage, with adjustable typing speed and compressing inference to two seconds."""
import argparse
from bisect import bisect_right
from functools import lru_cache
import json
import math
from pathlib import Path
import subprocess
import zlib

from PIL import Image, ImageDraw, ImageFont

from physical import PALETTE

FPS = 30
WAIT_FRAMES = 2 * FPS
HOLD_FRAMES = 2 * FPS
FONT_PATH = "/System/Library/Fonts/Menlo.ttc"
INK = "#edffd9"
LIME = "#c8fb6c"


def add_clock(image, seconds, speed):
    draw = ImageDraw.Draw(image)
    x, y = image.width - 246, image.height - 54
    draw.rounded_rectangle((x, y, x + 228, y + 42), radius=10,
                           fill="#10180e", outline=LIME, width=1)
    cx, cy, radius = x + 24, y + 21, 14
    draw.ellipse((cx-radius, cy-radius, cx+radius, cy+radius), outline=LIME, width=1)
    for tick in range(12):
        angle = math.tau * tick / 12
        sin, cos = math.sin(angle), math.cos(angle)
        draw.line((cx + 11*sin, cy - 11*cos, cx + 13*sin, cy - 13*cos), fill=LIME)
    for length, turns in ((10, 2.15), (6, 0.48)):
        angle = math.tau * seconds * turns
        point = (cx + length * math.sin(angle), cy - length * math.cos(angle))
        draw.line((cx, cy, *point), fill=LIME, width=2)
    draw.ellipse((cx-1, cy-1, cx+1, cy+1), fill=INK)
    draw.text((x + 47, y + 11), f"TIME-LAPSE  ×{speed:.1f}", fill=INK, font=font(15))


@lru_cache
def font(size):
    return ImageFont.truetype(FONT_PATH, size)


def edit(evidence, music, output, *, typing_speed=1):
    if not math.isfinite(typing_speed) or typing_speed <= 0:
        raise ValueError("typing speed must be positive and finite")
    results = json.loads((evidence / "video-results.json").read_bytes())
    if not results:
        raise ValueError("no completed native prompts")
    entries = [json.loads(line) for line in
               (evidence / "video-index.jsonl").read_text().splitlines()]
    timestamps = [entry[0] for entry in entries]
    raw = (evidence / "video-frames.bin").read_bytes()
    rgb_codes = [PALETTE[byte & 15] + PALETTE[byte >> 4] for byte in range(256)]
    pixel_pairs = [bytes(pair) for pair in rgb_codes]
    _, width, height, _, _ = entries[0]
    size = (width * 2, height * 2)

    @lru_cache(maxsize=8)
    def frame_by_index(index):
        _, w, h, offset, length = entries[index]
        if (w, h) != (width, height):
            raise ValueError("VIC capture geometry changed")
        pixels = zlib.decompress(raw[offset:offset+length])
        pixels = b"".join(pixel_pairs[byte] for byte in pixels)
        return Image.frombytes("RGB", (w, h), pixels).resize(size, Image.Resampling.NEAREST)

    def frame_at(seconds):
        return frame_by_index(max(0, bisect_right(timestamps, seconds) - 1))

    def typing_frame_count(result):
        elapsed = result["submitted"] - result["typing_start"]
        return math.ceil(elapsed * FPS / typing_speed)

    def frames():
        yield from (frame_at(0) for _ in range(FPS))
        for result in results:
            start = result["typing_start"]
            submitted = result["submitted"]
            finished = result["finished"]
            for count in range(typing_frame_count(result)):
                yield frame_at(start + count * typing_speed / FPS)
            for count in range(WAIT_FRAMES):
                fraction = count / WAIT_FRAMES
                image = frame_at(submitted + fraction * (finished - submitted)).copy()
                add_clock(image, count / FPS, (finished - submitted) / 2)
                yield image
            complete = frame_at(finished)
            yield from (complete for _ in range(HOLD_FRAMES))

    output.parent.mkdir(parents=True, exist_ok=True)
    duration = (FPS + sum(typing_frame_count(result) + WAIT_FRAMES + HOLD_FRAMES
                          for result in results)) / FPS
    command = [
        "/opt/homebrew/bin/ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-f", "rawvideo", "-pixel_format", "rgb24", "-video_size", f"{size[0]}x{size[1]}",
        "-framerate", str(FPS), "-i", "pipe:0", "-i", str(music), "-map", "0:v", "-map", "1:a:0",
        "-af", f"volume=0.67,afade=t=in:d=0.6,afade=t=out:st={duration-2.0:.3f}:d=2",
        "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", "-shortest", str(output),
    ]
    with subprocess.Popen(command, stdin=subprocess.PIPE) as ffmpeg:
        for image in frames():
            ffmpeg.stdin.write(image.tobytes())
        ffmpeg.stdin.close()
        if ffmpeg.wait():
            raise subprocess.CalledProcessError(ffmpeg.returncode, command)
    frame_at(results[0]["finished"]).save(output.parent / "poster.png")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path)
    parser.add_argument("music", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--typing-speed", type=float, default=1,
                        help="typing playback speed multiplier, independent of the two-second waits")
    options = parser.parse_args()
    edit(options.evidence, options.music, options.output, typing_speed=options.typing_speed)
