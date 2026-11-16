"""Offline checks for probe video identity and the early-error marker."""
from pathlib import Path
import struct
import tempfile
import time

from probe.physical import MARKER, probe_visible, wait_for_probe


class Replay:
    def __init__(self, frames):
        self.frames = iter(frames)
        self.count = 0

    def receive(self, _deadline):
        self.count += 1
        return next(self.frames)


def synthetic_frame(color, signed):
    width, height = 384, 272
    stride = width // 2
    raster = bytearray([color * 0x11] * (stride * height))
    if signed:
        for row in range(42, 50):
            offset = row * stride + 20
            raster[offset:offset + len(MARKER)] = MARKER
    return width, height, bytes(raster)


def main():
    early_error = synthetic_frame(2, True)
    unrelated = synthetic_frame(2, False)
    assert probe_visible(early_error) and not probe_visible(unrelated)
    with tempfile.TemporaryDirectory() as temp:
        folder = Path(temp)
        replay = Replay([unrelated, early_error, early_error, unrelated] + [early_error] * 3)
        mode, stages = wait_for_probe(replay, folder, time.monotonic(), 2)
        assert (mode, stages, replay.count) == ("error", {}, 7)
        png = (folder / "error.png").read_bytes()
        assert png.startswith(b"\x89PNG\r\n\x1a\n")
        assert struct.unpack_from(">II", png, 16) == (384, 272)
    print("Passive capture rejects unowned red frames and saves early probe errors without a loading frame.")


if __name__ == "__main__":
    main()
