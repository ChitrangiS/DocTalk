from services.embedder import (
    embed_text,
    get_embedding_dim,
    cosine_similarity,
)

print("Embedding Dimension:", get_embedding_dim())

v1 = embed_text("The cat sat on the mat")
v2 = embed_text("A feline rested on the floor")
v3 = embed_text("The stock market crashed today")

print("Cat vs Feline:",
      round(cosine_similarity(v1, v2), 3))

print("Cat vs Stock:",
      round(cosine_similarity(v1, v3), 3))