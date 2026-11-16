"""Record a checked keyboard session against the physical interactive console."""
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import subprocess
import threading
import time
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit
import zlib

ROOT = Path(__file__).resolve().parent.parent
INPUT = ROOT / "build/video-input/VideoInput.dll"
QUERIES = ROOT / "tests/fixtures/video-queries.json"


def screen_codes(text):
    return bytes(ord(char) - 96 if "a" <= char <= "z" else ord(char) for char in text)


@contextmanager
def keyboard_transport(device):
    """Keep LAN traffic in the approved Terminal-owned Python process."""
    class Transport(BaseHTTPRequestHandler):
        def relay(self):
            request = urlsplit(self.path)
            params = {key: values[0] for key, values in parse_qs(request.query).items()}
            address = params.get("address", "").upper()
            read = (self.command == "GET" and request.path == "/v1/machine:readmem"
                    and address == "C6" and params.get("length") == "1")
            write = (self.command == "PUT" and request.path == "/v1/machine:writemem"
                     and address in {"00C5", "0277", "00C6"}
                     and re.fullmatch(r"[0-9A-F]{2}", params.get("data", "")))
            if not read and not write:
                self.send_error(403)
                return
            try:
                data = device.request(request.path[3:], params=params, method=self.command, timeout=3)
            except HTTPError as error:
                self.send_error(error.code)
                return
            except (OSError, RuntimeError) as error:
                self.send_error(502, str(error))
                return
            self.send_response(200)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        do_GET = do_PUT = relay

        def log_message(self, *args):
            pass

    with ThreadingHTTPServer(("127.0.0.1", 0), Transport) as server:
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            yield f"127.0.0.1:{server.server_port}"
        finally:
            server.shutdown()
            worker.join()


def capture_questions(device, frames, out, marker, ready, *, start_query, color, visible, png, save_json):
    """Record genuine VIC transitions and check RAM only after stable completion."""
    questions = json.loads(QUERIES.read_bytes())
    if not 1 <= start_query <= len(questions):
        raise ValueError("start query must be a one-based fixture index")
    records = []
    epoch = time.monotonic()
    last_frame = None
    with (keyboard_transport(device) as host, (out / "video-frames.bin").open("wb") as video,
          (out / "video-index.jsonl").open("w") as index):
        def write(frame, timestamp):
            nonlocal last_frame
            if frame == last_frame:
                return
            width, height, raw = frame
            payload = zlib.compress(raw, 1)
            index.write(json.dumps([timestamp, width, height, video.tell(), len(payload)]) + "\n")
            video.write(payload)
            last_frame = frame

        def receive(deadline):
            frame = frames.receive(min(deadline, time.monotonic() + 10))
            timestamp = time.monotonic() - epoch
            if not visible(frame, marker):
                raise RuntimeError("interactive console disappeared from the VIC stream")
            write(frame, timestamp)
            return frame, timestamp

        write(ready, 0)
        for number, item in enumerate(questions[start_query - 1:], start_query):
            question = item["question"]
            print(f"{number:02d} typing {question}", flush=True)
            typing_start = time.monotonic() - epoch
            with subprocess.Popen(["/usr/local/share/dotnet/dotnet", str(INPUT), host, question]) as keyboard:
                deadline = time.monotonic() + 180
                submitted = first = finished = None
                green = 0
                while time.monotonic() < deadline:
                    frame, timestamp = receive(deadline)
                    if keyboard.poll() not in (None, 0):
                        raise RuntimeError("strict keyboard automation failed")
                    phase = color(frame)
                    if phase == 3 and submitted is None:
                        submitted = timestamp
                    if submitted is None:
                        continue
                    if phase == 4 and first is None:
                        first = timestamp
                    if phase == 5:
                        if green == 0:
                            finished = timestamp
                        green += 1
                        if green >= 3 and keyboard.poll() == 0:
                            break
                    else:
                        green = 0
                else:
                    raise TimeoutError(f"no complete native answer for {question}")
            if first is None:
                raise RuntimeError("no native answer-generation frames")
            status = device.capture_memory(0x0400 + 40 * 10, 40)
            if status.strip(b" ") != screen_codes("Answer complete. Ready."):
                raise RuntimeError(f"unexpected native status {status.hex()}")
            answer = device.capture_memory(0x0400 + 40 * 12 + 1, 79)
            expected = screen_codes(item["answer"])
            if answer.rstrip(b" ") != expected:
                raise RuntimeError(f"unexpected native output for {question}: {answer.hex()}")
            timing = device.capture_memory(0x0400 + 40 * 17, 40)
            match = re.match(screen_codes("Elapsed ") + rb"(\d{3}\.\d{3})", timing.lstrip(b" "))
            if not match:
                raise RuntimeError(f"missing native timing {timing.hex()}")
            record = {**item, "typing_start": typing_start, "submitted": submitted,
                      "first_visible": first, "finished": finished,
                      "native_elapsed_seconds": float(match[1]),
                      "vic_wall_seconds": finished - submitted}
            png(frame, out / f"query-{number:02}.png")
            records.append(record)
            video.flush()
            index.flush()
            save_json(out / "video-results.json", records)
            print(f'{number:02d} verified {item["answer"]} in {match[1].decode()} s', flush=True)
