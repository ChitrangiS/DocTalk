# backend/test_chunker.py

from services.chunker import process_pdf
import json

# Put a real PDF inside backend/
PDF_PATH = "sample.pdf"

DOC_ID = "test_doc_01"

chunks = process_pdf(PDF_PATH, DOC_ID)

print(f"\n{'=' * 50}")
print(f"Total chunks: {len(chunks)}")
print(f"{'=' * 50}\n")

# Inspect first 3 chunks
for chunk in chunks[:3]:

    print(
        f"--- Chunk {chunk['chunk_id']} "
        f"(Page {chunk['page']}, "
        f"{chunk['char_count']} chars) ---"
    )

    print(chunk["text"])
    print()

# Validation checks
assert len(chunks) > 0, "ERROR: No chunks produced"

assert all(
    "doc_id" in c for c in chunks
), "ERROR: Missing doc_id"

assert all(
    "page" in c for c in chunks
), "ERROR: Missing page number"

assert all(
    len(c["text"]) > 0 for c in chunks
), "ERROR: Empty chunk text"

print("✓ All assertions passed.")
print("✓ Chunker working correctly.")

# Save sample output
with open("chunks_output.json", "w") as f:
    json.dump(chunks[:10], f, indent=2)

print("✓ First 10 chunks saved to chunks_output.json")
