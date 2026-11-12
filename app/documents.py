"""Bounded text extraction from user-selected PDF pages; no OCR or execution."""

from io import BytesIO

from pypdf import PdfReader


def pdf_pages(content: bytes) -> list[str]:
    """Extract at most 100 text pages from a PDF of at most 10 MB."""
    if len(content) > 10_000_000 or not content.startswith(b"%PDF-"):
        raise ValueError("Upload a PDF smaller than 10 MB")
    try:
        reader = PdfReader(BytesIO(content))
        if reader.is_encrypted or len(reader.pages) > 100:
            raise ValueError("Use an unencrypted PDF of at most 100 pages")
        pages = []
        for page in reader.pages:
            text = page.extract_text() or ""
            if len(text) > 100000:
                raise ValueError("PDF page text is too large")
            pages.append(text)
        if not any(p.strip() for p in pages):
            raise ValueError("No readable text found; scanned PDFs require OCR first")
        return pages
    except Exception as exc:
        raise ValueError(
            "Unable to extract this PDF. Use a text PDF under 100 pages / 10 MB."
        ) from exc
