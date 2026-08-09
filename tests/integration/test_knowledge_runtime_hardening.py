"""PHASE 2.1 — async processing observability, OCR heuristics, race safety."""

from __future__ import annotations

import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from apps.api.main import create_app
from limen.config import settings as settings_module
from limen.knowledge.ingestion import KnowledgeIngestionService
from limen.knowledge.jobs import reset_knowledge_job_runner_for_tests
from limen.knowledge.ocr import (
    OCRUnavailableError,
    TesseractOCRProvider,
    document_needs_ocr,
    page_needs_ocr,
    tesseract_available,
)
from limen.knowledge.parsing import parse_document
from limen.persistence.database import get_database, reset_database_for_tests
from limen.persistence.repositories.knowledge import SqliteKnowledgeRepository

PASSWORD = "umbral-seguro-2026"
PROBE = "The LIMEN synthetic recovery protocol identifies marker ZXQ-417 uniquely."


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "p21.db"))
    monkeypatch.setenv("DOCUMENT_PATH", str(tmp_path / "documents"))
    monkeypatch.setenv("VECTOR_PATH", str(tmp_path / "vectors"))
    monkeypatch.setenv("EMBEDDING_PROVIDER", "stub")
    monkeypatch.setenv("LLM_PROVIDER", "stub")
    settings_module.get_settings.cache_clear()
    reset_database_for_tests()
    from limen.knowledge.vector_store import reset_vector_store_for_tests

    reset_vector_store_for_tests()
    reset_knowledge_job_runner_for_tests()
    with TestClient(create_app(settings_module.get_settings())) as test_client:
        yield test_client
    reset_knowledge_job_runner_for_tests()
    reset_vector_store_for_tests()
    reset_database_for_tests()
    settings_module.get_settings.cache_clear()


def _register(client: TestClient) -> None:
    assert (
        client.post(
            "/api/auth/register",
            json={
                "email": "p21@umbral.io",
                "password": PASSWORD,
                "display_name": "P21",
            },
        ).status_code
        == 201
    )


def _wait(
    client: TestClient, document_id: str, wanted: set[str], timeout: float = 8.0
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    last: dict[str, Any] = {}
    while time.monotonic() < deadline:
        last = client.get(f"/api/knowledge/documents/{document_id}").json()
        if last["status"] in wanted:
            return last
        time.sleep(0.05)
    raise AssertionError(f"timeout for {wanted}: {last}")


def test_post_returns_before_available(client: TestClient) -> None:
    _register(client)
    uploaded = client.post(
        "/api/knowledge/documents",
        files={"file": ("async.txt", PROBE.encode(), "text/plain")},
    )
    assert uploaded.status_code == 201
    body = uploaded.json()
    assert body["status"] == "PROCESSING"
    assert body["status"] != "AVAILABLE"
    # Drain background work so later tests do not race the shared DB singleton.
    _wait(client, body["document_id"], {"AVAILABLE", "FAILED"})


def test_processing_observable_then_available(client: TestClient) -> None:
    _register(client)
    uploaded = client.post(
        "/api/knowledge/documents",
        files={"file": ("obs.txt", PROBE.encode(), "text/plain")},
    )
    document_id = uploaded.json()["document_id"]
    assert uploaded.json()["status"] == "PROCESSING"

    listed = client.get("/api/knowledge/documents").json()
    match = next(item for item in listed if item["document_id"] == document_id)
    assert match["status"] in {"PROCESSING", "AVAILABLE"}

    final = _wait(client, document_id, {"AVAILABLE"})
    assert final["chunk_count"] and final["chunk_count"] > 0


def test_processing_failure_becomes_failed(client: TestClient) -> None:
    _register(client)
    uploaded = client.post(
        "/api/knowledge/documents",
        files={"file": ("bad.pdf", b"%PDF-1.4 corrupt", "application/pdf")},
    )
    failed = _wait(client, uploaded.json()["document_id"], {"FAILED"})
    assert failed["failure_stage"]
    assert failed["failure_message"]


def test_restart_policy_fails_processing_documents(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "restart.db"))
    monkeypatch.setenv("DOCUMENT_PATH", str(tmp_path / "docs"))
    monkeypatch.setenv("VECTOR_PATH", str(tmp_path / "vectors"))
    monkeypatch.setenv("EMBEDDING_PROVIDER", "stub")
    settings_module.get_settings.cache_clear()
    reset_database_for_tests()
    from limen.knowledge.vector_store import reset_vector_store_for_tests

    reset_vector_store_for_tests()
    settings = settings_module.get_settings()
    settings.ensure_runtime_dirs()
    db = get_database(settings)
    db.initialize()
    repo = SqliteKnowledgeRepository(db)
    # Simulate orphaned PROCESSING row without going through auth account FK:
    # create a minimal account first.
    db.connection.execute(
        "INSERT INTO accounts(account_id, email, display_name, password_hash, created_at) "
        "VALUES ('acct', 'a@b.c', 'A', 'x', '2020-01-01T00:00:00+00:00')"
    )
    db.connection.commit()
    doc = repo.create_document(
        account_id="acct",
        source_name="stuck.txt",
        size_bytes=3,
        storage_path="",
        sha256="abc",
    )
    repo.mark_processing("acct", doc["document_id"])
    assert repo.get_document("acct", doc["document_id"])["status"] == "PROCESSING"

    count = KnowledgeIngestionService(repo, settings).fail_interrupted_processing()
    assert count == 1
    failed = repo.get_document("acct", doc["document_id"])
    assert failed["status"] == "FAILED"
    assert failed["failure_stage"] == "interrupted_processing"
    reset_vector_store_for_tests()
    reset_database_for_tests()
    settings_module.get_settings.cache_clear()


def test_delete_during_processing_never_becomes_available(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "race.db"))
    monkeypatch.setenv("DOCUMENT_PATH", str(tmp_path / "docs"))
    monkeypatch.setenv("VECTOR_PATH", str(tmp_path / "vectors"))
    monkeypatch.setenv("EMBEDDING_PROVIDER", "stub")
    settings_module.get_settings.cache_clear()
    reset_database_for_tests()
    from limen.knowledge.vector_store import reset_vector_store_for_tests

    reset_vector_store_for_tests()
    settings = settings_module.get_settings()
    settings.ensure_runtime_dirs()
    db = get_database(settings)
    db.initialize()
    db.connection.execute(
        "INSERT INTO accounts(account_id, email, display_name, password_hash, created_at) "
        "VALUES ('acct', 'race@b.c', 'A', 'x', '2020-01-01T00:00:00+00:00')"
    )
    db.connection.commit()
    repo = SqliteKnowledgeRepository(db)
    ingest = KnowledgeIngestionService(repo, settings)
    from limen.knowledge.deletion import KnowledgeDeletionService

    accepted = ingest.accept_upload(
        account_id="acct",
        filename="race.txt",
        payload=PROBE.encode(),
    )
    assert accepted["status"] == "PROCESSING"
    deleted = KnowledgeDeletionService(repo).delete(
        account_id="acct", document_id=accepted["document_id"]
    )
    assert deleted is not None
    assert deleted["status"] == "REMOVED"

    after = ingest.process_document(account_id="acct", document_id=accepted["document_id"])
    assert after is not None
    assert after["status"] == "REMOVED"
    hits = repo.retrieve(account_id="acct", query="ZXQ-417", limit=5)
    assert hits == []
    reset_vector_store_for_tests()
    reset_database_for_tests()
    settings_module.get_settings.cache_clear()


def test_page_needs_ocr_heuristic() -> None:
    assert page_needs_ocr("") is True
    assert page_needs_ocr("short") is True
    sparse = ".... .... .... .... .... .... .... ...."
    assert page_needs_ocr(sparse) is True
    rich = "Postoperative fever monitoring protocol. " * 3
    assert page_needs_ocr(rich) is False
    assert document_needs_ocr(["", "   "]) is True
    assert document_needs_ocr([rich]) is False


def test_text_native_pdf_does_not_invoke_ocr(tmp_path: Path) -> None:
    import fitz

    path = tmp_path / "native.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text(
        (72, 72),
        "Postoperative wound care instructions with adequate extractable text content.",
    )
    doc.save(path)
    doc.close()

    class CountingOCR:
        def __init__(self) -> None:
            self.calls = 0

        def extract_pages(self, p: Path) -> list[tuple[int, str]]:
            self.calls += 1
            return [(1, "SHOULD NOT RUN")]

        def extract_page(self, p: Path, page_number: int) -> str:
            self.calls += 1
            return "SHOULD NOT RUN"

    ocr = CountingOCR()
    parsed = parse_document(path, filename="native.pdf", ocr=ocr)
    assert parsed.ocr_applied is False
    assert ocr.calls == 0
    assert "wound" in parsed.pages[0].text.lower()


def test_textless_pdf_invokes_ocr_and_preserves_provenance(tmp_path: Path) -> None:
    import fitz

    path = tmp_path / "scan.pdf"
    doc = fitz.open()
    page = doc.new_page()
    # Image-only page: draw rectangle, no text layer.
    page.draw_rect(page.rect, color=(0.8, 0.8, 0.8), fill=(0.9, 0.9, 0.9))
    doc.save(path)
    doc.close()

    class FakeOCR:
        def extract_pages(self, p: Path) -> list[tuple[int, str]]:
            return [(1, "OCR recovered marker ZXQ-417 from scan")]

        def extract_page(self, p: Path, page_number: int) -> str:
            assert page_number == 1
            return "OCR recovered marker ZXQ-417 from scan"

    parsed = parse_document(path, filename="scan.pdf", ocr=FakeOCR())
    assert parsed.ocr_applied is True
    assert parsed.pages[0].page == 1
    assert "ZXQ-417" in parsed.pages[0].text


def test_ocr_failure_never_available(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "ocrfail.db"))
    monkeypatch.setenv("DOCUMENT_PATH", str(tmp_path / "docs"))
    monkeypatch.setenv("VECTOR_PATH", str(tmp_path / "vectors"))
    monkeypatch.setenv("EMBEDDING_PROVIDER", "stub")
    settings_module.get_settings.cache_clear()
    reset_database_for_tests()
    from limen.knowledge.vector_store import reset_vector_store_for_tests

    reset_vector_store_for_tests()
    settings = settings_module.get_settings()
    settings.ensure_runtime_dirs()
    db = get_database(settings)
    db.initialize()
    db.connection.execute(
        "INSERT INTO accounts(account_id, email, display_name, password_hash, created_at) "
        "VALUES ('acct', 'ocr@b.c', 'A', 'x', '2020-01-01T00:00:00+00:00')"
    )
    db.connection.commit()

    import fitz

    path = tmp_path / "docs" / "acct"
    path.mkdir(parents=True)
    pdf = path / "empty.pdf"
    doc = fitz.open()
    doc.new_page()
    doc.save(pdf)
    doc.close()

    repo = SqliteKnowledgeRepository(db)
    ingest = KnowledgeIngestionService(repo, settings)
    accepted = ingest.accept_upload(
        account_id="acct",
        filename="empty.pdf",
        payload=pdf.read_bytes(),
    )

    class BoomOCR:
        def extract_pages(self, p: Path) -> list[tuple[int, str]]:
            raise OCRUnavailableError("boom")

        def extract_page(self, p: Path, page_number: int) -> str:
            raise OCRUnavailableError("boom")

    monkeypatch.setattr(
        "limen.knowledge.parsing.default_ocr_provider",
        lambda: BoomOCR(),
    )
    result = ingest.process_document(account_id="acct", document_id=accepted["document_id"])
    assert result is not None
    assert result["status"] == "FAILED"
    assert result["failure_stage"] == "ocr"
    reset_vector_store_for_tests()
    reset_database_for_tests()
    settings_module.get_settings.cache_clear()


def test_tesseract_adapter_unavailable_without_binary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Always exercise the missing-binary path (even if tesseract is installed)."""
    monkeypatch.setattr("limen.knowledge.ocr.shutil.which", lambda _name: None)
    provider = TesseractOCRProvider()
    with pytest.raises(OCRUnavailableError, match="tesseract binary"):
        provider.extract_pages(Path("/tmp/nope.pdf"))


@pytest.mark.skipif(not tesseract_available(), reason="tesseract binary not installed")
def test_tesseract_adapter_reads_rendered_page(tmp_path: Path) -> None:
    import fitz

    path = tmp_path / "tess.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "LIMEN Tesseract Marker ZXQ-417")
    # Convert to image-only by rendering and embedding — wipe text via pixmap roundtrip.
    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
    out = fitz.open()
    img_page = out.new_page(width=page.rect.width, height=page.rect.height)
    img_page.insert_image(img_page.rect, pixmap=pix)
    out.save(path)
    out.close()
    doc.close()

    text = TesseractOCRProvider(lang="eng").extract_page(path, 1)
    assert "ZXQ" in text.upper() or "417" in text or "LIMEN" in text.upper()
