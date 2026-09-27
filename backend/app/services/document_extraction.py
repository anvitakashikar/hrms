import io
import os
import shutil
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

from fastapi import HTTPException


def extract_text(content: bytes, file_name: str, content_type: str = "") -> str:
    extension = Path(file_name).suffix.lower()
    if extension in {".txt", ".csv"} or content_type.startswith("text/"):
        return content.decode("utf-8", errors="ignore")
    if extension == ".pdf" or content_type == "application/pdf":
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise HTTPException(status_code=503, detail="PDF text extraction dependency is unavailable") from exc
        reader = PdfReader(io.BytesIO(content))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    if extension == ".docx":
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                document = ElementTree.fromstring(archive.read("word/document.xml"))
        except (KeyError, zipfile.BadZipFile, ElementTree.ParseError) as exc:
            raise HTTPException(status_code=422, detail="The DOCX file could not be read") from exc
        return " ".join(node.text or "" for node in document.iter() if node.tag.endswith("}t"))
    if extension in {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}:
        return _extract_image_text(content)
    raise HTTPException(status_code=415, detail="Supported extraction formats are PDF, DOCX, TXT, PNG, and JPEG")


def _extract_image_text(content: bytes) -> str:
    try:
        from PIL import Image
        import pytesseract
    except ImportError as exc:
        raise HTTPException(status_code=503, detail="Image OCR requires Pillow and pytesseract") from exc
    configured_binary = os.environ.get("HRMS_TESSERACT_CMD")
    binary = configured_binary or shutil.which("tesseract")
    if not binary:
        raise HTTPException(status_code=503, detail="Image OCR requires the Tesseract executable; configure HRMS_TESSERACT_CMD")
    pytesseract.pytesseract.tesseract_cmd = binary
    try:
        return pytesseract.image_to_string(Image.open(io.BytesIO(content)))
    except Exception as exc:
        raise HTTPException(status_code=422, detail="Image text could not be extracted") from exc
