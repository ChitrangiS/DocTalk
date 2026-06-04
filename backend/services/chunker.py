# backend/services/chunker.py

import uuid

import fitz  # PyMuPDF
from langchain_text_splitters import RecursiveCharacterTextSplitter


def extract_text_by_page(pdf_path: str) -> list[dict]:
    """
    Opens a PDF and extracts text page-by-page.

    Returns:
        [
            {
                "page_num": 1,
                "text": "Page content..."
            }
        ]

    Skips pages with almost no text
    (usually scanned/image-only pages).
    """

    doc = fitz.open(pdf_path)

    pages = []

    for page_num in range(len(doc)):
        page = doc[page_num]

        # Extract plain text
        text = page.get_text("text")

        text = text.strip()

        # Skip empty/near-empty pages
        if len(text) < 20:
            continue

        pages.append({
            "page_num": page_num + 1,  # human-readable indexing
            "text": text
        })

    doc.close()

    return pages


def chunk_pages(pages: list[dict], doc_id: str) -> list[dict]:
    """
    Splits extracted pages into overlapping chunks.

    Why chunking matters:
    LLMs and vector DBs work better with small,
    semantically focused text pieces.

    Returns:
        [
            {
                "chunk_id": "...",
                "doc_id": "...",
                "page": 1,
                "text": "...",
                "char_count": 420
            }
        ]
    """

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=512,
        chunk_overlap=50,
        separators=["\n\n", "\n", ". ", " ", ""],
        length_function=len,
    )

    chunks = []

    for page in pages:

        page_chunks = splitter.split_text(page["text"])

        for i, chunk_text in enumerate(page_chunks):

            chunk_text = chunk_text.strip()

            # Ignore tiny fragments
            if len(chunk_text) < 30:
                continue

            chunks.append({
                "chunk_id": f"{doc_id}_p{page['page_num']}_c{i}",
                "doc_id": doc_id,
                "page": page["page_num"],
                "text": chunk_text,
                "char_count": len(chunk_text),
            })

    return chunks


def process_pdf(pdf_path: str, doc_id: str = None) -> list[dict]:
    """
    Main pipeline function.

    Flow:
    PDF → extract pages → chunk text → return chunks
    """

    if doc_id is None:
        doc_id = str(uuid.uuid4())[:8]

    pages = extract_text_by_page(pdf_path)

    if not pages:
        raise ValueError(
            f"No extractable text found in {pdf_path}. "
            "It may be a scanned PDF."
        )

    chunks = chunk_pages(pages, doc_id)

    print(f"✓ Processed {len(pages)} pages → {len(chunks)} chunks")

    return chunks