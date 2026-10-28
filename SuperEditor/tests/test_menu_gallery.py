"""Actual-CPU menu gallery for 40, 80, and editable GEOS modes."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "tools"), str(ROOT / "tests")]

import test_geos_editor as geos
from redraw_model import native_text


DOCUMENT = native_text(
    "# SuperEditor menu study\r"
    "Mixed Case PETSCII, **bold**, *italic*, and @@fixed@@.\r"
    "\r## Notes and ideas\r"
    "- First bullet\r- Second bullet\r1. Numbered item\r"
    "\r:::basic\r10 PRINT \"HELLO, C64!\"\r20 FOR I=1 TO 5:PRINT I:NEXT\r:::\r"
    "\r:::asm\rstart: lda #$00\r       sta $d020 ; border\r       rts\r:::\r"
    "\r:::region Details\rExpandable source region.\r:::end\r"
)

MENUS = (
    ("file", "f", 1, 0, 21, 3),
    ("edit", "e", 2, 6, 24, 4),
    ("view", "v", 3, 12, 27, 9),
    ("navigate", "n", 4, 11, 29, 15),
    ("block", "b", 5, 14, 26, 7),
    ("help", "h", 6, 14, 26, 2),
)
ROUNDED_LEFT = bytes.fromhex("18 18 1c 0f 07 00 00 00")
ROUNDED_RIGHT = bytes.fromhex("18 18 38 f0 e0 00 00 00")


def native_bitmap(matrix, colors, font):
    bits = bytearray(8000)
    for cell, value in enumerate(matrix):
        glyph = font[(value & 127) * 8 : (value & 127) * 8 + 8]
        at = (cell // 40) * 320 + (cell % 40) * 8
        bits[at : at + 8] = bytes(v ^ (255 if value & 128 else 0) for v in glyph)
    attrs = bytes(((value & 15) << 4) | 6 for value in colors)
    return bytes(bits), attrs


def cell_bytes(bits, row, col):
    at = row * 320 + col * 8
    return bits[at : at + 8]


def run():
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    out = ROOT / "agentsworking" / "evidence" / "M3" / (stamp + "-menu-gallery")
    out.mkdir(parents=True)
    frozen, identity = geos.freeze(out, None)
    geos.grid.editor_fixture.ROOT = geos.grid.cpu_editor.ROOT = frozen
    geos.grid.editor_fixture.NAMES = geos.grid.cpu_editor.NAMES = identity["names"]
    dll = geos.grid.runner(out)
    fixture = geos.Fixture(out, frozen, dll, True)
    font = (frozen / "fonts" / "native8.bin").read_bytes()
    assert font[0x6D * 8 : 0x6E * 8] == ROUNDED_LEFT
    assert font[0x7D * 8 : 0x7E * 8] == ROUNDED_RIGHT
    frames = []

    def capture(mode_name, item_name, popup=None):
        if fixture.get("se_mode", 1) == 0:
            matrix = fixture.read(0x4000, 1000)
            colors = fixture.read(0xD800, 1000)
            live_font = fixture.read(0x4800, 1024)
            assert live_font[0x6D * 8 : 0x6E * 8] == ROUNDED_LEFT
            assert live_font[0x7D * 8 : 0x7E * 8] == ROUNDED_RIGHT
            bits, attrs = native_bitmap(matrix, colors, live_font)
        else:
            bits = fixture.read(0x6000, 8000)
            attrs = fixture.read(0x4000, 1000)
        if not popup or popup[0] > 0:
            assert cell_bytes(bits, 1, 0) == ROUNDED_LEFT
        if not popup or popup[0] + popup[2] < 40:
            assert cell_bytes(bits, 1, 39) == ROUNDED_RIGHT
        if popup:
            x, y, width, height = popup
            assert tuple(fixture.get(name, 1) for name in
                         ("tui_box_x", "tui_box_y", "tui_box_w", "tui_box_h")) == popup
            assert cell_bytes(bits, y + height - 1, x) == ROUNDED_LEFT
            assert cell_bytes(bits, y + height - 1, x + width - 1) == ROUNDED_RIGHT
            assert attrs[(y + 1) * 40 + x + 2] >> 4 == 7
            assert attrs[(y + 1) * 40 + x + 3] >> 4 == 3
        path = out / f"{mode_name}-{item_name}.png"
        geos.png(bits, attrs, path)
        frames.append({
            "mode": mode_name,
            "view": item_name,
            "path": str(path),
            "popup": list(popup) if popup else None,
            "bitmap_sha256": hashlib.sha256(bits).hexdigest(),
            "attributes_sha256": hashlib.sha256(attrs).hexdigest(),
        })

    try:
        fixture.source(DOCUMENT)
        fixture.recolor()
        for mode_name, command, expected_mode in (("40", 96, 0), ("80", 98, 2), ("geos", 99, 3)):
            fixture.command(command)
            fixture.render()
            assert fixture.get("se_mode", 1) == expected_mode
            if fixture.get("se_st_request", 1) == 1:
                fixture.recolor()
                fixture.render()
            assert fixture.get("se_e_ui", 1) == 0
            capture(mode_name, "bare")
            for name, key, menu_id, x, width, count in MENUS:
                fixture.key(0x85)  # F1: expose the heading bar.
                fixture.key(native_text(key)[0])
                assert (fixture.get("se_e_ui", 1), fixture.get("se_e_menu", 1)) == (1, menu_id)
                fixture.render()
                capture(mode_name, name, (x, 1, width, count + 2))
                if name == "help":
                    fixture.key(native_text("h")[0])
                    assert fixture.get("se_e_menu", 1) == 9
                    fixture.render()
                fixture.key(3)
                fixture.render()
                assert fixture.get("se_e_ui", 1) == 0
        assert len(frames) == 21
        result = {
            "status": "passed",
            "evidence": str(out),
            "frames": frames,
            "rounded_bottom_corners": True,
            "content_sized_attached_pulldowns": True,
            "mnemonic_colors": True,
            "source_bytes": len(DOCUMENT),
            "prg_sha256": identity["prg_sha256"],
        }
        (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result, indent=2))
    finally:
        fixture.close()


if __name__ == "__main__":
    run()
