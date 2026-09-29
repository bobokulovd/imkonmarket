"""AI bilan bitta rasmda yaratilgan N×M mahsulotlar to'rini (grid) alohida rasmlarga bo'lish.

    python data/split_grid.py grid.png 3 3 key1 key2 ... key9
    python data/split_grid.py ~/Downloads/grid.png 3 3 --first    # birinchi namunaviy to'r (9 ta kalit tayyor)

Kataklar orasidagi oq chiziqlar avtomatik kesib tashlanadi. Natija: backend/market/seed/images/<key>.webp
"""
import sys
from pathlib import Path

from PIL import Image, ImageChops

DIR = Path(__file__).resolve().parent.parent / "backend/market/seed/images"
FIRST = ["pustotali-plita-61879c", "quduq-halqasi-afa7ba", "kiyim-javoni-434fbf",
         "pishgan-gisht-poltara-f58ca4", "kema-suvenir-df4692", "jurnal-stoli-97818f",
         "shkatulka-b0f433", "sheben-5ef658", "parta-2-kishilik-5b549c"]


def trim_white(im, thr=245):
    bg = Image.new("RGB", im.size, (255, 255, 255))
    diff = ImageChops.difference(im, bg).convert("L").point(lambda v: 255 if v > 255 - thr else 0)
    box = diff.getbbox()
    return im.crop(box) if box else im


def main():
    path, rows, cols, *keys = sys.argv[1:]
    rows, cols = int(rows), int(cols)
    if keys == ["--first"]:
        keys = FIRST
    im = Image.open(Path(path).expanduser()).convert("RGB")
    w, h = im.size
    assert len(keys) == rows * cols, f"{rows * cols} ta kalit kerak"
    for i, key in enumerate(keys):
        r, c = divmod(i, cols)
        cell = im.crop((c * w // cols, r * h // rows, (c + 1) * w // cols, (r + 1) * h // rows))
        cell = trim_white(cell)
        s = min(cell.size)  # markazdan kvadrat
        cell = cell.crop(((cell.width - s) // 2, (cell.height - s) // 2, (cell.width + s) // 2, (cell.height + s) // 2))
        cell.thumbnail((1024, 1024))
        out = DIR / f"{key}.webp"
        cell.save(out, "WEBP", quality=84, method=6)
        print("✓", out.name, cell.size)


if __name__ == "__main__":
    main()
