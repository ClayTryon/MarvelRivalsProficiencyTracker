"""
OCR utilities for reading hero proficiency data from a screenshot.

Two engines are used:
- pytesseract (--psm 6) for the XP fraction — fast, reliable on clean digits
- EasyOCR for the level number — handles the game's italic LV## font better
"""
import logging
import os
import re

import numpy as np
import pytesseract
from PIL import Image

from capture.debug import save_debug_image
from data.xp_table import level_range_for_xp, fit_level_to_range
from exceptions import ParseError

log = logging.getLogger(__name__)

_tess_cmd = os.environ.get("TESSERACT_CMD", r"C:\Program Files\Tesseract-OCR\tesseract.exe")
if os.path.exists(_tess_cmd):
    pytesseract.pytesseract.tesseract_cmd = _tess_cmd

# EasyOCR reader — initialized once on first use (model weights load ~5s)
_easy_reader = None


def _get_reader():
    global _easy_reader
    if _easy_reader is None:
        import easyocr
        _easy_reader = easyocr.Reader(['en'], gpu=False, verbose=False)
    return _easy_reader


def preprocess(image: Image.Image) -> Image.Image:
    """Convert to greyscale — improves pytesseract accuracy on both regions."""
    return image.convert("L")


def _ocr_digits_str(raw: str) -> str:
    """Substitute common OCR look-alikes with their digit equivalents."""
    return (raw.upper()
            .replace('I', '1').replace('L', '1')
            .replace('O', '0')
            .replace('A', '4')
            .replace('S', '5')
            .replace('B', '8')
            .replace('Z', '2')
            .replace('?', '2')
            .replace('G', '6')
            .replace('T', '7'))


# Fixed pixel regions within the proficiency screen (calibrated for 1936×1119 window)
LEVEL_REGION = (510, 870, 640, 900)  # italic LV## strip
XP_REGION    = (450, 910, 630, 970)  # XP fraction strip


def _easyocr_level(image: Image.Image) -> int:
    """Read the level number from LEVEL_REGION using EasyOCR.

    The crop is upscaled 2× before passing to the model — sharpens thin italic strokes.
    Raises ParseError if no digits can be extracted.
    """
    crop = image.crop(LEVEL_REGION)
    lc = crop.convert("L")
    lc = lc.resize((lc.width * 2, lc.height * 2), Image.LANCZOS)
    save_debug_image(lc, "level_ocr_input")

    results = _get_reader().readtext(np.array(lc), detail=0, allowlist='LV0123456789')
    raw = " ".join(results)

    # Apply substitution before matching so italic look-alikes are corrected first.
    # "LV" becomes "1V" after L→1; digits may be split across EasyOCR blocks.
    corrected = _ocr_digits_str(raw)
    m = re.search(r"1V\s*(\S+)", corrected)
    if m:
        digits = re.sub(r"\D", "", m.group(1))
    else:
        # Fallback: V was dropped (e.g. "L7" → "LV7") — grab trailing digits
        digits = re.sub(r"\D", "", corrected)
    if not digits:
        raise ParseError(f"Could not parse level from EasyOCR: {raw!r}")
    return int(digits)


def parse_proficiency_bar(image: Image.Image) -> tuple[str, int, int, int, bool]:
    """Extract (name, level, xp, xp_required, is_max) from a proficiency screen screenshot.

    name is always an empty string — the caller tracks hero identity via HERO_ROSTER index.
    is_max is True when the XP region contains 'MAX' or xp_required is 0.
    Level is cross-validated against the XP table and corrected if OCR produced a plausible
    look-alike (e.g. '17' when the real range is 15–19).
    """
    xp_text = pytesseract.image_to_string(preprocess(image.crop(XP_REGION)), config="--psm 6")

    if re.search(r"max", xp_text, re.IGNORECASE):
        level = _easyocr_level(image)
        return "", level, 0, 0, True

    xp_match = re.search(r"(\d[\d,]*)\s*/\s*(\d[\d,]*)", xp_text)
    if not xp_match:
        raise ParseError(f"Could not parse XP from region {XP_REGION}: {xp_text!r}")

    xp = int(xp_match.group(1).replace(",", ""))
    xp_required = int(xp_match.group(2).replace(",", ""))

    level_range = level_range_for_xp(xp_required)

    try:
        level = _easyocr_level(image)
    except ParseError:
        if level_range:
            level = level_range[0]
            log.warning("Level OCR failed — defaulting to %d based on xp_required=%d", level, xp_required)
        else:
            raise

    if level_range:
        corrected, was_corrected = fit_level_to_range(level, *level_range)
        if was_corrected:
            log.warning("Level corrected %d → %d (xp_required=%d, range=%s)",
                        level, corrected, xp_required, level_range)
            level = corrected

    return "", level, xp, xp_required, xp_required == 0
