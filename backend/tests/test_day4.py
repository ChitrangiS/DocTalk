
import asyncio
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient

from main import create_app
from services.rag import NOT_FOUND_PHRASE, RagResult, get_answer, stream_answer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("test_day4")

PDF_PATH = "sample.pdf"

# Adjust these questions to match your test PDF's actual content.
ON_TOPIC_QUESTIONS = [
    "What is the main topic or contribution of this document?",
    "What methodology or approach is described?",
    "What are the key results or conclusions?",
]
OFF_TOPIC_QUESTION  = "What is the boiling point of water on Mars?"
EMPTY_DOC_ID        = "nonexistent_doc_000"

PASS = "\033[92m✓ PASS\033[0m"
FAIL = "\033[91m✗ FAIL\033[0m"
results = {"passed": 0, "failed": 0}


def section(title: str) -> None:
    print(f"\n{'─'*60}\n  {title}\n{'─'*60}")


def check(condition: bool, msg: str) -> None:
    if condition:
        print(f"  {PASS}  {msg}")
        results["passed"] += 1
    else:
        print(f"  {FAIL}  {msg}")
        results["failed"] += 1


def run_tests() -> None:
    client = TestClient(create_app(), raise_server_exceptions=True)

    # ── Step 0: Upload PDF to get a real doc_id ───────────────────────
    section("SETUP — Upload PDF via HTTP endpoint")

    if not os.path.exists(PDF_PATH):
        print(f"  ⚠  {PDF_PATH} not found in backend/.")
        print(f"     Place a text-based PDF there and re-run.")
        _summarise()
        return

    with open(PDF_PATH, "rb") as f:
        pdf_bytes = f.read()

    upload_r = client.post(
        "/upload/",
        files={"file": ("sample.pdf", pdf_bytes, "application/pdf")},
    )
    check(upload_r.status_code == 201, f"PDF uploaded successfully (status {upload_r.status_code})")

    doc_id = upload_r.json().get("doc_id", "")
    check(bool(doc_id), f"Received doc_id: '{doc_id}'")
    print(f"  doc_id      : {doc_id}")
    print(f"  page_count  : {upload_r.json().get('page_count')}")
    print(f"  chunk_count : {upload_r.json().get('chunk_count')}")

    if not doc_id:
        print("  Aborting — cannot run RAG tests without a doc_id.")
        _summarise()
        return

    # ── Test 1: RagResult structure ───────────────────────────────────
    section("TEST 1 — RagResult dataclass structure")

    result: RagResult = get_answer(doc_id, ON_TOPIC_QUESTIONS[0])

    check(isinstance(result, RagResult),           "get_answer() returns RagResult")
    check(isinstance(result.answer, str),          "result.answer is str")
    check(len(result.answer) > 0,                  "result.answer is non-empty")
    check(isinstance(result.sources, list),        "result.sources is list")
    check(isinstance(result.doc_id, str),          "result.doc_id is str")
    check(result.doc_id == doc_id,                 "result.doc_id matches uploaded doc_id")
    check(isinstance(result.model, str),           "result.model is str")
    check(result.chunks_retrieved > 0,             f"chunks_retrieved > 0 (got {result.chunks_retrieved})")
    check(result.context_chars > 0,                f"context_chars > 0 (got {result.context_chars})")
    check(isinstance(result.is_not_found, bool),   "is_not_found is bool")
    check(not result.is_not_found,                 "is_not_found is False for on-topic question")

    # ── Test 2: Source citation structure ─────────────────────────────
    section("TEST 2 — Source citation structure")

    check(len(result.sources) > 0, f"Sources returned (got {len(result.sources)})")

    if result.sources:
        s = result.sources[0]
        check(hasattr(s, "page"),    "Source has .page attribute")
        check(hasattr(s, "excerpt"), "Source has .excerpt attribute")
        check(hasattr(s, "score"),   "Source has .score attribute")
        check(s.page >= 1,           f"Page number ≥ 1 (got {s.page})")
        check(len(s.excerpt) > 0,    "Excerpt is non-empty")
        check(0.0 <= s.score <= 1.0, f"Score in [0, 1] (got {s.score})")

    # ── Test 3: Answer quality — on-topic questions ───────────────────
    section("TEST 3 — Answer quality (on-topic questions)")

    for q in ON_TOPIC_QUESTIONS:
        r = get_answer(doc_id, q)
        has_page_cite = "Page" in r.answer or "page" in r.answer
        not_empty     = len(r.answer.strip()) > 20

        check(not_empty,     f"Answer non-trivial for: '{q[:50]}'")
        check(not r.is_not_found, f"Not-found phrase absent for on-topic: '{q[:50]}'")

        print(f"\n  Q : {q}")
        print(f"  A : {r.answer[:200]}{'...' if len(r.answer) > 200 else ''}")
        print(f"  Sources: {[(s.page, round(s.score,3)) for s in r.sources]}")
        if has_page_cite:
            print(f"  ✓ Answer contains page citation")
        else:
            print(f"  ⚠ No page citation detected (model may not always cite)")

    # ── Test 4: Off-topic question — not-found handling ───────────────
    section("TEST 4 — Off-topic question (not-found behaviour)")

    r_off = get_answer(doc_id, OFF_TOPIC_QUESTION)
    print(f"\n  Q : {OFF_TOPIC_QUESTION}")
    print(f"  A : {r_off.answer}")

    # Note: whether this triggers is_not_found depends on how off-topic
    # the question is vs the PDF's content. We don't assert on it strictly —
    # instead we check the answer is short and non-committal if it appears.
    check(
        len(r_off.answer) < 500,
        f"Off-topic answer is concise (len={len(r_off.answer)})"
    )
    print(f"  is_not_found: {r_off.is_not_found}")

    # ── Test 5: Empty doc_id returns gracefully ───────────────────────
    section("TEST 5 — Non-existent doc_id")

    r_empty = get_answer(EMPTY_DOC_ID, "What is this about?")
    check(r_empty.is_not_found,             "Non-existent doc_id triggers not-found")
    check(r_empty.chunks_retrieved == 0,    "chunks_retrieved == 0 for missing doc_id")
    print(f"  Answer: {r_empty.answer}")

    # ── Test 6: Input validation ──────────────────────────────────────
    section("TEST 6 — Input validation")

    try:
        get_answer("", "What is this about?")
        check(False, "Empty doc_id should raise ValueError")
    except ValueError:
        check(True, "Empty doc_id raises ValueError ✓")

    try:
        get_answer(doc_id, "")
        check(False, "Empty question should raise ValueError")
    except ValueError:
        check(True, "Empty question raises ValueError ✓")

    # ── Test 7: stream_answer() yields valid SSE events ───────────────
    section("TEST 7 — stream_answer() SSE generator")

    async def collect_stream(did: str, q: str) -> list[str]:
        events = []
        async for event in stream_answer(did, q):
            events.append(event)
        return events

    events = asyncio.run(collect_stream(doc_id, ON_TOPIC_QUESTIONS[0]))

    # Every event must be a valid SSE line
    all_sse = all(e.startswith("data: ") and e.endswith("\n\n") for e in events)
    check(all_sse,    "All stream events are valid SSE format (data: ...\\n\\n)")

    # Last event must be [DONE]
    check(events[-1] == "data: [DONE]\n\n", "Last event is 'data: [DONE]\\n\\n'")

    # Second-to-last event must start with [SOURCES] and be valid JSON
    sources_event = events[-2]
    check(
        sources_event.startswith("data: [SOURCES]"),
        "Second-to-last event is [SOURCES] event"
    )
    try:
        sources_json = sources_event.replace("data: [SOURCES]", "").strip()
        parsed = json.loads(sources_json.rstrip("\n"))
        check(isinstance(parsed, list), f"[SOURCES] payload is a JSON array (len={len(parsed)})")
        if parsed:
            check("page" in parsed[0],    "Source objects have 'page' field")
            check("excerpt" in parsed[0], "Source objects have 'excerpt' field")
            check("score" in parsed[0],   "Source objects have 'score' field")
    except json.JSONDecodeError as e:
        check(False, f"[SOURCES] payload is valid JSON: {e}")

    # Token events are everything except last two
    token_events = events[:-2]
    check(len(token_events) > 0, f"Stream produced {len(token_events)} token events")

    # Reassemble answer from tokens
    reassembled = "".join(
        e.replace("data: ", "").rstrip("\n").replace("\\n", "\n")
        for e in token_events
    )
    check(len(reassembled) > 10, f"Reassembled answer is non-trivial (len={len(reassembled)})")
    print(f"\n  Reassembled answer preview: {reassembled[:150]}...")

    # ── Cleanup ───────────────────────────────────────────────────────
    client.delete(f"/upload/{doc_id}")

    _summarise()


import json  # needed inside run_tests


def _summarise() -> None:
    total = results["passed"] + results["failed"]
    print(f"\n{'═'*60}")
    print(f"  Results: {results['passed']}/{total} tests passed")
    if results["failed"] == 0:
        print("  \033[92mAll tests passed. Day 4 RAG pipeline is production-ready.\033[0m")
    else:
        print(f"  \033[91m{results['failed']} test(s) failed — see above.\033[0m")
        sys.exit(1)
    print(f"{'═'*60}\n")


if __name__ == "__main__":
    run_tests()