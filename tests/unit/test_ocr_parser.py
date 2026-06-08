import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

import pytest
from PIL import Image
from unittest.mock import patch, MagicMock
from exceptions import ParseError


def _make_reader(xp_str: str, level_str: str):
    """Mock EasyOCR reader: first readtext call returns XP text, second returns level text."""
    reader = MagicMock()
    reader.readtext.side_effect = [[xp_str], [level_str]]
    return reader


def test_parse_proficiency_bar_normal():
    from capture.ocr import parse_proficiency_bar
    img = Image.new("RGB", (1920, 1080), (20, 20, 20))
    with patch("capture.ocr._get_reader", return_value=_make_reader("44 /400", "LV11")):
        name, level, xp, xp_req, is_max = parse_proficiency_bar(img, save_debug=False)
    assert level == 11
    assert xp == 44
    assert xp_req == 400
    assert is_max is False


def test_parse_proficiency_bar_large_xp():
    from capture.ocr import parse_proficiency_bar
    img = Image.new("RGB", (1920, 1080), (20, 20, 20))
    with patch("capture.ocr._get_reader", return_value=_make_reader("2452081 /3000000", "LV50")):
        name, level, xp, xp_req, is_max = parse_proficiency_bar(img, save_debug=False)
    assert xp == 2452081
    assert xp_req == 3000000
    assert is_max is False


def test_parse_proficiency_bar_max_level_zero_required():
    from capture.ocr import parse_proficiency_bar
    img = Image.new("RGB", (1920, 1080), (20, 20, 20))
    with patch("capture.ocr._get_reader", return_value=_make_reader("0 /0", "LV99")):
        name, level, xp, xp_req, is_max = parse_proficiency_bar(img, save_debug=False)
    assert is_max is True


def test_parse_proficiency_bar_raises_on_unreadable_xp():
    from capture.ocr import parse_proficiency_bar
    img = Image.new("RGB", (1920, 1080), (20, 20, 20))
    with patch("capture.ocr._get_reader", return_value=_make_reader("???", "LV11")):
        with pytest.raises(ParseError):
            parse_proficiency_bar(img, save_debug=False)


def test_parse_proficiency_bar_max_keyword():
    from capture.ocr import parse_proficiency_bar
    img = Image.new("RGB", (1920, 1080), (20, 20, 20))
    with patch("capture.ocr._get_reader", return_value=_make_reader("MAX", "LV99")):
        name, level, xp, xp_req, is_max = parse_proficiency_bar(img, save_debug=False)
    assert is_max is True
