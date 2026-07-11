"""
Runs Tesseract OCR on a rendered page image. Used only when normal text
extraction returns almost nothing for a page - the signal that it's a
scanned image rather than real text.

Requires the Tesseract binary on the system (not just the Python package):
    Ubuntu/Debian: sudo apt-get install tesseract-ocr
    Mac:           brew install tesseract
    Windows:       https://github.com/UB-Mannheim/tesseract/wiki
"""

import pytesseract
from PIL import Image
import io

_tesseract_available = None


def ocr_ready():
    global _tesseract_available
    if _tesseract_available is not None:
        return _tesseract_available
    try:
        pytesseract.get_tesseract_version()
        _tesseract_available = True
    except Exception:
        _tesseract_available = False
        print(
            "[ocr_engine] Tesseract binary not found on this system. "
            "Scanned pages will be skipped. Install it with "
            "`sudo apt-get install tesseract-ocr` (Linux) or `brew install tesseract` (Mac)."
        )
    return _tesseract_available


def extract_text_from_image(image_bytes: bytes) -> str:
    """Returns OCR'd text from a page image, or '' if OCR isn't available."""
    if not ocr_ready():
        return ""
    try:
        image = Image.open(io.BytesIO(image_bytes))
        return pytesseract.image_to_string(image).strip()
    except Exception as e:
        print(f"[ocr_engine] OCR failed: {e}")
        return ""
