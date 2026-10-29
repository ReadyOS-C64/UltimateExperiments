"""Execute both production checkpoint capability scans in dense pair order."""
from pathlib import Path
import argparse
import binascii
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from peddle import Machine


def labels(path):
    return {
        name: int(address, 16)
        for address, name in re.findall(
            r"al ([0-9A-Fa-f]+) \.(\S+)", path.read_text())
    }


def payload(build, name):
    image = (build / "overlays" / f"{name}.seo").read_bytes()
    assert image[:4] == b"SEO2"
    return image, image[36:]


def write_catalog(machine, symbols, capacity, entries):
    fields = ("se_overlay_ids", "image_slot", "image_size_lo",
              "image_size_hi", "image_crc_lo", "image_crc_hi")
    for field in fields:
        for index in range(capacity):
            machine.write(symbols[field] + index, 0)
    for index, image in entries.items():
        raw = image[36:]
        size = len(raw)
        crc = binascii.crc_hqx(raw, 0xFFFF)
        values = (image[6], image[5], size & 0xFF, size >> 8,
                  crc & 0xFF, crc >> 8)
        for field, value in zip(fields, values):
            machine.write(symbols[field] + index, value)


def execute(build):
    report = json.loads((build / "editor-report.json").read_text())
    symbols = report["symbols"]
    capacity = symbols["se_overlay_capacity"]
    assert capacity == 51

    resident = (build / "editor.prg").read_bytes()
    load = int.from_bytes(resident[:2], "little")
    fold_image, _ = payload(build, "geosfold")
    semantic_image, semantic = payload(build, "geossema")
    assert fold_image[5:7] == bytes((0, 24))
    assert semantic_image[5:7] == bytes((1, 24))

    scans = (
        ("checkpoint/outgoing.s", "rangeio", build / "overlays/rangeio.lbl"),
        ("checkpoint/consumer.inc", "geospage", build / "overlays/geospage.lbl"),
    )
    results = []
    for source, image_name, label_path in scans:
        image, raw = payload(build, image_name)
        scan_labels = labels(label_path)
        entry = scan_labels["gsc_cap"]
        base = 0xA000 if image[5] == 0 else 0xB000
        machine = Machine()
        try:
            machine.load(load, resident[2:])
            machine.load(base, raw)

            # Current dense order: renderer (0,24) precedes command (1,24).
            write_catalog(machine, symbols, capacity,
                          {11: fold_image, 41: semantic_image})
            accepted, accepted_cost = machine.call(entry)
            assert not accepted.p & 1, (source, "wrong-slot stopped scan")

            # The slot-1 witness remains authenticated and fails closed.
            machine.write(symbols["image_size_lo"] + 41,
                          (len(semantic) + 1) & 0xFF)
            wrong_size, wrong_size_cost = machine.call(entry)
            assert wrong_size.p & 1, (source, "wrong size accepted")

            # A renderer ID-24 alone is not the command capability.
            write_catalog(machine, symbols, capacity, {11: fold_image})
            missing, missing_cost = machine.call(entry)
            assert missing.p & 1, (source, "wrong slot accepted")
            results.append(dict(
                source=source,
                overlay=image_name,
                entry=entry,
                dense_indices=[11, 41],
                accepted_instructions=accepted_cost,
                wrong_size_instructions=wrong_size_cost,
                missing_command_instructions=missing_cost,
            ))
        finally:
            machine.close()
    return dict(status="PASS", capacity=capacity, scans=results)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", type=Path, default=ROOT / "build")
    parser.add_argument("--out", type=Path)
    arguments = parser.parse_args()
    result = execute(arguments.build.resolve())
    if arguments.out:
        arguments.out.parent.mkdir(parents=True, exist_ok=True)
        arguments.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
