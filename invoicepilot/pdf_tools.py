
import pymupdf


def extract_pdf_text(data):
    doc = pymupdf.open(
        stream=data,
        filetype="pdf"
    )

    try:
        text = "\n".join(
            page.get_text()
            for page in doc
        )

        if not text.strip():
            raise ValueError(
                "No selectable text found. "
                "Scanned PDFs need OCR; "
                "this demo accepts text-based PDFs."
            )

        return text[:30000]

    finally:
        doc.close()
