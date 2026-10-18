"""Compose four authentic frames; labels stay outside the screen pixels."""
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
PANELS = (
    ('physical-20261017/dos-40.png', 'DOS prompt - 40 columns'),
    ('physical-20261017/dir-more-80.png', 'DIR | MORE - 80 columns'),
    ('physical-ripple-20261017/editor.png', 'Turbo Pascal - RIPPLE.PAS'),
    ('physical-ripple-20261017/picture.png', 'RIPPLE - finished'),
)


def compose():
    folder = ROOT / 'docs/screenshots'
    canvas = Image.new('RGB', (1584, 1200), '#10151e')
    font = (ROOT / 'assets/native-text/cp437-unscii8.bin').read_bytes()
    for index, (name, caption) in enumerate(PANELS):
        x = 16 + (index % 2) * 784
        y = 16 + (index // 2) * 592
        label = Image.new('RGB', (384, 16), '#10151e')
        for column, char in enumerate(caption):
            for row in range(8):
                bits = font[ord(char) * 8 + row]
                for pixel in range(8):
                    if bits & (128 >> pixel):
                        label.putpixel((column * 8 + pixel, 4 + row), (239, 239, 239))
        canvas.paste(label.resize((768, 32), Image.Resampling.NEAREST), (x, y))
        frame = Image.open(folder / name).convert('RGB')
        assert frame.size == (384, 272)
        canvas.paste(frame.resize((768, 544), Image.Resampling.NEAREST), (x, y + 32))
    canvas.save(folder / 'overview.png')


if __name__ == '__main__':
    compose()
