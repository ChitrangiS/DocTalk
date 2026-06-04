# test_rag_manual.py

from services.rag import get_answer

DOC_ID = "92a782f1b213"   

result = get_answer(
    DOC_ID,
    "What is this document about?"
)

print("\nANSWER:")
print(result.answer)

print("\nSOURCES:")
for s in result.sources:
    print(
        f"Page={s.page}, "
        f"Score={s.score}"
    )

print("\nNOT FOUND:")
print(result.is_not_found)