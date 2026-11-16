"""Detached Ultimate probe runner with passive VIC capture."""
import argparse
import ftplib
import fcntl
import hashlib
import io
import json
import os
from pathlib import Path
import socket
import struct
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
import zlib

PALETTE = (
    (0, 0, 0), (255, 255, 255), (136, 57, 50), (103, 182, 189),
    (139, 63, 150), (85, 160, 73), (64, 49, 141), (191, 206, 114),
    (139, 84, 41), (87, 66, 0), (184, 105, 98), (80, 80, 80),
    (120, 120, 120), (148, 224, 137), (120, 105, 196), (159, 159, 159),
)
COLORS = {8: "loading", 3: "prompt-one", 4: "prompt-two", 5: "complete", 2: "error"}
CATEGORY = "U64 Specific Settings"
CARTRIDGE_CATEGORY = "C64 and Cartridge Settings"
MARKER = bytes(color * 0x11 for color in (6, 14, 3, 13, 7, 1, 1, 7, 13, 3, 14, 6)
               for _ in range(4))
PORT = 11031


def json_file(path, obj):
    path.write_text(json.dumps(obj, indent=2) + "\n")


def hash_bytes(data):
    return hashlib.sha256(data).hexdigest()


class Ultimate:
    def __init__(self, host):
        self.host = host
        self.base = f"http://{host}/v1"

    def request(self, endpoint, *, params=None, method="GET", timeout=12):
        path = self.base + endpoint
        if params:
            path += "?" + urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
        request = urllib.request.Request(path, method=method)
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read()
            if response.headers.get("Content-Type", "").startswith("application/json"):
                data = json.loads(body)
                if data.get("errors"):
                    raise RuntimeError(f"{endpoint}: {data['errors']}")
            return body

    def json(self, path, **kwargs):
        return json.loads(self.request(path, **kwargs))

    def category(self, name):
        return self.json("/configs/" + urllib.parse.quote(name))[name]

    def setting_info(self, category, field):
        endpoint = "/configs/" + "/".join(urllib.parse.quote(part) for part in (category, field))
        return self.json(endpoint)[category][field]

    def setting(self, category, field, value):
        endpoint = "/configs/" + "/".join(urllib.parse.quote(part) for part in (category, field))
        self.request(endpoint, method="PUT", params={"value": value})

    def local_ip(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as target:
            target.connect((self.host, 80))
            return target.getsockname()[0]

    def capture_memory(self, address, length):
        data = self.request("/machine:readmem", params={"address": f"{address:X}", "length": length})
        if len(data) != length:
            raise RuntimeError("short REST memory read")
        return data

    def install(self, bundle, manifest):
        root = manifest["remote_path"]
        with ftplib.FTP() as ftp:
            ftp.connect(self.host, 21, timeout=15)
            ftp.login("anonymous", "anonymous@")
            # MKD is exclusive. Never turn an existing directory into a run root.
            ftp.mkd(root)
            files = [("PROBE.PRG", "prg_sha256")]
            if "model_sha256" in manifest:
                files.insert(0, ("MODEL.BIN", "model_sha256"))
            for name, key in files:
                local = (bundle / name).read_bytes()
                if hash_bytes(local) != manifest[key]:
                    raise ValueError(f"bundle identity mismatch for {name}")
                target = root + "/" + name
                ftp.storbinary("STOR " + target, io.BytesIO(local))
                copy = io.BytesIO()
                ftp.retrbinary("RETR " + target, copy.write)
                if hash_bytes(copy.getvalue()) != manifest[key]:
                    raise ValueError(f"remote content identity mismatch for {name}")


class Frames:
    """Assemble complete frames from Ultimate's byte-packed UDP VIC stream."""

    def __init__(self, sock):
        self.sock = sock
        self.frames = {}
        self.epoch = None

    def receive(self, deadline):
        while time.monotonic() < deadline:
            self.sock.settimeout(min(1, max(0.01, deadline - time.monotonic())))
            try:
                packet = self.sock.recv(4096)
            except TimeoutError:
                continue
            if len(packet) < 12:
                continue
            _, frame, raster, width, lines, depth, encoding = struct.unpack_from("<HHHHBBH", packet)
            if encoding != 0 or depth != 4 or width not in (384, 400) or not 0 < lines <= 8:
                continue
            end = bool(raster & 32768)
            line = raster & 32767
            stride = width // 2
            pixels = packet[12:]
            if len(pixels) != stride * lines or line + lines > 400:
                continue
            if self.epoch is None:
                self.epoch = frame
            index = (frame - self.epoch) & 65535
            rows, height = self.frames.get(index, ({}, None))
            rows.update({line + pos: pixels[stride * pos:stride * (pos + 1)]
                         for pos in range(lines)})
            height = line + lines if end else height
            self.frames[index] = (rows, height)
            self.frames = {key: value for key, value in self.frames.items()
                           if ((index - key) & 65535) < 6 or ((key - index) & 65535) < 6}
            if height and all(row in rows for row in range(height)):
                return width, height, b"".join(rows[row] for row in range(height))
        raise TimeoutError("no complete Ultimate video frame before deadline")

    def flush(self):
        self.frames.clear()
        self.epoch = None
        self.sock.setblocking(False)
        try:
            while True:
                self.sock.recv(4096)
        except BlockingIOError:
            pass


def frame_color(frame):
    width, _, packed = frame
    # Probe colors fill the entire VIC border. Sample the top two scan rows.
    border = packed[:width]
    candidates = [byte & 15 for byte in border] + [byte >> 4 for byte in border]
    color = max(set(candidates), key=candidates.count)
    return color if candidates.count(color) >= len(candidates) * 0.8 else None


def probe_visible(frame, marker=MARKER):
    width, height, packed = frame
    stride = width // 2
    for row in range(min(height - 1, 100)):
        origin = row * stride
        at = packed.find(marker, origin, origin + stride)
        if at >= 0 and packed[at + stride:at + stride + len(marker)] == marker:
            return True
    return False


def save_png(frame, target):
    width, height, data = frame
    pixels = [bytes(PALETTE[pos & 15] + PALETTE[pos >> 4]) for pos in range(256)]
    rows = b"".join(b"\0" + b"".join(pixels[byte] for byte in data[y:y + width // 2])
                    for y in range(0, len(data), width // 2))

    def chunk(kind, payload):
        return struct.pack(">I", len(payload)) + kind + payload + struct.pack(
            ">I", zlib.crc32(kind + payload))

    with target.open("wb") as stream:
        stream.write(b"\x89PNG\r\n\x1a\n")
        stream.write(chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)))
        stream.write(chunk(b"IDAT", zlib.compress(rows, 8)))
        stream.write(chunk(b"IEND", b""))


def decode_boot(mail, manifest, ready_phase):
    if mail[:4] != b"T64P" or mail[4] != ready_phase:
        raise ValueError(f"program did not publish expected ready state: {mail.hex()}")
    pal, turbo, stage = mail[5:8]
    load_ticks, rate, turbo_ticks, crc = struct.unpack_from("<4I", mail, 8)
    if (pal not in (0, 1) or rate != (985248 if pal else 1022727)
            or turbo & 0x8f != 0x8f or not 4608 <= turbo_ticks <= 5887
            or (stage, mail[24:26]) not in ((4, b"00"), (5, b"\0\0"))
            or (stage == 5 and load_ticks != 0)
            or crc != int(manifest["model_crc32"], 16)):
        raise ValueError(f"probe timing or loader identity mismatch: {mail.hex()}")
    return {
        "clock": "CIA2 A/B cascaded PHI2",
        "pal": bool(pal), "ticks_per_second": rate, "turbo_register": turbo,
        "turbo_validation_ticks": turbo_ticks, "model_crc32": f"{crc:08x}",
        "model_source": "preloaded REU" if stage == 5 else "Ultimate DOS",
        "dos_load_ticks": load_ticks, "dos_load_seconds": load_ticks / rate,
    }


def decode_result(mail, records, manifest):
    result = decode_boot(mail, manifest, ready_phase=3)
    rate = result["ticks_per_second"]
    rows = []
    for prompt, expected, record in zip(manifest["questions"], manifest["expected_answers"], records):
        marker, length, first, total = struct.unpack_from("<BBII", record)
        answer = record[10:10 + length].decode("ascii")
        if marker != 0xa5 or length > 127 - len(prompt) or not 0 < first <= total or answer != expected:
            raise ValueError(f"unexpected native result for {prompt!r}: {answer!r}, ticks {first}/{total}")
        rows.append({
            "prompt": prompt, "answer": answer, "character_tokens": length,
            "first_ticks": first, "total_ticks": total,
            "first_seconds": first / rate, "total_seconds": total / rate,
            "answer_phase_tokens_per_second": length * rate / (total - first) if total > first else None,
        })
    if manifest.get("context_test"):
        first_prompt = rows[0]
        if (len(first_prompt["prompt"]) + 1 + first_prompt["character_tokens"] != 128
                or records[0][137] != 128):
            raise ValueError("native context run did not prove the full context and overflow rejection")
        first_prompt["context_positions"] = 128
        first_prompt["next_token_rejected"] = True
    return {**result, "runs": rows}


def decode_transport(data, manifest):
    which = int(manifest["transport_mode"] == "georam")
    frequency, turbo_ticks = struct.unpack_from("<II", data, 8)
    if (data[:4] != b"T64D" or data[4] != 3 or data[5] != which
            or data[6] != manifest["sweeps"] or len(manifest["methods"]) != data[7]
            or frequency not in (985248, 1022727)
            or not 4608 <= turbo_ticks <= 5887 or data[62] & 0x8f != 0x8f):
        raise ValueError(f"invalid native transport benchmark result: {data.hex()}")
    low_speed_ticks, high_speed_ticks = struct.unpack_from("<II", data, 50)
    if not 262144 <= low_speed_ticks < 458752 or not 4608 <= high_speed_ticks <= 5887:
        raise ValueError("transport speed validation was outside supported limits")
    rows = []
    copied = data[6] * manifest["sample_bytes"]
    for index, mhz in enumerate((1, 64)):
        for lane, method in enumerate(manifest["methods"]):
            offset = 16 + 4 * (index * data[7] + lane)
            ticks, = struct.unpack_from("<I", data, offset)
            if not ticks:
                raise ValueError(f"transport cycle count missing for {method}, {mhz} MHz")
            rows.append({"cpu_setting_mhz": mhz, "method": method, "bytes": copied,
                         "phi2_ticks": ticks, "seconds": ticks / frequency,
                         "mib_per_second": copied * frequency / ticks / (1 << 20),
                         "destination_checked_byte_for_byte": True})
    return {"clock": "CIA2 A/B cascaded PHI2", "ticks_per_second": frequency,
            "turbo_validation_ticks": turbo_ticks, "sample_sha256": manifest["sample_sha256"],
            "speed_validation_ticks": {"1_mhz": low_speed_ticks, "64_mhz": high_speed_ticks},
            "transport_mode": manifest["transport_mode"], "runs": rows}


def decode_reu_qualification(raw):
    if raw != b"T64R" + bytes((0, 0, 34, 0, 34, 2)):
        raise ValueError(f"16 MiB REU qualification did not pass: {raw.hex()}")
    return {
        "banks_verified": 32,
        "last_byte": "FFFFFF",
        "boundary": "F7FFFF/F80000",
        "original_ranges_restored_and_verified": 34,
        "original_bytes_restored_and_verified": 544,
        "rejected_spans": ["beyond configured capacity", "24-bit address overflow"],
    }


def diagnose(device, out):
    diagnostics = {}
    for title, argv in (("route", ["/sbin/route", "-n", "get", device.host]),
                        ("arp", ["/usr/sbin/arp", "-n", device.host])):
        process = subprocess.run(argv, text=True, capture_output=True, timeout=4)
        diagnostics[title] = {"stdout": process.stdout, "stderr": process.stderr,
                              "returncode": process.returncode}
    errors = []
    for endpoint in ("/info", "/version"):
        try:
            json_file(out / (endpoint[1:] + ".json"), device.json(endpoint, timeout=4))
        except OSError as exc:
            errors.append(f"{endpoint}: {exc}")
    diagnostics["endpoint_errors"] = errors
    json_file(out / "diagnostics.json", diagnostics)
    if errors:
        raise RuntimeError("; ".join(errors))


def observe(device, out, timeout, check_input=False):
    # Query only management state and VIC video. No C64 RAM or media reads.
    json_file(out / "info.json", device.json("/info"))
    json_file(out / "drives.json", device.json("/drives"))
    if check_input:
        try:
            receipt = device.json("/machine:input")
        except urllib.error.HTTPError as error:
            receipt = {"http_status": error.code, "detail": error.read().decode(errors="replace")}
        json_file(out / "input-capability.json", receipt)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind(("", PORT))
        device.request("/streams/video:start", method="PUT",
                       params={"ip": f"{device.local_ip()}:{PORT}"})
        try:
            frame = Frames(sock).receive(time.monotonic() + timeout)
            save_png(frame, out / "preflight.png")
        finally:
            device.request("/streams/video:stop", method="PUT")


def wait_for_probe(frames, out, started, timeout, marker=MARKER):
    """Gate RAM evidence on three uninterrupted, probe-owned terminal frames."""
    seen = {}
    mode = None
    terminal_frames = 0
    deadline = started + timeout
    while time.monotonic() < deadline:
        frame = frames.receive(min(deadline, time.monotonic() + 20))
        if not probe_visible(frame, marker):
            terminal_frames = 0
            continue
        phase = COLORS.get(frame_color(frame))
        if phase != mode:
            terminal_frames = 0
            mode = phase
        if phase in ("loading", "prompt-one", "prompt-two") and phase not in seen:
            seen[phase] = time.monotonic() - started
            save_png(frame, out / f"{phase}.png")
            json_file(out / "progress.json", seen)
        if phase in ("error", "complete"):
            terminal_frames += 1
            if terminal_frames < 3:
                continue
            save_png(frame, out / f"{phase}.png")
            break
    else:
        raise TimeoutError("probe produced no final VIC frame")
    if mode not in ("error", "complete"):
        raise TimeoutError("probe did not reach a confirmed terminal video state")
    return mode, seen


def bundle_marker(manifest):
    return bytes(color * 0x11 for color in manifest["video_colors"] for _ in range(4))


def watch_keyboard(device, out, bundle, timeout, keyboard_timeout):
    """Resume qualification on the specified CIA1 console without relaunching it."""
    from manual_keyboard import verify

    manifest = json.loads((bundle / "bundle.json").read_text())
    if not manifest.get("interactive") or manifest.get("automation_keyboard"):
        raise ValueError("watch-keyboard requires the CIA1-only interactive console")
    json_file(out / "info.json", device.json("/info"))
    json_file(out / "run-bundle.json", manifest)
    marker = bundle_marker(manifest)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1 << 20)
        sock.bind(("", PORT))
        frames = Frames(sock)
        device.request("/streams/video:start", method="PUT",
                       params={"ip": f"{device.local_ip()}:{PORT}"})
        try:
            mode, _ = wait_for_probe(frames, out, time.monotonic(), timeout, marker)
            if mode != "complete":
                raise RuntimeError("the specified console is not ready")
            mail = device.capture_memory(manifest["mailbox"], 32)
            (out / "mailbox.bin").write_bytes(mail)
            if int.from_bytes(mail[30:32], "little") != manifest["nonce"]:
                raise RuntimeError("running console does not match the supplied bundle")
            boot = decode_boot(mail, manifest, ready_phase=4)
            (out / "complete.png").rename(out / "ready.png")
            json_file(out / "boot-result.json", boot)
            keyboard = verify(device, frames, out, bundle, marker, keyboard_timeout,
                              color=frame_color, visible=probe_visible, png=save_png,
                              save_json=json_file)
            json_file(out / "result.json", {**boot, "physical_keyboard": keyboard})
        finally:
            device.request("/streams/video:stop", method="PUT")



def run(device, out, bundle, timeout, *, record_video=False, start_query=1,
        keyboard_timeout=None):
    manifest = json.loads((bundle / "bundle.json").read_text())
    if record_video and not manifest.get("automation_keyboard"):
        raise ValueError("video mode requires an automation console bundle")
    if keyboard_timeout is not None and (not manifest.get("interactive")
                                         or manifest.get("automation_keyboard")):
        raise ValueError("physical-keyboard mode requires the CIA1-only interactive console")
    json_file(out / "info.json", device.json("/info"))
    json_file(out / "drives.json", device.json("/drives"))
    config = device.category(CATEGORY)
    cartridge = device.category(CARTRIDGE_CATEGORY)
    json_file(out / "cartridge-settings.json", cartridge)
    if (cartridge.get("Command Interface") != "Enabled" or
            cartridge.get("RAM Expansion Unit") != "Enabled" or
            not cartridge.get("REU Size", "")):
        raise RuntimeError("enable Command Interface and REU before this probe")
    json_file(out / "before-settings.json", config)
    json_file(out / "run-bundle.json", manifest)
    device.install(bundle, manifest)
    must_restore = False
    reu_target = None
    switched_mode = False
    disabled_audio = False
    disabled_uci = False
    streaming = False
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1 << 20)
        sock.bind(("", PORT))
        frames = Frames(sock)
        try:
            device.request("/streams/video:start", method="PUT",
                           params={"ip": f"{device.local_ip()}:{PORT}"})
            streaming = True
            save_png(frames.receive(time.monotonic() + 15), out / "preflight.png")
            turbo_key = "Turbo Control"
            options = device.setting_info(CATEGORY, turbo_key)
            turbo_mode = next((mode for mode in options["values"]
                               if mode in ("C64U Turbo Registers", "U64 Turbo Registers")), None)
            if not turbo_mode:
                raise RuntimeError("firmware does not offer register-controlled turbo")
            if config[turbo_key] != turbo_mode:
                must_restore = True
                device.setting(CATEGORY, turbo_key, turbo_mode)
                if device.category(CATEGORY)[turbo_key] != turbo_mode:
                    raise RuntimeError("could not select register-controlled turbo")
            json_file(out / "active-settings.json", device.category(CATEGORY))
            if str(cartridge["REU Size"]).split() != ["16", "MB"]:
                device.setting(CARTRIDGE_CATEGORY, "REU Size", "16 MB")
                active_cartridge = device.category(CARTRIDGE_CATEGORY)
                json_file(out / "active-cartridge-settings.json", active_cartridge)
                if str(active_cartridge["REU Size"]).split() != ["16", "MB"]:
                    raise RuntimeError("could not set 16 MB REU")
            reu_target = "16 MB"
            if manifest.get("transport_mode") == "georam":
                key = "RAM Expansion Unit"
                mode = "GeoRAM Mode"
                if mode not in device.setting_info(CARTRIDGE_CATEGORY, key)["values"]:
                    raise RuntimeError("firmware does not offer GeoRAM Mode")
                # The audio sampler configuration names the range including
                # GeoRAM page/bank registers ($DFFE/$DFFF). Free the range
                # during the alternate-mapping leg and restore it afterward.
                audio = "Map Ultimate Audio $DF20-DFFF"
                if cartridge.get(audio) == "Enabled":
                    disabled_audio = True
                    device.setting(CARTRIDGE_CATEGORY, audio, "Disabled")
                uci = "Command Interface"
                if cartridge.get(uci) == "Enabled":
                    disabled_uci = True
                    device.setting(CARTRIDGE_CATEGORY, uci, "Disabled")
                switched_mode = True
                device.setting(CARTRIDGE_CATEGORY, key, mode)
                if device.category(CARTRIDGE_CATEGORY)[key] != mode:
                    raise RuntimeError("could not select GeoRAM Mode")
                json_file(out / "georam-settings.json", device.category(CARTRIDGE_CATEGORY))
                # Unlike a C64 reset, this endpoint explicitly initializes
                # the configured cartridge before restarting the CPU.
                device.request("/machine:reboot", method="PUT")
                json_file(out / "georam-post-reboot.json", device.category(CARTRIDGE_CATEGORY))
            frames.flush()
            started = time.monotonic()
            device.request("/runners:run_prg", method="PUT",
                           params={"file": manifest["remote_path"] + "/PROBE.PRG"}, timeout=40)
            marker = bundle_marker(manifest)
            mode, seen = wait_for_probe(frames, out, started, timeout, marker)
            # A terminal VIC marker is now stable. Loading and inference have ceased.
            transport = manifest.get("transport_mode")
            mail = device.capture_memory(manifest["mailbox"], 64 if transport else 32)
            (out / "mailbox.bin").write_bytes(mail)
            nonce_offset = 60 if transport else 30
            if int.from_bytes(mail[nonce_offset:nonce_offset + 2], "little") != manifest["nonce"]:
                raise RuntimeError(f"probe run nonce mismatch: {mail.hex()}")
            qualification = manifest.get("reu_qualification_mailbox")
            if qualification is not None:
                qualified = device.capture_memory(qualification, 10)
                (out / "reu-qualification.bin").write_bytes(qualified)
            if mode == "error":
                raise RuntimeError(f"probe failed with mailbox {mail.hex()}")
            if transport:
                result = decode_transport(mail, manifest)
            elif manifest.get("interactive"):
                result = {**decode_boot(mail, manifest, ready_phase=4), "interactive_ready": True}
                (out / "complete.png").rename(out / "ready.png")
                if record_video:
                    from video_capture import capture_questions
                    ready = frames.receive(time.monotonic() + 10)
                    capture_questions(device, frames, out, marker, ready, start_query=start_query,
                                      color=frame_color,
                                      visible=probe_visible, png=save_png, save_json=json_file)
                if keyboard_timeout is not None:
                    from manual_keyboard import verify
                    json_file(out / "boot-result.json", result)
                    result["physical_keyboard"] = verify(
                        device, frames, out, bundle, marker, keyboard_timeout,
                        color=frame_color, visible=probe_visible, png=save_png, save_json=json_file)
            else:
                records = [device.capture_memory(address, 138) for address in manifest["answer_records"]]
                for index, record in enumerate(records, start=1):
                    (out / f"answer-{index}.bin").write_bytes(record)
                result = decode_result(mail, records, manifest)
            if qualification is not None:
                result["reu_qualification"] = decode_reu_qualification(qualified)
            result["host_run_elapsed_seconds"] = time.monotonic() - started
            result["video_stage_seconds"] = seen
            json_file(out / "result.json", result)
        finally:
            failures = []
            if streaming:
                try:
                    device.request("/streams/video:stop", method="PUT")
                except Exception as exc:
                    failures.append(f"video stop: {exc}")
            try:
                if must_restore:
                    device.setting(CATEGORY, "Turbo Control", config["Turbo Control"])
                actual = device.category(CATEGORY)
                json_file(out / "after-settings.json", actual)
                if actual != config:
                    failures.append("U64 Specific Settings did not match pre-run values")
            except Exception as exc:
                failures.append(f"turbo restore: {exc}")
            if reu_target:
                try:
                    if switched_mode:
                        key = "RAM Expansion Unit"
                        device.setting(CARTRIDGE_CATEGORY, key, cartridge[key])
                    if disabled_audio:
                        audio = "Map Ultimate Audio $DF20-DFFF"
                        device.setting(CARTRIDGE_CATEGORY, audio, cartridge[audio])
                    if disabled_uci:
                        uci = "Command Interface"
                        device.setting(CARTRIDGE_CATEGORY, uci, cartridge[uci])
                    if switched_mode:
                        device.request("/machine:reboot", method="PUT")
                    current_cartridge = device.category(CARTRIDGE_CATEGORY)
                    json_file(out / "after-cartridge-settings.json", current_cartridge)
                    if current_cartridge != {**cartridge, "REU Size": reu_target}:
                        failures.append("C64 and Cartridge Settings changed except for the intended 16 MB REU")
                except Exception as exc:
                    failures.append(f"REU capacity check: {exc}")
            if failures:
                json_file(out / "cleanup-errors.json", failures)
                raise RuntimeError("; ".join(failures))


def set_reu_capacity(device, out):
    before = device.category(CARTRIDGE_CATEGORY)
    json_file(out / "before-cartridge-settings.json", before)
    if before["REU Size"] != "16 MB":
        device.setting(CARTRIDGE_CATEGORY, "REU Size", "16 MB")
    after = device.category(CARTRIDGE_CATEGORY)
    json_file(out / "after-cartridge-settings.json", after)
    if after != {**before, "REU Size": "16 MB"}:
        raise RuntimeError("could not selectively set the REU to 16 MB")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["diagnose", "observe", "settings", "set-reu", "run", "video",
                                         "keyboard", "watch-keyboard"])
    parser.add_argument("--host", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--bundle", type=Path)
    parser.add_argument("--timeout", type=float)
    parser.add_argument("--start-query", type=int, default=1,
                        help="one-based starting index for a resumed video capture")
    parser.add_argument("--keyboard-timeout", type=float, default=1200,
                        help="seconds to observe the physical keyboard after the ready screen")
    parser.add_argument("--check-input", action="store_true",
                        help="include the current REST keyboard capability in an observe receipt")
    parser.add_argument("--device-available", action="store_true",
                        help="owner checked live preflight and released device for this detached run")
    args = parser.parse_args()
    if os.environ.get("TINY64_DETACHED") != "1" or os.isatty(0):
        parser.error("use launch_detached.py for all Ultimate communications")
    args.out.mkdir(parents=True, exist_ok=False)
    if args.mode == "diagnose":
        diagnose(Ultimate(args.host), args.out)
    elif args.mode == "settings":
        device = Ultimate(args.host)
        for group, field in ((CATEGORY, "Turbo Control"), (CATEGORY, "CPU Speed"),
                             (CARTRIDGE_CATEGORY, "REU Size"),
                             (CARTRIDGE_CATEGORY, "Command Interface"),
                             (CARTRIDGE_CATEGORY, "RAM Expansion Unit")):
            end = "/configs/" + "/".join(urllib.parse.quote(part) for part in (group, field))
            json_file(args.out / (field.lower().replace(" ", "-") + ".json"), device.json(end))
    elif args.mode == "observe":
        observe(Ultimate(args.host), args.out, args.timeout or 12, args.check_input)
    else:
        if not args.device_available:
            parser.error("device writes require a completed ownership preflight")
        if args.mode in ("run", "video", "keyboard", "watch-keyboard") and not args.bundle:
            parser.error("run requires --bundle")
        with Path("/tmp/tiny64-ultimate-probe.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            if args.mode == "set-reu":
                set_reu_capacity(Ultimate(args.host), args.out)
            elif args.mode == "watch-keyboard":
                watch_keyboard(Ultimate(args.host), args.out, args.bundle,
                               args.timeout or 15, args.keyboard_timeout)
            else:
                run(Ultimate(args.host), args.out, args.bundle, args.timeout or 1200,
                    record_video=args.mode == "video", start_query=args.start_query,
                    keyboard_timeout=args.keyboard_timeout if args.mode == "keyboard" else None)
