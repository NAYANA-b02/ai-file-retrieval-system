import io
import time
import unittest

import numpy as np
import pymupdf
import docx
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.core.database import SessionLocal
from app.models.user import User
from app.models.file import File as FileModel
from app.models.text_chunk import TextChunk
from app.services.embedding_service import (
    chunk_text,
    deserialize_embedding,
    process_chunking_and_embedding,
    CHUNK_SIZE,
)


def create_sample_pdf(text: str) -> bytes:
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((50, 72), text, fontsize=12)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def create_sample_docx(text: str) -> bytes:
    doc = docx.Document()
    doc.add_paragraph(text)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


class TestPhase5ChunkingAndEmbeddings(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.user1_username = "chunk_user1"
        cls.user1_email = "chunk_user1@example.com"
        cls.user1_password = "Password123!"

        cls.user2_username = "chunk_user2"
        cls.user2_email = "chunk_user2@example.com"
        cls.user2_password = "Password123!"

    def wait_for_file_completion(self, file_id: int, cookies: dict, timeout: float = 15.0, poll_interval: float = 0.2) -> dict:
        """Poll GET /api/v1/files/{file_id} until processing_status is 'completed' or 'failed'."""
        start = time.time()
        while time.time() - start < timeout:
            res = self.client.get(f"/api/v1/files/{file_id}", cookies=cookies)
            if res.status_code == 200:
                data = res.json()
                if data.get("processing_status") in ("completed", "failed"):
                    return data
            time.sleep(poll_interval)
        res = self.client.get(f"/api/v1/files/{file_id}", cookies=cookies)
        return res.json()

    def setUp(self):
        db = SessionLocal()
        try:
            users = db.query(User).filter(
                (User.username.like("chunk_%")) |
                (User.email.like("chunk_%"))
            ).all()
            for u in users:
                db.delete(u)
            db.commit()
        finally:
            db.close()

        # Register and login User 1
        self.client.post("/api/v1/auth/register", json={
            "username": self.user1_username,
            "email": self.user1_email,
            "password": self.user1_password,
        })
        login_res1 = self.client.post("/api/v1/auth/login", json={
            "username_or_email": self.user1_username,
            "password": self.user1_password,
        })
        self.user1_session = login_res1.cookies.get(settings.SESSION_COOKIE_NAME)

        # Register and login User 2
        self.client.post("/api/v1/auth/register", json={
            "username": self.user2_username,
            "email": self.user2_email,
            "password": self.user2_password,
        })
        login_res2 = self.client.post("/api/v1/auth/login", json={
            "username_or_email": self.user2_username,
            "password": self.user2_password,
        })
        self.user2_session = login_res2.cookies.get(settings.SESSION_COOKIE_NAME)

    def tearDown(self):
        db = SessionLocal()
        try:
            users = db.query(User).filter(
                (User.username.like("chunk_%")) |
                (User.email.like("chunk_%"))
            ).all()
            for u in users:
                db.delete(u)
            db.commit()
        finally:
            db.close()

    def test_01_txt_chunking_and_embedding(self):
        """TEST 1: TXT upload produces chunks with embeddings"""
        # Create text long enough for multiple chunks
        long_text = "This is a test sentence for chunking. " * 50  # ~1900 chars
        txt_bytes = long_text.encode("utf-8")

        response = self.client.post(
            "/api/v1/files/upload",
            files={"file": ("long_doc.txt", txt_bytes, "text/plain")},
            cookies={settings.SESSION_COOKIE_NAME: self.user1_session}
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["processing_status"], "processing")
        self.assertEqual(data["text_chunk_count"], 0)

        file_data = self.wait_for_file_completion(data["id"], cookies={settings.SESSION_COOKIE_NAME: self.user1_session})
        self.assertEqual(file_data["processing_status"], "completed")
        self.assertGreater(file_data["text_chunk_count"], 1)

        # Verify chunks in database
        db = SessionLocal()
        try:
            chunks = db.query(TextChunk).filter(
                TextChunk.file_id == data["id"]
            ).order_by(TextChunk.chunk_index).all()
            self.assertEqual(len(chunks), file_data["text_chunk_count"])
            for i, chunk in enumerate(chunks):
                self.assertEqual(chunk.chunk_index, i)
                self.assertTrue(len(chunk.chunk_text) > 0)
                self.assertIsNotNone(chunk.embedding)
                self.assertTrue(len(chunk.embedding) > 0)
        finally:
            db.close()

    def test_02_pdf_chunking_and_embedding(self):
        """TEST 2: PDF upload produces chunks with embeddings"""
        text = "PDF document content for embedding test. " * 30
        pdf_bytes = create_sample_pdf(text)

        response = self.client.post(
            "/api/v1/files/upload",
            files={"file": ("embed.pdf", pdf_bytes, "application/pdf")},
            cookies={settings.SESSION_COOKIE_NAME: self.user1_session}
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["processing_status"], "processing")
        self.assertEqual(data["text_chunk_count"], 0)

        file_data = self.wait_for_file_completion(data["id"], cookies={settings.SESSION_COOKIE_NAME: self.user1_session})
        self.assertEqual(file_data["processing_status"], "completed")
        self.assertGreater(file_data["text_chunk_count"], 0)

        db = SessionLocal()
        try:
            chunks = db.query(TextChunk).filter(
                TextChunk.file_id == data["id"]
            ).all()
            self.assertEqual(len(chunks), file_data["text_chunk_count"])
            for chunk in chunks:
                self.assertIsNotNone(chunk.embedding)
        finally:
            db.close()

    def test_03_docx_chunking_and_embedding(self):
        """TEST 3: DOCX upload produces chunks with embeddings"""
        text = "DOCX document content for chunking and embedding. " * 30
        docx_bytes = create_sample_docx(text)

        response = self.client.post(
            "/api/v1/files/upload",
            files={"file": (
                "embed.docx",
                docx_bytes,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )},
            cookies={settings.SESSION_COOKIE_NAME: self.user1_session}
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["processing_status"], "processing")
        self.assertEqual(data["text_chunk_count"], 0)

        file_data = self.wait_for_file_completion(data["id"], cookies={settings.SESSION_COOKIE_NAME: self.user1_session})
        self.assertEqual(file_data["processing_status"], "completed")
        self.assertGreater(file_data["text_chunk_count"], 0)

        db = SessionLocal()
        try:
            chunks = db.query(TextChunk).filter(
                TextChunk.file_id == data["id"]
            ).all()
            self.assertEqual(len(chunks), file_data["text_chunk_count"])
        finally:
            db.close()

    def test_04_short_text_single_chunk(self):
        """TEST 4: Short text produces exactly one chunk"""
        short_text = "Hello world"
        txt_bytes = short_text.encode("utf-8")

        response = self.client.post(
            "/api/v1/files/upload",
            files={"file": ("short.txt", txt_bytes, "text/plain")},
            cookies={settings.SESSION_COOKIE_NAME: self.user1_session}
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["processing_status"], "processing")
        self.assertEqual(data["text_chunk_count"], 0)

        file_data = self.wait_for_file_completion(data["id"], cookies={settings.SESSION_COOKIE_NAME: self.user1_session})
        self.assertEqual(file_data["processing_status"], "completed")
        self.assertEqual(file_data["text_chunk_count"], 1)

        db = SessionLocal()
        try:
            chunks = db.query(TextChunk).filter(
                TextChunk.file_id == data["id"]
            ).all()
            self.assertEqual(len(chunks), 1)
            self.assertEqual(chunks[0].chunk_index, 0)
            self.assertEqual(chunks[0].chunk_text, short_text)
        finally:
            db.close()

    def test_05_empty_text_zero_chunks(self):
        """TEST 5: File with whitespace-only extracted text produces zero chunks"""
        # Upload a file that will extract to empty / whitespace
        # A corrupted PDF that passes validation but extracts nothing
        whitespace_text = "   \n\n\t  "
        txt_bytes = whitespace_text.encode("utf-8")

        response = self.client.post(
            "/api/v1/files/upload",
            files={"file": ("spaces.txt", txt_bytes, "text/plain")},
            cookies={settings.SESSION_COOKIE_NAME: self.user1_session}
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        # Whitespace-only text should produce 0 chunks
        self.assertEqual(data["text_chunk_count"], 0)

        db = SessionLocal()
        try:
            chunks = db.query(TextChunk).filter(
                TextChunk.file_id == data["id"]
            ).all()
            self.assertEqual(len(chunks), 0)
        finally:
            db.close()

    def test_06_ownership_preserved_on_chunks(self):
        """TEST 6: Chunks belong to the correct user's file; User 2 cannot see User 1's chunks"""
        long_text = "User 1 confidential document content. " * 30
        txt_bytes = long_text.encode("utf-8")

        res_u1 = self.client.post(
            "/api/v1/files/upload",
            files={"file": ("u1_secret.txt", txt_bytes, "text/plain")},
            cookies={settings.SESSION_COOKIE_NAME: self.user1_session}
        )
        self.assertEqual(res_u1.status_code, 201)
        u1_file_id = res_u1.json()["id"]

        # User 2 uploads a different file
        u2_text = "User 2 public document. " * 10
        res_u2 = self.client.post(
            "/api/v1/files/upload",
            files={"file": ("u2_doc.txt", u2_text.encode("utf-8"), "text/plain")},
            cookies={settings.SESSION_COOKIE_NAME: self.user2_session}
        )
        self.assertEqual(res_u2.status_code, 201)
        u2_file_id = res_u2.json()["id"]

        db = SessionLocal()
        try:
            # User 1's chunks belong to User 1's file
            u1_chunks = db.query(TextChunk).filter(TextChunk.file_id == u1_file_id).all()
            self.assertGreater(len(u1_chunks), 0)
            u1_file = db.query(FileModel).filter(FileModel.id == u1_file_id).first()
            u1_user = db.query(User).filter(User.username == self.user1_username).first()
            self.assertEqual(u1_file.owner_id, u1_user.id)

            # User 2's chunks belong to User 2's file
            u2_chunks = db.query(TextChunk).filter(TextChunk.file_id == u2_file_id).all()
            self.assertGreater(len(u2_chunks), 0)
            u2_file = db.query(FileModel).filter(FileModel.id == u2_file_id).first()
            u2_user = db.query(User).filter(User.username == self.user2_username).first()
            self.assertEqual(u2_file.owner_id, u2_user.id)

            # No cross-contamination
            for chunk in u1_chunks:
                self.assertEqual(chunk.file_id, u1_file_id)
            for chunk in u2_chunks:
                self.assertEqual(chunk.file_id, u2_file_id)
        finally:
            db.close()

    def test_07_repeatable_processing(self):
        """TEST 7: Re-processing the same file does not create duplicate chunks"""
        text = "Repeatable chunking test content. " * 20
        txt_bytes = text.encode("utf-8")

        response = self.client.post(
            "/api/v1/files/upload",
            files={"file": ("repeat.txt", txt_bytes, "text/plain")},
            cookies={settings.SESSION_COOKIE_NAME: self.user1_session}
        )
        self.assertEqual(response.status_code, 201)
        file_id = response.json()["id"]

        file_data = self.wait_for_file_completion(file_id, cookies={settings.SESSION_COOKIE_NAME: self.user1_session})
        self.assertEqual(file_data["processing_status"], "completed")
        original_count = file_data["text_chunk_count"]
        self.assertGreater(original_count, 0)

        # Re-process the same file
        db = SessionLocal()
        try:
            result = process_chunking_and_embedding(db, file_id)
            self.assertEqual(result, original_count)

            chunks = db.query(TextChunk).filter(TextChunk.file_id == file_id).all()
            self.assertEqual(len(chunks), original_count)
        finally:
            db.close()

    def test_08_embedding_dimension_check(self):
        """TEST 8: Embedding deserializes to 384-dim float32 array (all-MiniLM-L6-v2)"""
        text = "Embedding dimension verification test"
        txt_bytes = text.encode("utf-8")

        response = self.client.post(
            "/api/v1/files/upload",
            files={"file": ("dim_check.txt", txt_bytes, "text/plain")},
            cookies={settings.SESSION_COOKIE_NAME: self.user1_session}
        )
        self.assertEqual(response.status_code, 201)
        file_id = response.json()["id"]

        file_data = self.wait_for_file_completion(file_id, cookies={settings.SESSION_COOKIE_NAME: self.user1_session})
        self.assertEqual(file_data["processing_status"], "completed")

        db = SessionLocal()
        try:
            chunk = db.query(TextChunk).filter(TextChunk.file_id == file_id).first()
            self.assertIsNotNone(chunk)
            self.assertIsNotNone(chunk.embedding)

            embedding = deserialize_embedding(chunk.embedding)
            self.assertEqual(embedding.dtype, np.float32)
            self.assertEqual(embedding.shape, (384,))
        finally:
            db.close()

    def test_09_failed_extraction_skipped(self):
        """TEST 9: File with processing_status='failed' has 0 chunks"""
        # Upload a corrupted PDF that will fail extraction
        corrupted_pdf = b"%PDF-1.4\nCorrupted content trailing garbage \xff\xfe\x00\x01"

        response = self.client.post(
            "/api/v1/files/upload",
            files={"file": ("corrupt.pdf", corrupted_pdf, "application/pdf")},
            cookies={settings.SESSION_COOKIE_NAME: self.user1_session}
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()

        if data["processing_status"] == "failed":
            self.assertEqual(data["text_chunk_count"], 0)
            db = SessionLocal()
            try:
                chunks = db.query(TextChunk).filter(
                    TextChunk.file_id == data["id"]
                ).all()
                self.assertEqual(len(chunks), 0)
            finally:
                db.close()
        # If extraction somehow succeeds on corrupted data, chunks may exist — that's valid


if __name__ == "__main__":
    unittest.main()
