from io import BytesIO

import pytest
from pypdf import PdfWriter

from app.documents import pdf_pages


@pytest.mark.parametrize("content", [b"not a PDF", b"%PDF-broken", b"%PDF-" + b"x" * 10_000_000])
def test_invalid_pdf(content):
    with pytest.raises(ValueError):
        pdf_pages(content)


def test_empty_and_encrypted_pdf():
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    output = BytesIO()
    writer.write(output)
    with pytest.raises(ValueError):
        pdf_pages(output.getvalue())
    writer.encrypt("test-password")
    output = BytesIO()
    writer.write(output)
    with pytest.raises(ValueError):
        pdf_pages(output.getvalue())
