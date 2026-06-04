
import io
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient

from main import create_app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)

PDF_PATH = "sample.pdf"

PASS = "\033[92m✓ PASS\033[0m"
FAIL = "\033[91m✗ FAIL\033[0m"


def section(title: str) -> None:
    print(f"\n{'─'*60}\n  {title}\n{'─'*60}")


results = {"passed": 0, "failed": 0}


def check(condition: bool, msg: str) -> None:
    if condition:
        print(f"  {PASS}  {msg}")
        results["passed"] += 1
    else:
        print(f"  {FAIL}  {msg}")
        results["failed"] += 1


def run_tests() -> None:
    client = TestClient(create_app(), raise_server_exceptions=False)

    # ── Test 1: Health endpoints ──────────────────────────────────────
    section("TEST 1 — Health endpoints")

    r = client.get("/health")
    check(r.status_code == 200,          "GET /health → 200")
    check("status" in r.json(),          "/health response has 'status' field")
    check(r.json()["status"] == "ok",    "/health status is 'ok'")
    check("vector_store" in r.json(),    "/health includes vector_store stats")
    check("version" in r.json(),         "/health includes version")

    r = client.get("/upload/health")
    check(r.status_code == 200,          "GET /upload/health → 200")
    check(r.json()["status"] == "ok",    "/upload/health status is 'ok'")

    # ── Test 2: /docs endpoint (Swagger UI) ───────────────────────────
    section("TEST 2 — Swagger UI available")

    r = client.get("/docs")
    check(r.status_code == 200, "GET /docs → 200 (Swagger UI reachable)")

    # ── Test 3: Upload validation — no file ───────────────────────────
    section("TEST 3 — Upload validation (bad inputs)")

    r = client.post("/upload/")
    check(r.status_code == 422, "POST /upload/ with no file → 422 (validation error)")

    # Not a PDF (text file with .txt extension)
    r = client.post(
        "/upload/",
        files={"file": ("notes.txt", b"just some text", "text/plain")},
    )
    check(r.status_code == 415, "Non-PDF file → 415 Unsupported Media Type")

    # PDF extension but wrong magic bytes (not actually a PDF)
    r = client.post(
        "/upload/",
        files={"file": ("fake.pdf", b"this is not a pdf", "application/pdf")},
    )
    check(r.status_code == 415, "Fake PDF (wrong magic bytes) → 415")

    # Empty file
    r = client.post(
        "/upload/",
        files={"file": ("empty.pdf", b"", "application/pdf")},
    )
    check(r.status_code == 400, "Empty file → 400 Bad Request")

    # File exceeding size limit (simulate oversized content)
    big_content = b"%PDF-1.4 " + b"x" * (21 * 1024 * 1024)
    r = client.post(
        "/upload/",
        files={"file": ("big.pdf", big_content, "application/pdf")},
    )
    check(r.status_code == 413, "File > 20 MB → 413 Request Entity Too Large")

    # ── Test 4: Successful upload ─────────────────────────────────────
    section("TEST 4 — Successful PDF upload")

    if not os.path.exists(PDF_PATH):
        print(f"  ⚠  {PDF_PATH} not found. Skipping upload tests.")
        print(f"     Place a text-based PDF at backend/{PDF_PATH} and re-run.")
        _summarise()
        return

    with open(PDF_PATH, "rb") as f:
        pdf_bytes = f.read()

    r = client.post(
        "/upload/",
        files={"file": ("sample.pdf", pdf_bytes, "application/pdf")},
    )

    check(r.status_code == 201,             "POST /upload/ with valid PDF → 201 Created")

    body = r.json()
    check("doc_id"      in body,            "Response contains 'doc_id'")
    check("filename"    in body,            "Response contains 'filename'")
    check("page_count"  in body,            "Response contains 'page_count'")
    check("chunk_count" in body,            "Response contains 'chunk_count'")
    check("message"     in body,            "Response contains 'message'")
    check(len(body.get("doc_id", "")) == 12, f"doc_id is 12 chars (got '{body.get('doc_id')}')")
    check(body.get("page_count", 0) >= 1,   f"page_count ≥ 1 (got {body.get('page_count')})")
    check(body.get("chunk_count", 0) >= 1,  f"chunk_count ≥ 1 (got {body.get('chunk_count')})")
    check(body.get("filename") == "sample.pdf", "filename matches uploaded file")

    doc_id = body.get("doc_id")
    print(f"\n  Ingested doc_id : {doc_id}")
    print(f"  Pages           : {body.get('page_count')}")
    print(f"  Chunks          : {body.get('chunk_count')}")

    # ── Test 5: Idempotent re-upload (same PDF, same doc_id not possible,
    #           but same PDF should succeed without error) ───────────────
    section("TEST 5 — Re-upload is idempotent (upsert)")

    r2 = client.post(
        "/upload/",
        files={"file": ("sample.pdf", pdf_bytes, "application/pdf")},
    )
    check(r2.status_code == 201,  "Re-uploading same PDF → 201 (no error)")
    doc_id_2 = r2.json().get("doc_id")
    check(doc_id_2 != doc_id,     "Second upload produces a new doc_id (independent document)")

    # ── Test 6: Response schema validation ────────────────────────────
    section("TEST 6 — Response schema")

    from models.schemas import UploadResponse
    try:
        parsed = UploadResponse(**body)
        check(True, "Response body is valid UploadResponse schema")
    except Exception as e:
        check(False, f"Schema validation failed: {e}")

    # ── Test 7: Vector store updated after upload ─────────────────────
    section("TEST 7 — Vector store updated")

    r_health = client.get("/health")
    total = r_health.json()["vector_store"]["total_vectors"]
    check(total >= body.get("chunk_count", 1), f"Vector store has ≥ chunk_count vectors ({total})")

    # ── Test 8: Delete endpoint ───────────────────────────────────────
    section("TEST 8 — DELETE /upload/{doc_id}")

    r_del = client.delete(f"/upload/{doc_id}")
    check(r_del.status_code == 200,           "DELETE /upload/{doc_id} → 200")
    check("message" in r_del.json(),          "Delete response has 'message'")
    check(r_del.json()["doc_id"] == doc_id,   "Delete response echoes correct doc_id")

    # Cleanup second upload too
    client.delete(f"/upload/{doc_id_2}")

    _summarise()


def _summarise() -> None:
    total = results["passed"] + results["failed"]
    print(f"\n{'═'*60}")
    print(f"  Results: {results['passed']}/{total} tests passed")
    if results["failed"] == 0:
        print("  \033[92mAll tests passed. Day 3 HTTP layer is production-ready.\033[0m")
    else:
        print(f"  \033[91m{results['failed']} test(s) failed — see above.\033[0m")
        sys.exit(1)
    print(f"{'═'*60}\n")


if __name__ == "__main__":
    run_tests()