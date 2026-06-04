from services.embedder import embed_text
from services.chroma_client import (
    upsert_chunks,
    query_chunks,
    get_collection_stats,
)

DOC_ID = "test_doc"

sample_chunks = [
    {
    "chunk_id": "chunk_1",
    "doc_id": DOC_ID,
    "page": 1,
    "text": "Mitochondria are organelles responsible for producing ATP and cellular energy.",
    "embedding": embed_text(
        "Mitochondria are organelles responsible for producing ATP and cellular energy."
    ),
},
    {
        "chunk_id": "chunk_2",
        "doc_id": DOC_ID,
        "page": 2,
        "text": "Photosynthesis converts sunlight into energy.",
        "embedding": embed_text(
            "Photosynthesis converts sunlight into energy."
        ),
    },
]

print("\nUpserting chunks...")
upsert_chunks(sample_chunks)

print("\nCollection Stats:")
print(get_collection_stats())

query_embedding = embed_text(
    "What creates energy in cells?",
    is_query=True,
)

results = query_chunks(
    query_embedding,
    DOC_ID,
    top_k=3,
)

print("\nResults:")
for r in results:
    print(
        f"Page {r['page']} | "
        f"Score={r['score']} | "
        f"{r['text']}"
    )