"""
OCR utilities for reading hero proficiency data from a screenshot.

EasyOCR handles both level and XP regions — the game uses a stylized italic font
that pytesseract misreads; EasyOCR also handles white-on-dark without inversion.
Crop regions are expressed as relative fractions so the same values work at any 16:9 resolution.
"""
import logging
import re

import numpy as np
from PIL import Image

from capture.debug import save_debug_image
from data.xp_table import level_range_for_xp, fit_level_to_range
from exceptions import ParseError

log = logging.getLogger(__name__)

# EasyOCR reader — initialized once on first use (model weights load ~5s)
_easy_reader = None


def _get_reader():
    global _easy_reader
    if _easy_reader is None:
        import easyocr
        _easy_reader = easyocr.Reader(['en'], gpu=False, verbose=False)
    return _easy_reader


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


# Relative crop fractions for client-area captures (derived from 1936x1119 full-window calibration,
# adjusted for 8px side borders + 38px title bar → scales to any 16:9 client area)
_LEVEL_FRACS = (0.265, 0.770, 0.312, 0.813)   # "LV##" badge row
_XP_FRACS    = (0.230, 0.807, 0.324, 0.863)   # "## /####" proficiency row


def _scale_region(fracs, w, h):
    x1, y1, x2, y2 = fracs
    return (int(x1 * w), int(y1 * h), int(x2 * w), int(y2 * h))


def _easyocr_level(image: Image.Image, save_debug: bool = True) -> int:
    """Read the level number using EasyOCR. Raises ParseError if no digits found."""
    region = _scale_region(_LEVEL_FRACS, image.width, image.height)
    crop = image.crop(region)
    lc = crop.convert("L")
    lc = lc.resize((lc.width * 2, lc.height * 2), Image.LANCZOS)
    if save_debug:
        save_debug_image(lc, "level_ocr_input")

    results = _get_reader().readtext(np.array(lc), detail=0, allowlist='LV0123456789')
    raw = " ".join(results)

    corrected = _ocr_digits_str(raw)
    m = re.search(r"1V\s*(\S+)", corrected)
    if m:
        digits = re.sub(r"\D", "", m.group(1))
    else:
        digits = re.sub(r"\D", "", corrected)
    if not digits:
        raise ParseError(f"Could not parse level from EasyOCR: {raw!r}")
    return int(digits)


def parse_proficiency_bar(image: Image.Image, save_debug: bool = True) -> tuple[str, int, int, int, bool]:
    """Extract (name, level, xp, xp_required, is_max) from a proficiency screen screenshot.

    name is always an empty string — caller tracks hero identity via HERO_ROSTER index.
    is_max is True when the XP region contains 'MAX' or xp_required is 0.
    Level is cross-validated against the XP table and corrected if OCR produced a plausible
    look-alike.
    """
    xp_region = _scale_region(_XP_FRACS, image.width, image.height)
    xp_crop = image.crop(xp_region).convert("L")
    xp_crop = xp_crop.resize((xp_crop.width * 2, xp_crop.height * 2), Image.LANCZOS)
    if save_debug:
        save_debug_image(xp_crop, "xp_ocr_input")

    xp_results = _get_reader().readtext(np.array(xp_crop), detail=0, allowlist='MAX0123456789 /')
    xp_text = " ".join(xp_results)

    if re.search(r"max", xp_text, re.IGNORECASE):
        level = _easyocr_level(image, save_debug=save_debug)
        return "", level, 0, 0, True

    xp_text_clean = _ocr_digits_str(xp_text)
    xp_match = re.search(r"(\d[\d,]*)\s*/\s*(\d[\d,]*)", xp_text_clean)
    if not xp_match:
        raise ParseError(f"Could not parse XP from region {xp_region}: {xp_text!r}")

    xp = int(xp_match.group(1).replace(",", ""))
    xp_required = int(xp_match.group(2).replace(",", ""))

    level_range = level_range_for_xp(xp_required)

    try:
        level = _easyocr_level(image, save_debug=save_debug)
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
