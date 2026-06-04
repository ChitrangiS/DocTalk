
import json
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient

from main import create_app
from services.rag import NOT_FOUND_PHRASE

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("test_day5")

PDF_PATH = "sample.pdf"
PASS     = "\033[92m✓ PASS\033[0m"
FAIL     = "\033[91m✗ FAIL\033[0m"
results  = {"passed": 0, "failed": 0}


def section(title: str) -> None:
    print(f"\n{'─'*60}\n  {title}\n{'─'*60}")


def check(condition: bool, msg: str) -> None:
    if condition:
        print(f"  {PASS}  {msg}")
        results["passed"] += 1
    else:
        print(f"  {FAIL}  {msg}")
        results["failed"] += 1


def parse_sse_stream(content: bytes) -> list[str]:
    """
    Split raw SSE response bytes into a list of data payloads.
    Strips 'data: ' prefix and trailing newlines from each event.
    """
    raw = content.decode("utf-8")
    events = []
    for line in raw.split("\n"):
        line = line.strip()
        if line.startswith("data: "):
            events.append(line[len("data: "):])
    return events


def run_tests() -> None:
    client = TestClient(create_app(), raise_server_exceptions=False)

    # ── Test 1: /chat/health — idle state (no PDFs yet) ──────────────
    section("TEST 1 — GET /chat/health")

    r = client.get("/chat/health")
    check(r.status_code == 200,          "GET /chat/health → 200")
    body = r.json()
    check("status"      in body,         "Response has 'status' field")
    check("model"       in body,         "Response has 'model' field")
    check("vector_store" in body,        "Response has 'vector_store' field")
    check(body["status"] in ("ready", "idle"), f"Status is 'ready' or 'idle' (got '{body['status']}')")
    print(f"  model  : {body.get('model')}")
    print(f"  status : {body.get('status')}")

    # ── Test 2: POST /chat/ — missing body ────────────────────────────
    section("TEST 2 — POST /chat/ with no body (422)")

    r = client.post("/chat/", json={})
    check(r.status_code == 422, f"Empty body → 422 Unprocessable Entity (got {r.status_code})")

    # ── Test 3: POST /chat/ — blank question ──────────────────────────
    section("TEST 3 — POST /chat/ with blank question (422)")

    r = client.post("/chat/", json={"doc_id": "abc", "question": "   "})
    check(r.status_code == 422, f"Blank question → 422 (got {r.status_code})")

    # ── Test 4: POST /chat/ — question too short ──────────────────────
    section("TEST 4 — POST /chat/ with question below min_length (422)")

    r = client.post("/chat/", json={"doc_id": "abc", "question": "hi"})
    check(r.status_code == 422, f"Question < 3 chars → 422 (got {r.status_code})")

    # ── Test 5: POST /chat/ — non-existent doc_id ────────────────────
    section("TEST 5 — POST /chat/ with non-existent doc_id")

    # Requires at least one document in the store to avoid the 503 guard.
    # We'll revisit after uploading in Test 7. Skip gracefully if store empty.
    stats_r = client.get("/chat/health")
    if stats_r.json().get("vector_store", {}).get("total_vectors", 0) == 0:
        print("  ⚠  Vector store empty — skipping non-existent doc_id test.")
        print("     (Will re-run implicitly in Test 7 after upload.)")
    else:
        r = client.post(
            "/chat/",
            json={"doc_id": "definitely_not_real_xyz", "question": "What is this about?"},
        )
        check(r.status_code == 200, "Non-existent doc_id → 200 (stream started)")
        events = parse_sse_stream(r.content)
        has_not_found = any(NOT_FOUND_PHRASE in e for e in events)
        check(has_not_found, f"Stream contains NOT_FOUND_PHRASE for missing doc_id")
        check("[DONE]" in events, "Stream ends with [DONE]")

    # ── Test 6: Upload PDF ────────────────────────────────────────────
    section("TEST 6 — Upload PDF (prerequisite for chat tests)")

    if not os.path.exists(PDF_PATH):
        print(f"  ⚠  {PDF_PATH} not found. Skipping chat stream tests.")
        print(f"     Place a text-based PDF at backend/{PDF_PATH} and re-run.")
        _summarise()
        return

    with open(PDF_PATH, "rb") as f:
        pdf_bytes = f.read()

    upload_r = client.post(
        "/upload/",
        files={"file": ("sample.pdf", pdf_bytes, "application/pdf")},
    )
    check(upload_r.status_code == 201,   f"PDF upload → 201 (got {upload_r.status_code})")
    doc_id = upload_r.json().get("doc_id", "")
    check(bool(doc_id),                  f"doc_id received: '{doc_id}'")

    if not doc_id:
        print("  Aborting — cannot run chat tests without a valid doc_id.")
        _summarise()
        return

    # Verify /chat/health now shows ready ─────────────────────────────
    health_r = client.get("/chat/health")
    check(
        health_r.json().get("status") == "ready",
        "GET /chat/health shows 'ready' after upload"
    )

    # ── Test 7: POST /chat/ — valid request, full SSE stream ─────────
    section("TEST 7 — POST /chat/ valid request (full SSE stream)")

    r = client.post(
        "/chat/",
        json={
            "doc_id":   doc_id,
            "question": "What is the main topic of this document?",
        },
    )

    check(r.status_code == 200,               f"POST /chat/ → 200 (got {r.status_code})")
    check(
        "text/event-stream" in r.headers.get("content-type", ""),
        f"Content-Type is text/event-stream (got '{r.headers.get('content-type')}')"
    )
    check(
        r.headers.get("cache-control") == "no-cache",
        "Cache-Control: no-cache header present"
    )
    check(
        r.headers.get("x-accel-buffering") == "no",
        "X-Accel-Buffering: no header present"
    )

    # ── Test 8: SSE wire format ───────────────────────────────────────
    section("TEST 8 — SSE wire format validation")

    events = parse_sse_stream(r.content)
    check(len(events) > 0, f"Stream produced {len(events)} events")

    # Last event must be [DONE]
    check(events[-1] == "[DONE]",               "Last event is '[DONE]'")

    # Second-to-last must start with [SOURCES]
    sources_raw = events[-2] if len(events) >= 2 else ""
    check(
        sources_raw.startswith("[SOURCES]"),
        "Second-to-last event starts with '[SOURCES]'"
    )

    # Token events are everything before the last two
    token_events = events[:-2]
    check(len(token_events) > 0, f"Stream has {len(token_events)} token events before [SOURCES]")

    # ── Test 9: [SOURCES] JSON payload ────────────────────────────────
    section("TEST 9 — [SOURCES] event JSON schema")

    try:
        sources_json = sources_raw.replace("[SOURCES]", "", 1)
        sources_list = json.loads(sources_json)
        check(isinstance(sources_list, list),  "[SOURCES] payload is a JSON array")
        check(len(sources_list) > 0,           f"Sources array is non-empty (len={len(sources_list)})")

        if sources_list:
            first = sources_list[0]
            check("page"    in first, "Source has 'page' field")
            check("excerpt" in first, "Source has 'excerpt' field")
            check("score"   in first, "Source has 'score' field")
            check(
                isinstance(first["page"], int) and first["page"] >= 1,
                f"page is int ≥ 1 (got {first['page']})"
            )
            check(
                0.0 <= first["score"] <= 1.0,
                f"score in [0, 1] (got {first['score']})"
            )
            check(
                isinstance(first["excerpt"], str) and len(first["excerpt"]) > 0,
                "excerpt is non-empty string"
            )

        print(f"\n  Sources received: {len(sources_list)}")
        for s in sources_list:
            print(f"    Page {s['page']} | Score {s['score']:.4f} | {s['excerpt'][:60]}...")

    except json.JSONDecodeError as e:
        check(False, f"[SOURCES] payload is valid JSON: {e}")

    # ── Test 10: Reconstructed answer ─────────────────────────────────
    section("TEST 10 — Reconstructed answer quality")

    reassembled = "".join(
        t.replace("\\n", "\n") for t in token_events
    )
    check(len(reassembled) > 20,    f"Answer is non-trivial (len={len(reassembled)})")
    check(
        reassembled.strip() != NOT_FOUND_PHRASE,
        "Answer is not the NOT_FOUND_PHRASE for a relevant question"
    )

    print(f"\n  Reconstructed answer preview:")
    print(f"  {reassembled[:250]}{'...' if len(reassembled) > 250 else ''}")

    # ── Test 11: Non-existent doc_id with populated store ─────────────
    section("TEST 11 — Non-existent doc_id (store is now populated)")

    r_miss = client.post(
        "/chat/",
        json={"doc_id": "definitely_not_real_xyz_9999", "question": "What is this about?"},
    )
    check(r_miss.status_code == 200, "Non-existent doc_id → 200 (stream opened)")
    miss_events = parse_sse_stream(r_miss.content)
    has_not_found = any(NOT_FOUND_PHRASE in e for e in miss_events)
    check(has_not_found, "Stream contains NOT_FOUND_PHRASE for missing doc_id")
    check("[DONE]" in miss_events, "Stream ends with [DONE] for missing doc_id")

    # ── Test 12: /docs Swagger reflects both routers ─────────────────
    section("TEST 12 — Swagger UI and OpenAPI schema")

    r_docs   = client.get("/docs")
    r_openapi = client.get("/openapi.json")

    check(r_docs.status_code == 200,     "GET /docs → 200 (Swagger UI)")
    check(r_openapi.status_code == 200,  "GET /openapi.json → 200")

    openapi = r_openapi.json()
    paths   = openapi.get("paths", {})
    check("/upload/" in paths, "OpenAPI schema includes /upload/")
    check("/chat/"   in paths, "OpenAPI schema includes /chat/")
    check("/health"  in paths, "OpenAPI schema includes /health")

    # ── Cleanup ───────────────────────────────────────────────────────
    section("CLEANUP")
    del_r = client.delete(f"/upload/{doc_id}")
    check(del_r.status_code == 200, f"Cleanup: deleted doc_id {doc_id}")

    _summarise()


def _summarise() -> None:
    total = results["passed"] + results["failed"]
    print(f"\n{'═'*60}")
    print(f"  Results: {results['passed']}/{total} tests passed")
    if results["failed"] == 0:
        print("  \033[92mAll tests passed. Backend is complete and production-ready.\033[0m")
    else:
        print(f"  \033[91m{results['failed']} test(s) failed — see above.\033[0m")
        sys.exit(1)
    print(f"{'═'*60}\n")


if __name__ == "__main__":
    run_tests()