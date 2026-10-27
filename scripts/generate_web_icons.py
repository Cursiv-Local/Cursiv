"""Generate exact-size website favicons from the existing official Cursiv artwork.

No new artwork, launcher changes or external downloads. Requires the existing Pillow dependency.
"""
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'launcher/resources/icons/cursiv-logo-source.png'


def main():
    with Image.open(SOURCE) as original:
        assert original.width == original.height, 'Official source must be square'
        image = original.convert('RGBA')
        for size, name in ((96, 'favicon-96x96.png'), (180, 'apple-touch-icon.png')):
            image.resize((size, size), Image.Resampling.LANCZOS).save(ROOT / 'website' / name)
        sizes = (16, 32, 48, 64, 96, 128, 256)
        image.resize((256, 256), Image.Resampling.LANCZOS).save(
            ROOT / 'website/favicon.ico', format='ICO', sizes=[(size, size) for size in sizes])
    for name in ('favicon.ico', 'favicon-96x96.png', 'apple-touch-icon.png'):
        with Image.open(ROOT / 'website' / name) as icon:
            print(name, icon.format, icon.size, sorted(icon.info.get('sizes', [])))


if __name__ == '__main__':
    main()
