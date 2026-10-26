"""
Generate cursiv.ico, tray.ico and cursiv_256.png for the Cursiv launcher from the logo
(icons/cursiv-logo-source.png, the same image the website uses since U103).
Run: python launcher/resources/gen_icons.py
"""
from pathlib import Path
from PIL import Image, ImageDraw

OUT = Path(__file__).parent / "icons"
SOURCE = OUT / "cursiv-logo-source.png"

SIZES = [16, 32, 48, 64, 128, 256]


def _draw_cursiv(size: int) -> Image.Image:
    """The logo on its dark disc, with transparent corners (no black square on the desktop)."""
    big = size * 4                                   # mask drawn large, then scaled: smooth edge
    logo = Image.open(SOURCE).convert("RGBA").resize((big, big), Image.LANCZOS)
    mask = Image.new("L", (big, big), 0)
    pad = big * 0.02
    ImageDraw.Draw(mask).ellipse([pad, pad, big - pad, big - pad], fill=255)
    logo.putalpha(mask)
    return logo.resize((size, size), Image.LANCZOS)


def _save_ico(path: Path):
    """Pillow's ICO writer scales each listed size down from the largest frame."""
    _draw_cursiv(256).save(path, format="ICO", sizes=[(s, s) for s in SIZES])
    print(f"  {path.name}: {sorted(Image.open(path).info['sizes'])} — {path.stat().st_size:,} bytes")


def main():
    print("Generating Cursiv icons...")
    _save_ico(OUT / "cursiv.ico")
    _save_ico(OUT / "tray.ico")          # the same mark: the disc keeps it visible on light and dark taskbars
    _draw_cursiv(256).save(OUT / "cursiv_256.png")   # window icon, Inno Setup wizard, macOS .icns
    print("Done.")


if __name__ == "__main__":
    main()
