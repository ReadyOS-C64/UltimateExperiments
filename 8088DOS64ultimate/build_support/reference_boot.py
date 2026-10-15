"""Boot a disposable supplied DOS image in DOSBox-X and capture guest-written evidence.

No host-mounted drive survives BOOT. VER/DIR/DONE are written by the real guest
COMMAND.COM to the cloned floppy and read with this small read-only FAT12 reader.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import time


def read_file(image, name):
    bps, spc, reserved, fats, entries, sectors, media, spf = struct.unpack_from("<HBHBHHBH", image, 11)
    if bps != 512 or not spc or len(image) != sectors * bps:
        raise ValueError("unsupported reference geometry")
    root = (reserved + fats * spf) * bps
    data = root + ((entries * 32 + bps - 1) // bps) * bps
    fat = image[reserved*bps:(reserved+spf)*bps]
    for position in range(root, root+entries*32, 32):
        entry = image[position:position+32]
        if entry[0] == 0:
            break
        if entry[0] == 0xe5 or entry[11] & 0x18:
            continue
        candidate = entry[:8].decode("ascii").rstrip()+"."+entry[8:11].decode("ascii").rstrip()
        if candidate != name:
            continue
        cluster = int.from_bytes(entry[26:28], "little")
        length = int.from_bytes(entry[28:32], "little")
        result = bytearray()
        seen = set()
        while len(result) < length:
            if cluster < 2 or cluster >= 0xff0 or cluster in seen:
                raise ValueError("invalid FAT12 chain")
            seen.add(cluster)
            start = data+(cluster-2)*spc*bps
            result.extend(image[start:start+spc*bps])
            value = int.from_bytes(fat[cluster*3//2:cluster*3//2+2], "little")
            cluster = (value >> 4) if cluster & 1 else (value & 0xfff)
        return bytes(result[:length])
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dosbox", default=os.environ.get("DOS64_DOSBOX", "dosbox-x"))
    parser.add_argument("--timeout", type=float, default=20)
    args = parser.parse_args()
    project = Path(__file__).resolve().parents[1]
    run = project/"agentworking/runs"/("reference-"+time.strftime("%Y%m%d-%H%M%S"))
    run.mkdir(parents=True, exist_ok=False)
    source = sorted((project/"reference").glob("*1 of 3.img"))[0]
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    disk = run/"dos33.img"
    shutil.copyfile(source, disk)
    (run/"AUTOEXEC.BAT").write_bytes(
        b"@ECHO OFF\r\nVER > A:\\VER.TXT\r\nDIR A: > A:\\DIR.TXT\r\nECHO DOS64_REFERENCE_OK > A:\\DONE.TXT\r\n")
    config = run/"dosbox-x.conf"
    config.write_text(f'''[sdl]
output=surface
fullscreen=false
autolock=false
[dosbox]
machine=cga
memsize=1
fastbioslogo=true
[cpu]
core=normal
cputype=8086
cycles=fixed 10000
[mixer]
nosound=true
[autoexec]
mount c "{run}"
imgmount a "{disk}" -t floppy
copy c:\\AUTOEXEC.BAT a:\\AUTOEXEC.BAT
boot a:
''')
    env = os.environ.copy()
    env.update(SDL_VIDEODRIVER="dummy", SDL_AUDIODRIVER="dummy")
    command = [shutil.which(args.dosbox) or args.dosbox, "-conf", str(config), "-noconsole"]
    completed = False
    with (run/"process.log").open("wb") as log:
        process = subprocess.Popen(command, cwd=run, env=env, stdout=log, stderr=log)
        deadline = time.monotonic()+args.timeout
        try:
            while time.monotonic() < deadline and process.poll() is None:
                time.sleep(0.2)
                if read_file(disk.read_bytes(), "DONE.TXT") == b"DOS64_REFERENCE_OK \r\n":
                    completed = True
                    break
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
    after = hashlib.sha256(source.read_bytes()).hexdigest()
    outputs = {}
    for name in ("VER.TXT", "DIR.TXT", "DONE.TXT"):
        data = read_file(disk.read_bytes(), name)
        outputs[name] = None if data is None else data.decode("cp437")
        if data is not None:
            (run/name).write_bytes(data)
    completed = outputs["DONE.TXT"] is not None and "DOS64_REFERENCE_OK" in outputs["DONE.TXT"]
    report = {"command": command, "configuration": str(config), "run": str(run),
              "source": str(source), "original_sha256": before, "source_unchanged": before == after,
              "transformation": "DOSBox-X integrated DOS copies supplied AUTOEXEC.BAT into cloned floppy before BOOT; original CONFIG.SYS retained",
              "guest_outputs": outputs, "completed": completed, "process_returncode": process.returncode,
              "limitations": "Functional DOS reference only; not XT timing or target emulator acceptance."}
    (run/"result.json").write_text(json.dumps(report, indent=2)+"\n")
    print(json.dumps(report, indent=2))
    if not (completed and before == after):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
