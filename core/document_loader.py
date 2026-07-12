"""
Turns a PDF into a flat list of "raw chunks" - one dict per unit of content,
each tagged with a type so the rest of the pipeline (and citations) knows what
it's looking at:

    {"content": str, "page": int, "type": "text" | "table" | "image"}

Four extraction paths run per page:
  1. Native text          -> pypdf                (fast path, most pages)
  2. Scanned/image pages  -> PyMuPDF render + OCR  (when native text is too thin)
  3. Tables               -> pdfplumber            (kept as markdown, not prose)
  4. Embedded figures     -> PyMuPDF + vision model (best-effort, degrades if
                                                      llama3.2-vision isn't installed)
"""

import fitz  # PyMuPDF
import pdfplumber
from pypdf import PdfReader

from config import Config
from core.ocr_engine import extract_text_from_image
from core.vision_engine import describe_image, vision_model_ready


def _table_to_markdown(table_rows) -> str:
    if not table_rows or not table_rows[0]:
        return ""
    rows = [[(cell or "").strip() for cell in row] for row in table_rows]
    header = rows[0]
    md = "| " + " | ".join(header) + " |\n"
    md += "|" + "|".join(["---"] * len(header)) + "|\n"
    for row in rows[1:]:
        md += "| " + " | ".join(row) + " |\n"
    return md


def extract_pdf_content(filepath: str) -> dict:
    """
    Returns:
        {
          "chunks": [ {content, page, type}, ... ],
          "num_pages": int,
          "has_tables": bool,
          "has_images": bool,
        }
    """
    chunks = []
    has_tables = False
    has_images = False

    # ---- 1 & 2: text per page, with OCR fallback for scanned pages ----
    reader = PdfReader(filepath)
    num_pages = len(reader.pages)
    doc_render = fitz.open(filepath)  # used for rendering scanned pages + images

    for i, page in enumerate(reader.pages):
        page_num = i + 1
        text = (page.extract_text() or "").strip()

        if len(text) < Config.OCR_TEXT_THRESHOLD:
            # Likely a scanned page - render it to an image and OCR it instead
            pix = doc_render[i].get_pixmap(dpi=200)
            ocr_text = extract_text_from_image(pix.tobytes("png"))
            if ocr_text:
                text = ocr_text

        if text:
            chunks.append({"content": text, "page": page_num, "type": "text"})

    # ---- 3: tables ----
    with pdfplumber.open(filepath) as pdf:
        for i, page in enumerate(pdf.pages):
            page_num = i + 1
            for table in page.extract_tables():
                md = _table_to_markdown(table)
                if md.strip():
                    has_tables = True
                    chunks.append({"content": md, "page": page_num, "type": "table"})

    # ---- 4: embedded figures/graphs (best-effort, needs llama3.2-vision) ----
# ---- embedded figures/graphs (best-effort, needs llama3.2-vision) ----
    if vision_model_ready():
        images_processed = 0
        for i in range(len(doc_render)):
            if images_processed >= Config.MAX_IMAGES_PER_DOC:
                break
            page = doc_render[i]
            for img_index, img in enumerate(page.get_images(full=True)):
                if images_processed >= Config.MAX_IMAGES_PER_DOC:
                    break
                xref = img[0]
                try:
                    base_image = doc_render.extract_image(xref)
                    image_bytes = base_image["image"]
                    if len(image_bytes) < 5000:
                        continue  # skip tiny icons/logos, not real figures
                    description = describe_image(image_bytes)
                    if description:
                        has_images = True
                        images_processed += 1
                        chunks.append(
                            {"content": f"[Figure on page {i + 1}] {description}",
                             "page": i + 1, "type": "image"}
                        )
                except Exception as e:
                    print(f"[document_loader] skipped image on page {i+1}: {e}")
        if images_processed >= Config.MAX_IMAGES_PER_DOC:
            print(
                f"[document_loader] hit MAX_IMAGES_PER_DOC ({Config.MAX_IMAGES_PER_DOC}) - "
                f"remaining images in this document were skipped for speed."
            )

    doc_render.close()

    return {
        "chunks": chunks,
        "num_pages": num_pages,
        "has_tables": has_tables,
        "has_images": has_images,
    }
