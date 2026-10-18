#!/usr/bin/env python3
"""Collect, recolor, enlarge, and index the C77 ReadyOS VICE captures."""

import argparse
import json
from pathlib import Path
import shutil

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
HARNESS_LOGS = ROOT.parent / "agenticdevharness" / "tools" / "vice_tasks_dotnet" / "logs"
OUT = ROOT / "screenshots" / "c77-cyberpunk-77"
VPL = ROOT / "C77CYBER.VPL"

STANDARD = (
    (0, 0, 0), (255, 255, 255), (136, 0, 0), (170, 255, 238),
    (204, 68, 204), (0, 204, 85), (0, 0, 170), (238, 238, 119),
    (221, 136, 85), (102, 68, 0), (255, 119, 119), (51, 51, 51),
    (119, 119, 119), (170, 255, 102), (0, 136, 255), (187, 187, 187),
)

LABELS = (
    "00_loader", "01_launcher", "02_editor", "03_readyshell",
    "04_simplefiles", "05_clipmgr", "06_readybasic", "07_cal26",
    "08_tasklist", "09_reuviewer", "10_sysinfo", "11_quicknotes",
    "12_calcplus", "13_hexview", "14_simplecells", "15_game2048",
    "16_deminer", "17_dizzy", "18_readyirc", "19_ucitest", "20_readme",
)


def custom_palette() -> tuple[tuple[int, int, int], ...]:
    values = []
    for line in VPL.read_text(encoding="ascii").splitlines():
        values.append(tuple(int(value, 16) for value in line.split()))
    if len(values) != 16:
        raise ValueError("C77CYBER.VPL must contain 16 RGB triplets")
    return tuple(values)


def latest_run(plan_id: str) -> Path:
    matches = []
    for manifest in HARNESS_LOGS.glob("vice_auto_*/manifest.json"):
        data = json.loads(manifest.read_text(encoding="utf-8-sig"))
        if data.get("plan_id") == plan_id:
            matches.append(manifest.parent)
    if not matches:
        raise FileNotFoundError(f"No VICE run found for {plan_id}")
    return sorted(matches)[-1]


def recolor(source: Path, palette: tuple[tuple[int, int, int], ...]) -> Image.Image:
    image = Image.open(source).convert("RGB")
    mapping = dict(zip(STANDARD, palette))
    pixels = image.load()
    for y in range(image.height):
        for x in range(image.width):
            pixels[x, y] = mapping.get(pixels[x, y], pixels[x, y])
    return image


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=OUT,
        help="Gallery output directory (default: screenshots/c77-cyberpunk-77)",
    )
    args = parser.parse_args()
    output_dir = args.output if args.output.is_absolute() else ROOT / args.output

    palette = custom_palette()
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "3x").mkdir(exist_ok=True)
    (output_dir / "contact-sheets").mkdir(exist_ok=True)

    sources: dict[str, Path] = {}
    gallery = latest_run("c77_cyberpunk_77_loader_launcher")
    sources["00_loader"] = gallery / "screens" / "00_loader.png"
    sources["01_launcher"] = gallery / "screens" / "01_launcher.png"
    for label in LABELS[2:]:
        app = label.split("_", 1)[1]
        run = latest_run(f"c77_cyberpunk_77_{app}")
        sources[label] = run / "screens" / f"{label}.png"

    font_path = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
    font = ImageFont.truetype(font_path, 20)
    small_font = ImageFont.truetype(font_path, 16)
    images: list[tuple[str, Image.Image]] = []
    inventory = ["C77 CYBERPUNK 77 READYOS VICE GALLERY", ""]
    for label in LABELS:
        source = sources[label]
        if not source.exists():
            raise FileNotFoundError(source)
        image = recolor(source, palette)
        output = output_dir / f"{label}.png"
        image.save(output)
        image.resize((960, 600), Image.Resampling.NEAREST).save(output_dir / "3x" / f"{label}.png")
        images.append((label, image))
        inventory.append(f"{label}.png <- {source}")

    # One compact index containing every screen.
    index = Image.new("RGB", (4 * 320, 6 * 228), (14, 15, 22))
    draw = ImageDraw.Draw(index)
    for i, (label, image) in enumerate(images):
        x = (i % 4) * 320
        y = (i // 4) * 228
        index.paste(image, (x, y + 28))
        draw.text((x + 8, y + 5), label.replace("_", " ").upper(), font=small_font, fill=(252, 238, 9))
    index.save(output_dir / "00-complete-gallery-index.png")

    # Detailed 2x2 pages, each screen enlarged 2x without smoothing.
    for page_no, start in enumerate(range(0, len(images), 4), start=1):
        page = Image.new("RGB", (1280, 856), (14, 15, 22))
        draw = ImageDraw.Draw(page)
        for slot, (label, image) in enumerate(images[start : start + 4]):
            x = (slot % 2) * 640
            y = (slot // 2) * 428
            draw.text((x + 12, y + 7), label.replace("_", " ").upper(), font=font, fill=(252, 238, 9))
            page.paste(image.resize((640, 400), Image.Resampling.NEAREST), (x, y + 28))
        page.save(output_dir / "contact-sheets" / f"gallery-{page_no:02d}.png")

    (output_dir / "inventory.txt").write_text("\n".join(inventory) + "\n", encoding="utf-8")
    print(f"Collected {len(images)} screens in {output_dir}")


if __name__ == "__main__":
    main()
