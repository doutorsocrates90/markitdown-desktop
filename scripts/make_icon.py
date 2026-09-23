# MarkItDown Desktop - GPL-3.0-or-later
"""Generate assets/icon.png and assets/AppIcon.icns (requires Pillow + macOS iconutil)."""

import os
import shutil
import subprocess
import tempfile

from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets")
S = 1024


def build() -> Image.Image:
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))

    # soft drop shadow
    shadow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle((100, 118, 924, 942), 190, fill=(0, 0, 0, 90))
    img.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(18)))

    # blue vertical gradient tile (macOS icon grid: 824px body inside 1024 canvas)
    grad = Image.new("RGBA", (S, S))
    top, bottom = (58, 146, 255), (8, 84, 196)
    for y in range(S):
        t = y / (S - 1)
        grad.paste(tuple(int(a + (b - a) * t) for a, b in zip(top, bottom)) + (255,), (0, y, S, y + 1))
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).rounded_rectangle((100, 100, 924, 924), 190, fill=255)
    img.paste(grad, (0, 0), mask)

    # white document sheet
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((250, 210, 774, 814), 48, fill=(255, 255, 255, 255))

    # "M" and a down arrow, the Markdown mark
    blue = (14, 96, 214, 255)
    w = 62
    d.line([(330, 660), (330, 380), (440, 520), (550, 380), (550, 660)], fill=blue, width=w, joint="curve")
    for x, y in [(330, 660), (330, 380), (550, 380), (550, 660)]:
        d.ellipse((x - w / 2, y - w / 2, x + w / 2, y + w / 2), fill=blue)
    d.line([(668, 390), (668, 640)], fill=blue, width=w)
    d.polygon([(590, 590), (746, 590), (668, 690)], fill=blue)
    d.ellipse((668 - w / 2, 390 - w / 2, 668 + w / 2, 390 + w / 2), fill=blue)
    return img


def main() -> None:
    os.makedirs(ASSETS, exist_ok=True)
    icon = build()
    png = os.path.join(ASSETS, "icon.png")
    icon.save(png)

    tmp = tempfile.mkdtemp()
    iconset = os.path.join(tmp, "AppIcon.iconset")
    os.makedirs(iconset)
    for size in (16, 32, 128, 256, 512):
        icon.resize((size, size), Image.LANCZOS).save(os.path.join(iconset, f"icon_{size}x{size}.png"))
        icon.resize((size * 2, size * 2), Image.LANCZOS).save(os.path.join(iconset, f"icon_{size}x{size}@2x.png"))
    subprocess.run(["iconutil", "-c", "icns", iconset, "-o", os.path.join(ASSETS, "AppIcon.icns")], check=True)
    shutil.rmtree(tmp)
    print("wrote", png, "and AppIcon.icns")


if __name__ == "__main__":
    main()
