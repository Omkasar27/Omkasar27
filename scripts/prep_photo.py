"""
prep_photo.py — turn a normal photo into a clean, high-contrast grayscale
image that converts well to ASCII art.

Usage:
    python scripts/prep_photo.py source-photo.jpg
    python scripts/prep_photo.py source-photo.jpg --no-bg-removal

Steps:
    1. Remove the background (rembg) so only the subject remains.
    2. Boost local contrast with CLAHE so a flatly-lit face gets real
       highlights and shadows (a flat face -> a dark unreadable blob
       without this step).
    3. Composite onto pure white so the background maps to the blank
       end of the ASCII ramp (white -> space character).

Output: source-prepped.png (grayscale, next to the input file).
"""
import argparse
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image


def remove_background(img: Image.Image) -> Image.Image:
    """Cut the subject out on a transparent background using rembg.
    Falls back to the original image (with full alpha) if rembg / its
    model isn't available, e.g. no network access to fetch the model."""
    try:
        from rembg import remove
        return remove(img)
    except Exception as e:
        print(f"[prep_photo] background removal unavailable ({e}); "
              f"continuing without it", file=sys.stderr)
        return img.convert("RGBA")


def boost_contrast(gray: np.ndarray) -> np.ndarray:
    """CLAHE = Contrast Limited Adaptive Histogram Equalization.
    Works in local tiles so it brings out shadow/highlight detail
    without blowing out the whole image the way global equalization does."""
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    return clahe.apply(gray)


def composite_on_white(rgba: Image.Image) -> Image.Image:
    bg = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
    return Image.alpha_composite(bg, rgba).convert("RGB")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source", help="path to the source photo")
    ap.add_argument("--no-bg-removal", action="store_true",
                     help="skip background removal (useful if rembg's "
                          "model can't be downloaded, e.g. offline)")
    ap.add_argument("-o", "--output", default=None,
                     help="output path (default: <source>-prepped.png)")
    args = ap.parse_args()

    src_path = Path(args.source)
    out_path = Path(args.output) if args.output else src_path.with_name(
        src_path.stem + "-prepped.png"
    )

    img = Image.open(src_path).convert("RGBA")

    if not args.no_bg_removal:
        img = remove_background(img)

    flat = composite_on_white(img)

    gray = cv2.cvtColor(np.array(flat), cv2.COLOR_RGB2GRAY)
    gray = boost_contrast(gray)

    Image.fromarray(gray).save(out_path)
    print(f"[prep_photo] wrote {out_path}")


if __name__ == "__main__":
    main()
