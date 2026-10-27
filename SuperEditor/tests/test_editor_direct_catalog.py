"""CPU regression for the resident editor's fixed pair-to-catalog mapping."""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json
import sys

import test_cache_observer as observer
from peddle import library


def pair_index(slot, identity):
    if slot == 1 and 4 <= identity <= 33:
        return identity + 17
    if slot == 0:
        if identity in (1, 2):
            return identity - 1
        if identity == 14:
            return 2
        if 16 <= identity <= 33:
            return identity - 13
    return None


def execute(fixture, out):
    library()
    gate = observer.Gate(out, fixture)
    f, symbols = gate.f, gate.f.s
    cases = []

    def record(name, **details):
        cases.append(dict(name=name, status="PASS", **details))

    def overlay_call(slot, identity):
        return f.fast_call(symbols["se_overlay_call"], a=identity, x=slot)[0]

    def expect_error(slot, identity, error):
        result = overlay_call(slot, identity)
        assert result.p & 1 and result.a == error, (
            slot, identity, hex(result.a), hex(result.p), hex(error))

    try:
        frozen = gate.frozen
        identity = gate.identity
        binding = bytes.fromhex(json.loads(
            (frozen / "build/editor-bindings.json").read_text())["digest"])
        pairs = {}
        for name in identity["names"]:
            image = (frozen / f"build/overlays/{name}.seo").read_bytes()
            slot, overlay_id = image[5], image[6]
            index = pair_index(slot, overlay_id)
            assert index is not None and index not in pairs, (
                name, slot, overlay_id, index, pairs.get(index))
            assert image[20:36] == binding, (name, "resident binding")
            pairs[index] = name, slot, overlay_id
        assert set(pairs) == set(range(51)), sorted(pairs)
        assert f.read(symbols["se_overlay_ids"], 51) == bytes(
            pairs[index][2] for index in range(51))
        for index, (name, slot, _) in pairs.items():
            assert f.m.read(symbols["image_slot"] + index) & 1 == slot, name
        record("exact-dense-pair-publication", pairs=51,
               binding=binding.hex())

        refused = ((1, 1), (1, 2), (1, 3), (0, 3),
                   (0, 4), (0, 15), (0, 34), (1, 34))
        for slot, overlay_id in refused:
            expect_error(slot, overlay_id, 0x17)
        record("out-of-set-and-wrong-slot", pairs=[list(x) for x in refused],
               error=0x17)

        slot, overlay_id = 1, 7
        index = pair_index(slot, overlay_id)
        catalog = symbols["se_overlay_ids"] + index
        f.m.write(symbols["se_overlay_active"] + slot, 0)
        f.m.write(catalog, 0)
        expect_error(slot, overlay_id, 0x17)
        f.m.write(catalog, 8)
        expect_error(slot, overlay_id, 0x17)
        f.m.write(catalog, 0)
        image = (frozen / "build/overlays/menu40.seo").read_bytes()
        f.m.load(symbols["se_overlay_header"], image[:36])
        f.m.load(0x5000, image[36:])
        result = f.call("se_overlay_import")
        assert not result.p & 1 and f.m.read(catalog) == overlay_id
        record("wrong-nonzero-clear-and-reimport", index=index, error=0x17)

        f.put("se_overlay_frame", 4, 1)
        f.m.write(symbols["se_overlay_active"] + slot, 0)
        result = overlay_call(slot, overlay_id)
        assert not (result.p & 1 and result.a in (0x11, 0x17, 0x18, 0x19))
        assert f.m.read(symbols["se_overlay_active"] + slot) == index + 1
        original_binding = f.m.read(0xB000)
        f.m.write(0xB000, original_binding ^ 1)
        expect_error(slot, overlay_id, 0x11)
        f.m.write(0xB000, original_binding)
        f.put("se_overlay_frame", 4, 1)
        result = overlay_call(slot, overlay_id)
        assert not (result.p & 1 and result.a == 0x11)
        record("active-binding-validation", address=0xB000, error=0x11)

        handle = f.m.read(symbols["se_overlay_asset"] + (index >> 4))
        owner = symbols["se_reu_logical_owner"] + handle
        old_owner = f.m.read(owner)
        f.m.write(owner, old_owner ^ 1)
        expect_error(slot, overlay_id, 0x18)
        f.m.write(owner, old_owner)
        epoch = f.get("se_reu_epoch", 2)
        f.put("se_reu_epoch", epoch + 1, 2)
        expect_error(slot, overlay_id, 0x18)
        f.put("se_reu_epoch", epoch, 2)
        record("owner-and-epoch", handle=handle, error=0x18)

        payload_offset = ((index & 15) << 12) + 16
        original_payload = image[36 + 16]

        def reu_write(value):
            f.m.write(0x5400, value)
            f.put("se_reu_c64", 0x5400, 2)
            f.put("se_reu_offset", payload_offset, 2)
            f.put("se_reu_length", 1, 2)
            f.put("se_reu_logical", handle, 1)
            copied = f.fast_call(symbols["se_reu_copy"], a=0)[0]
            assert not copied.p & 1, (hex(copied.a), hex(copied.p))

        f.fast_call(symbols["se_overlay_unverify"])
        reu_write(original_payload ^ 1)
        f.m.write(symbols["se_overlay_active"] + slot, 0)
        expect_error(slot, overlay_id, 0x14)
        reu_write(original_payload)
        f.m.write(symbols["se_overlay_active"] + slot, 0)
        f.put("se_overlay_frame", 4, 1)
        result = overlay_call(slot, overlay_id)
        assert not (result.p & 1 and result.a in (0x11, 0x14, 0x17, 0x18, 0x19))
        record("unverified-crc-and-recovery", offset=payload_offset, error=0x14)

        assert f.read(0xC600, 1024) == f.shim
        record("readyos-shim", sha256=hashlib.sha256(f.shim).hexdigest())
        report = dict(status="PASS", fixture_prg_sha256=identity["prg_sha256"],
                      cases=cases)
        (out / "result.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report, indent=2))
        return report
    finally:
        f.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--out", type=Path)
    arguments = parser.parse_args()
    out = arguments.out or Path(__file__).resolve().parents[1] / "build/direct-catalog" / (
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    out.mkdir(parents=True, exist_ok=True)
    execute(arguments.fixture.resolve(), out.resolve())


if __name__ == "__main__":
    main()
