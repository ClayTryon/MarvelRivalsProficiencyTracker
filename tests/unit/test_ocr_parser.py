import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

import pytest
from PIL import Image
from unittest.mock import patch, MagicMock
from exceptions import ParseError


def _mock_reader(level_str: str):
    """Return a mock EasyOCR reader whose readtext yields the given level string."""
    reader = MagicMock()
    reader.readtext.return_value = [level_str]
    return reader


def test_parse_proficiency_bar_normal():
    from capture.ocr import parse_proficiency_bar
    img = Image.new("RGB", (1920, 1080), (20, 20, 20))
    with patch("capture.ocr.pytesseract.image_to_string", return_value="44 /400\n"), \
         patch("capture.ocr._get_reader", return_value=_mock_reader("LV11")):
        name, level, xp, xp_req, is_max = parse_proficiency_bar(img)
    assert level == 11
    assert xp == 44
    assert xp_req == 400
    assert is_max is False


def test_parse_proficiency_bar_large_xp():
    from capture.ocr import parse_proficiency_bar
    img = Image.new("RGB", (1920, 1080), (20, 20, 20))
    with patch("capture.ocr.pytesseract.image_to_string", return_value="2452081 /3000000\n"), \
         patch("capture.ocr._get_reader", return_value=_mock_reader("LV50")):
        name, level, xp, xp_req, is_max = parse_proficiency_bar(img)
    assert xp == 2452081
    assert xp_req == 3000000
    assert is_max is False


def test_parse_proficiency_bar_max_level_zero_required():
    from capture.ocr import parse_proficiency_bar
    img = Image.new("RGB", (1920, 1080), (20, 20, 20))
    with patch("capture.ocr.pytesseract.image_to_string", return_value="0 /0\n"), \
         patch("capture.ocr._get_reader", return_value=_mock_reader("LV99")):
        name, level, xp, xp_req, is_max = parse_proficiency_bar(img)
    assert is_max is True


def test_parse_proficiency_bar_raises_on_unreadable_xp():
    from capture.ocr import parse_proficiency_bar
    img = Image.new("RGB", (1920, 1080), (20, 20, 20))
    with patch("capture.ocr.pytesseract.image_to_string", return_value="???"), \
         patch("capture.ocr._get_reader", return_value=_mock_reader("LV11")):
        with pytest.raises(ParseError):
            parse_proficiency_bar(img)


def test_parse_proficiency_bar_max_keyword():
    from capture.ocr import parse_proficiency_bar
    img = Image.new("RGB", (1920, 1080), (20, 20, 20))
    with patch("capture.ocr.pytesseract.image_to_string", return_value="MAX\n"), \
         patch("capture.ocr._get_reader", return_value=_mock_reader("LV99")):
        name, level, xp, xp_req, is_max = parse_proficiency_bar(img)
    assert is_max is True
