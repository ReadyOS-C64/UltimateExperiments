#!/usr/bin/env python3
"""Render scanline previews from frames captured during VICE CRT-mode runs."""

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parents[1]
ROM = ROOT / "assets/c77-photo-reconstruction-readyos-v3-chargen.bin"
LABELS = (
    "00_loader", "01_launcher", "02_editor", "03_readyshell",
    "04_simplefiles", "05_clipmgr", "06_readybasic", "07_cal26",
    "08_tasklist", "09_reuviewer", "10_sysinfo", "11_quicknotes",
    "12_calcplus", "13_hexview", "14_simplecells", "15_game2048",
    "16_deminer", "17_dizzy", "18_readyirc", "19_ucitest", "20_readme",
)
FEATURED = (
    "01_launcher", "03_readyshell", "04_simplefiles",
    "10_sysinfo", "18_readyirc", "20_readme",
)


def verify_bank1_font(input_dir: Path) -> str:
    """Require an exact bank-1 ROM match for APPLICATIONS in the launcher."""
    rom = ROM.read_bytes()
    if len(rom) != 4096:
        raise ValueError(f"Expected a 4096-byte character ROM, got {len(rom)}")
    image = Image.open(input_dir / "01_launcher.png").convert("RGB")
    foreground = (252, 238, 9)
    word = "APPLICATIONS"
    origin_x, origin_y = 20, 23
    matched = []
    for index, character in enumerate(word):
        code = ord(character) - 64
        expected = rom[2048 + code * 8 : 2048 + code * 8 + 8]
        x0 = origin_x + index * 8
        actual = []
        for y in range(8):
            row = 0
            for x in range(8):
                if image.getpixel((x0 + x, origin_y + y)) == foreground:
                    row |= 1 << (7 - x)
            actual.append(row)
        if bytes(actual) != expected:
            raise ValueError(
                f"Launcher glyph {index + 1} ({character}) does not match ROM bank 1"
            )
        matched.append(character)
    return (
        f"Verified {len(matched)}/{len(word)} launcher glyphs in APPLICATIONS "
        "against the ReadyOS ROM's second 2KB character bank."
    )


def crt_render(source: Image.Image) -> Image.Image:
    image = source.convert("RGB").resize((960, 600), Image.Resampling.NEAREST)
    image = image.filter(ImageFilter.Kernel((3, 3), (0, 0, 0, 0.15, 0.70, 0.15, 0, 0, 0)))
    image = ImageEnhance.Color(image).enhance(1.08)

    scanlines = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(scanlines)
    for y in range(2, image.height, 3):
        draw.line((0, y, image.width, y), fill=(0, 0, 10, 150))
    image = Image.alpha_composite(image.convert("RGBA"), scanlines).convert("RGB")

    # A restrained edge falloff approximates the darker visible area of a CRT
    # without distorting the 40x25 text grid.
    shade = Image.new("L", image.size, 255)
    shade_draw = ImageDraw.Draw(shade)
    for inset, alpha in ((0, 190), (6, 208), (12, 226), (18, 242)):
        shade_draw.rectangle(
            (inset, inset, image.width - 1 - inset, image.height - 1 - inset),
            outline=alpha,
            width=6,
        )
    black = Image.new("RGB", image.size, (0, 0, 5))
    return Image.composite(image, black, shade)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    input_dir = args.input if args.input.is_absolute() else ROOT / args.input
    output_dir = args.output if args.output.is_absolute() else ROOT / args.output
    sheets = output_dir / "contact-sheets"
    output_dir.mkdir(parents=True, exist_ok=True)
    sheets.mkdir(exist_ok=True)

    verification = verify_bank1_font(input_dir)

    font_path = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
    title_font = ImageFont.truetype(font_path, 18)
    rendered = []
    for label in LABELS:
        source = input_dir / f"{label}.png"
        if not source.exists():
            raise FileNotFoundError(source)
        image = crt_render(Image.open(source))
        image.save(output_dir / f"{label}.png")
        rendered.append((label, image))

    index = Image.new("RGB", (4 * 480, 6 * 330), (8, 9, 16))
    draw = ImageDraw.Draw(index)
    for i, (label, image) in enumerate(rendered):
        x = (i % 4) * 480
        y = (i // 4) * 330
        draw.text((x + 8, y + 5), label.replace("_", " ").upper(), font=title_font, fill=(252, 238, 9))
        index.paste(image.resize((480, 300), Image.Resampling.LANCZOS), (x, y + 30))
    index.save(output_dir / "00-complete-crt-gallery-index.png")

    # A single high-resolution comparison sheet.  Each frame is pasted at its
    # full 960x600 rendered size so the 3-line double-scan pattern is never
    # resampled or averaged away.
    combined = Image.new("RGB", (1920, 1980), (8, 9, 16))
    combined_draw = ImageDraw.Draw(combined)
    header_font = ImageFont.truetype(font_path, 28)
    combined_draw.text(
        (20, 18),
        "READYOS  •  C77 DUAL-BANK FONT  •  VICE CRT / DOUBLE-SCAN",
        font=header_font,
        fill=(252, 238, 9),
    )
    by_label = dict(rendered)
    for slot, label in enumerate(FEATURED):
        x = (slot % 2) * 960
        y = 72 + (slot // 2) * 636
        combined_draw.text(
            (x + 10, y + 5),
            label.replace("_", " ").upper(),
            font=title_font,
            fill=(112, 130, 255),
        )
        combined.paste(by_label[label], (x, y + 36))
    combined.save(output_dir / "00-combined-double-scan-font-proof.png")

    for page_no, start in enumerate(range(0, len(rendered), 4), start=1):
        page = Image.new("RGB", (1920, 1272), (8, 9, 16))
        draw = ImageDraw.Draw(page)
        for slot, (label, image) in enumerate(rendered[start : start + 4]):
            x = (slot % 2) * 960
            y = (slot // 2) * 636
            draw.text((x + 10, y + 5), label.replace("_", " ").upper(), font=title_font, fill=(252, 238, 9))
            page.paste(image, (x, y + 36))
        page.save(sheets / f"gallery-{page_no:02d}.png")

    (output_dir / "VICE-CRT-settings.txt").write_text(
        "VICE 3.10 CRT-mode run settings\n"
        "VICIIfilter=1 (CRT emulation)\n"
        "VICIIdscan=enabled\n"
        "VICIIcrtblur=350\n"
        "VICIIcrtscanlineshade=650\n"
        "VICIIoddlinesphase=1250\n"
        "VICIIoddlinesoffset=1000\n"
        "\nThe automation framebuffer API captures before VICE's display shader.\n"
        "The PNG previews reproduce the enabled blur and scanline presentation.\n",
        encoding="utf-8",
    )
    (output_dir / "FONT-VERIFICATION.txt").write_text(
        verification
        + "\nROM: "
        + str(ROM)
        + "\nVerified screen: 01_launcher.png\n",
        encoding="utf-8",
    )
    print(verification)
    print(f"Rendered {len(rendered)} CRT previews in {output_dir}")


if __name__ == "__main__":
    main()
