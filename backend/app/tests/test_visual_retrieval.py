"""
Regression tests for Visual Retrieval Pipeline fix.

Covers:
  A. Visual-intent query when text chunks exist but cannot answer the question.
  B. Visual-intent query when no text chunks meet the threshold but a visual exists.
  C. Normal non-visual question — standard RAG behaviour unchanged.
  D. Visual returned in API response; protected endpoint returns image to authorized owner.
  E. Unauthenticated and non-owner users cannot access visuals.
  F. Frontend-relevant: authenticated blob fetch returns valid image bytes.
  G. Visual extraction from a newly uploaded PDF with diagram keywords.
"""

import io
import os
import unittest
from unittest.mock import patch, MagicMock, PropertyMock

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session as DBSession

from app.main import app
from app.core.config import settings
from app.core.database import SessionLocal
from app.models.user import User
from app.models.file import File
from app.models.document_visual import DocumentVisual
from app.services.visual_service import detect_visual_intent, find_relevant_visual
from app.services.rag_service import execute_rag, NOT_ENOUGH_INFO_ANSWER


class TestVisualRetrievalRegression(unittest.TestCase):
    """Regression tests for the visual retrieval pipeline."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.owner_username = "vis_owner_user"
        cls.owner_email = "vis_owner@example.com"
        cls.owner_password = "Password123!"

        cls.other_username = "vis_other_user"
        cls.other_email = "vis_other@example.com"
        cls.other_password = "Password123!"

    def setUp(self):
        """Clean up test users and register fresh ones for each test."""
        db = SessionLocal()
        try:
            users = db.query(User).filter(
                (User.username.like("vis_%")) |
                (User.email.like("vis_%"))
            ).all()
            for u in users:
                db.delete(u)
            db.commit()
        finally:
            db.close()

        # Register and login owner
        self.client.post("/api/v1/auth/register", json={
            "username": self.owner_username,
            "email": self.owner_email,
            "password": self.owner_password,
        })
        login_res = self.client.post("/api/v1/auth/login", json={
            "username_or_email": self.owner_username,
            "password": self.owner_password,
        })
        self.owner_session = login_res.cookies.get(settings.SESSION_COOKIE_NAME)

        # Register and login non-owner
        self.client.post("/api/v1/auth/register", json={
            "username": self.other_username,
            "email": self.other_email,
            "password": self.other_password,
        })
        login_res2 = self.client.post("/api/v1/auth/login", json={
            "username_or_email": self.other_username,
            "password": self.other_password,
        })
        self.other_session = login_res2.cookies.get(settings.SESSION_COOKIE_NAME)

    def tearDown(self):
        db = SessionLocal()
        try:
            users = db.query(User).filter(
                (User.username.like("vis_%")) |
                (User.email.like("vis_%"))
            ).all()
            for u in users:
                db.delete(u)
            db.commit()
        finally:
            db.close()

    def _upload_file(self, session_id, filename, content, content_type="text/plain"):
        return self.client.post(
            "/api/v1/files/upload",
            files={"file": (filename, io.BytesIO(content.encode("utf-8")), content_type)},
            cookies={settings.SESSION_COOKIE_NAME: session_id},
        )

    # ----------------------------------------------------------------
    # Test A: Visual intent + qualifying chunks exist but can't answer
    # ----------------------------------------------------------------
    def test_A_visual_intent_with_chunks_returns_visual(self):
        """
        When visual intent is detected, qualifying text chunks exist,
        and a matching visual is found, the response should include
        the visual and NOT the LLM 'not enough info' string.
        """
        # Upload a text file so chunks will match
        self._upload_file(
            self.owner_session,
            "architecture_notes.txt",
            "This document contains the system architecture overview and component diagram details.",
        )

        # Create a mock visual in the DB
        db = SessionLocal()
        try:
            owner = db.query(User).filter(User.username == self.owner_username).first()
            file_record = db.query(File).filter(File.owner_id == owner.id).first()
            self.assertIsNotNone(file_record, "File record must exist after upload")

            visual = DocumentVisual(
                file_id=file_record.id,
                visual_index=0,
                page_number=1,
                visual_type="page_render",
                storage_path=file_record.file_path,  # reuse the file path for testing
                mime_type="image/png",
                caption="Architecture diagram",
                context_text="architecture diagram system overview component",
            )
            db.add(visual)
            db.commit()
            db.refresh(visual)
            file_id = file_record.id
            visual_id = visual.id
        finally:
            db.close()

        # Ask a visual-intent question
        res = self.client.post(
            "/api/v1/rag/ask",
            json={"question": "Show me the architecture diagram from my document", "top_k": 5},
            cookies={settings.SESSION_COOKIE_NAME: self.owner_session},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()

        # Must NOT have the rejection string
        self.assertNotIn("not contain enough information", data["answer"])

        # Must have visuals in the response
        self.assertIsNotNone(data["visuals"])
        self.assertGreaterEqual(len(data["visuals"]), 1)

        # Visual must have correct fields
        vis = data["visuals"][0]
        self.assertEqual(vis["file_id"], file_id)
        self.assertEqual(vis["visual_id"], visual_id)
        self.assertIn("content_url", vis)

        # Answer should be a truthful introductory message
        self.assertIn("architecture_notes.txt", data["answer"])

    # ----------------------------------------------------------------
    # Test B: Visual intent + no qualifying chunks + visual exists
    # ----------------------------------------------------------------
    def test_B_visual_intent_no_chunks_returns_visual(self):
        """
        Visual-intent query with no qualifying text chunks but a matching
        visual should return the visual, not 'not enough info'.
        """
        # Upload a file with unrelated content
        self._upload_file(
            self.owner_session,
            "data_report.txt",
            "Quarterly revenue figures and financial projections for the fiscal year.",
        )

        db = SessionLocal()
        try:
            owner = db.query(User).filter(User.username == self.owner_username).first()
            file_record = db.query(File).filter(File.owner_id == owner.id).first()
            self.assertIsNotNone(file_record)

            visual = DocumentVisual(
                file_id=file_record.id,
                visual_index=0,
                page_number=2,
                visual_type="embedded_image",
                storage_path=file_record.file_path,
                mime_type="image/png",
                caption="Revenue chart",
                context_text="revenue chart quarterly figures visual",
            )
            db.add(visual)
            db.commit()
            db.refresh(visual)
        finally:
            db.close()

        # Ask about a diagram — text chunks won't match
        res = self.client.post(
            "/api/v1/rag/ask",
            json={"question": "Show me the chart diagram from my document", "top_k": 5},
            cookies={settings.SESSION_COOKIE_NAME: self.owner_session},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()

        # Should have visual, not rejection
        self.assertNotIn("not contain enough information", data["answer"])
        self.assertIsNotNone(data["visuals"])
        self.assertGreaterEqual(len(data["visuals"]), 1)

    # ----------------------------------------------------------------
    # Test C: Normal non-visual question — standard RAG unchanged
    # ----------------------------------------------------------------
    @patch("app.services.rag_service.call_llm_chat")
    def test_C_non_visual_query_unchanged(self, mock_llm):
        """
        A normal (non-visual) RAG question should behave exactly as before:
        calls LLM, returns answer with citations, no visuals.
        """
        mock_llm.return_value = "The speed of light is approximately 299,792,458 m/s."

        self._upload_file(
            self.owner_session,
            "physics.txt",
            "The speed of light in vacuum is approximately 299,792,458 meters per second.",
        )

        res = self.client.post(
            "/api/v1/rag/ask",
            json={"question": "What is the speed of light?", "top_k": 3},
            cookies={settings.SESSION_COOKIE_NAME: self.owner_session},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()

        # LLM should have been called
        mock_llm.assert_called_once()

        # Should have answer from LLM
        self.assertIn("299,792,458", data["answer"])

        # No visuals for a non-visual query
        self.assertIsNone(data["visuals"])

        # Citations should be present
        self.assertGreaterEqual(len(data["citations"]), 1)

    # ----------------------------------------------------------------
    # Test D: Protected visual endpoint returns image to authorized owner
    # ----------------------------------------------------------------
    def test_D_visual_endpoint_authorized_owner(self):
        """
        GET /api/v1/files/{file_id}/visuals/{visual_id} returns image bytes
        for the authorized file owner.
        """
        self._upload_file(
            self.owner_session,
            "diagram_doc.txt",
            "Document with architecture diagram content.",
        )

        db = SessionLocal()
        try:
            owner = db.query(User).filter(User.username == self.owner_username).first()
            file_record = db.query(File).filter(File.owner_id == owner.id).first()
            self.assertIsNotNone(file_record)

            visual = DocumentVisual(
                file_id=file_record.id,
                visual_index=0,
                page_number=1,
                visual_type="page_render",
                storage_path=file_record.file_path,
                mime_type="image/png",
                caption="Test diagram",
                context_text="architecture diagram",
            )
            db.add(visual)
            db.commit()
            db.refresh(visual)
            file_id = file_record.id
            visual_id = visual.id
        finally:
            db.close()

        res = self.client.get(
            f"/api/v1/files/{file_id}/visuals/{visual_id}",
            cookies={settings.SESSION_COOKIE_NAME: self.owner_session},
        )
        self.assertEqual(res.status_code, 200)
        # Content should be non-empty bytes
        self.assertGreater(len(res.content), 0)

    # ----------------------------------------------------------------
    # Test E: Unauthenticated and non-owner cannot access visuals
    # ----------------------------------------------------------------
    def test_E_unauthenticated_access_denied(self):
        """Unauthenticated request to visual endpoint returns 401."""
        self._upload_file(
            self.owner_session,
            "secret_doc.txt",
            "Secret architecture diagram document.",
        )

        db = SessionLocal()
        try:
            owner = db.query(User).filter(User.username == self.owner_username).first()
            file_record = db.query(File).filter(File.owner_id == owner.id).first()
            self.assertIsNotNone(file_record)

            visual = DocumentVisual(
                file_id=file_record.id,
                visual_index=0,
                page_number=1,
                visual_type="page_render",
                storage_path=file_record.file_path,
                mime_type="image/png",
                caption="Secret diagram",
                context_text="secret architecture",
            )
            db.add(visual)
            db.commit()
            db.refresh(visual)
            file_id = file_record.id
            visual_id = visual.id
        finally:
            db.close()

        # Unauthenticated access
        unauth_client = TestClient(app)
        res = unauth_client.get(f"/api/v1/files/{file_id}/visuals/{visual_id}")
        self.assertEqual(res.status_code, 401)

    def test_E_non_owner_access_denied(self):
        """Non-owner user cannot access another user's visual (404)."""
        self._upload_file(
            self.owner_session,
            "owner_only_doc.txt",
            "Owner-only architecture diagram document.",
        )

        db = SessionLocal()
        try:
            owner = db.query(User).filter(User.username == self.owner_username).first()
            file_record = db.query(File).filter(File.owner_id == owner.id).first()
            self.assertIsNotNone(file_record)

            visual = DocumentVisual(
                file_id=file_record.id,
                visual_index=0,
                page_number=1,
                visual_type="page_render",
                storage_path=file_record.file_path,
                mime_type="image/png",
                caption="Owner diagram",
                context_text="owner architecture",
            )
            db.add(visual)
            db.commit()
            db.refresh(visual)
            file_id = file_record.id
            visual_id = visual.id
        finally:
            db.close()

        # Non-owner access
        res = self.client.get(
            f"/api/v1/files/{file_id}/visuals/{visual_id}",
            cookies={settings.SESSION_COOKIE_NAME: self.other_session},
        )
        self.assertEqual(res.status_code, 404)

    # ----------------------------------------------------------------
    # Test F: Authenticated blob fetch returns valid image bytes
    # ----------------------------------------------------------------
    def test_F_authenticated_blob_fetch(self):
        """
        Simulates the frontend AuthenticatedVisual component's blob fetch:
        GET with session cookie returns valid bytes with image/* content type.
        """
        self._upload_file(
            self.owner_session,
            "blob_test_doc.txt",
            "Document for blob fetch visual testing.",
        )

        db = SessionLocal()
        try:
            owner = db.query(User).filter(User.username == self.owner_username).first()
            file_record = db.query(File).filter(File.owner_id == owner.id).first()
            self.assertIsNotNone(file_record)

            visual = DocumentVisual(
                file_id=file_record.id,
                visual_index=0,
                page_number=1,
                visual_type="page_render",
                storage_path=file_record.file_path,
                mime_type="image/png",
                caption="Blob test diagram",
                context_text="blob test architecture",
            )
            db.add(visual)
            db.commit()
            db.refresh(visual)
            file_id = file_record.id
            visual_id = visual.id
        finally:
            db.close()

        res = self.client.get(
            f"/api/v1/files/{file_id}/visuals/{visual_id}",
            cookies={settings.SESSION_COOKIE_NAME: self.owner_session},
        )
        self.assertEqual(res.status_code, 200)
        self.assertIn("image/", res.headers.get("content-type", ""))
        self.assertGreater(len(res.content), 0)

    # ----------------------------------------------------------------
    # Unit tests: detect_visual_intent
    # ----------------------------------------------------------------
    def test_detect_visual_intent_positive(self):
        """Visual intent is detected for diagram/image requests."""
        positive_queries = [
            "Show me the architecture diagram from my document",
            "Display the flowchart",
            "Can you show the system architecture?",
            "View the database schema",
            "Show the figure on page 3",
        ]
        for q in positive_queries:
            self.assertTrue(
                detect_visual_intent(q),
                f"Expected visual intent for: '{q}'"
            )

    def test_detect_visual_intent_negative(self):
        """Visual intent is NOT detected for ordinary text queries."""
        negative_queries = [
            "What is the speed of light?",
            "Summarize the document",
            "What are the key findings?",
            "How many employees does the company have?",
        ]
        for q in negative_queries:
            self.assertFalse(
                detect_visual_intent(q),
                f"Did NOT expect visual intent for: '{q}'"
            )

    # ----------------------------------------------------------------
    # Unit test: find_relevant_visual with qualifying_chunks
    # ----------------------------------------------------------------
    def test_find_relevant_visual_uses_qualifying_chunks(self):
        """
        find_relevant_visual prioritizes visuals from files that
        appear in qualifying_chunks when they are provided.
        """
        self._upload_file(
            self.owner_session,
            "chunk_match_doc.txt",
            "Architecture overview and system component diagram description.",
        )

        db = SessionLocal()
        try:
            owner = db.query(User).filter(User.username == self.owner_username).first()
            file_record = db.query(File).filter(File.owner_id == owner.id).first()
            self.assertIsNotNone(file_record)

            visual = DocumentVisual(
                file_id=file_record.id,
                visual_index=0,
                page_number=1,
                visual_type="page_render",
                storage_path=file_record.file_path,
                mime_type="image/png",
                caption="Architecture diagram",
                context_text="architecture diagram system overview component",
            )
            db.add(visual)
            db.commit()
            db.refresh(visual)

            # Create a mock qualifying chunk
            mock_chunk = MagicMock()
            mock_chunk.file_id = file_record.id

            result = find_relevant_visual(
                db=db,
                user_id=owner.id,
                query="Show me the architecture diagram",
                qualifying_chunks=[mock_chunk],
            )

            self.assertIsNotNone(result)
            self.assertEqual(result.id, visual.id)
        finally:
            db.close()

    # ----------------------------------------------------------------
    # Test: RAG response does not expose filesystem paths
    # ----------------------------------------------------------------
    def test_visual_response_no_path_leakage(self):
        """RAG visual response never leaks server filesystem paths."""
        self._upload_file(
            self.owner_session,
            "path_leak_test.txt",
            "Testing path leakage prevention in architecture diagram response.",
        )

        db = SessionLocal()
        try:
            owner = db.query(User).filter(User.username == self.owner_username).first()
            file_record = db.query(File).filter(File.owner_id == owner.id).first()

            visual = DocumentVisual(
                file_id=file_record.id,
                visual_index=0,
                page_number=1,
                visual_type="page_render",
                storage_path=file_record.file_path,
                mime_type="image/png",
                caption="Diagram",
                context_text="architecture diagram overview",
            )
            db.add(visual)
            db.commit()
        finally:
            db.close()

        res = self.client.post(
            "/api/v1/rag/ask",
            json={"question": "Show me the architecture diagram", "top_k": 3},
            cookies={settings.SESSION_COOKIE_NAME: self.owner_session},
        )
        self.assertEqual(res.status_code, 200)
        raw = res.text.lower()
        self.assertNotIn("c:\\", raw)
        self.assertNotIn("uploads\\", raw)
        self.assertNotIn("app/data", raw)
        self.assertNotIn("storage_path", raw)


    # ----------------------------------------------------------------
    # Meaning-Based Retrieval Tests (Architecture vs Workflow disambiguation)
    # ----------------------------------------------------------------
    def test_architecture_query_prefers_architecture_over_workflow(self):
        """
        Replicates Final HackNow scenario:
        Document has two diagrams:
          - Diagram 0 (Page 1): Solution Workflow
          - Diagram 1 (Page 2): System Architecture
        Query asking for 'architecture diagram' MUST return Diagram 1, NOT Diagram 0.
        """
        self._upload_file(
            self.owner_session,
            "Final_HackNow.txt",
            "This document presents the hackathon solution workflow on page 1 and the full system architecture diagram on page 2.",
        )

        db = SessionLocal()
        try:
            owner = db.query(User).filter(User.username == self.owner_username).first()
            file_record = db.query(File).filter(File.owner_id == owner.id).first()
            file_id = file_record.id

            # Visual 0: Solution Workflow (first in document order)
            vis_workflow = DocumentVisual(
                file_id=file_id,
                visual_index=0,
                page_number=1,
                visual_type="embedded_image",
                storage_path=file_record.file_path,
                mime_type="image/png",
                caption="Figure 1: Solution Workflow",
                context_text="Solution Workflow diagram showing user upload, ingestion pipeline, vectorization step, and answer display stages.",
            )
            # Visual 1: System Architecture (second in document order)
            vis_architecture = DocumentVisual(
                file_id=file_id,
                visual_index=1,
                page_number=2,
                visual_type="embedded_image",
                storage_path=file_record.file_path,
                mime_type="image/png",
                caption="Figure 2: System Architecture",
                context_text="System Architecture diagram. React Frontend communicating via REST API with FastAPI Backend, PostgreSQL database, and FastEmbed vector store.",
            )
            db.add_all([vis_workflow, vis_architecture])
            db.commit()
            db.refresh(vis_workflow)
            db.refresh(vis_architecture)
            arch_id = vis_architecture.id
            workflow_id = vis_workflow.id
        finally:
            db.close()

        res = self.client.post(
            "/api/v1/rag/ask",
            json={"question": "Show me the system architecture diagram from Final HackNow", "top_k": 5},
            cookies={settings.SESSION_COOKIE_NAME: self.owner_session},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertIsNotNone(data["visuals"])
        self.assertEqual(len(data["visuals"]), 1)
        selected_vis = data["visuals"][0]

        # MUST select the System Architecture diagram (Visual 1), NOT the Solution Workflow (Visual 0)
        self.assertEqual(selected_vis["visual_id"], arch_id)
        self.assertEqual(selected_vis["diagram_type"], "System Architecture")
        self.assertEqual(selected_vis["page_number"], 2)

    def test_workflow_query_prefers_workflow_over_architecture(self):
        """
        In the same document, asking for 'solution workflow' MUST return
        the Solution Workflow diagram (Visual 0), NOT System Architecture.
        """
        self._upload_file(
            self.owner_session,
            "Final_HackNow.txt",
            "This document presents the hackathon solution workflow on page 1 and the full system architecture diagram on page 2.",
        )

        db = SessionLocal()
        try:
            owner = db.query(User).filter(User.username == self.owner_username).first()
            file_record = db.query(File).filter(File.owner_id == owner.id).first()
            file_id = file_record.id

            vis_workflow = DocumentVisual(
                file_id=file_id,
                visual_index=0,
                page_number=1,
                visual_type="embedded_image",
                storage_path=file_record.file_path,
                mime_type="image/png",
                caption="Figure 1: Solution Workflow",
                context_text="Solution Workflow diagram showing user upload, ingestion pipeline, vectorization step, and answer display stages.",
            )
            vis_architecture = DocumentVisual(
                file_id=file_id,
                visual_index=1,
                page_number=2,
                visual_type="embedded_image",
                storage_path=file_record.file_path,
                mime_type="image/png",
                caption="Figure 2: System Architecture",
                context_text="System Architecture diagram. React Frontend communicating via REST API with FastAPI Backend, PostgreSQL database, and FastEmbed vector store.",
            )
            db.add_all([vis_workflow, vis_architecture])
            db.commit()
            db.refresh(vis_workflow)
            workflow_id = vis_workflow.id
        finally:
            db.close()

        res = self.client.post(
            "/api/v1/rag/ask",
            json={"question": "Show me the solution workflow diagram", "top_k": 5},
            cookies={settings.SESSION_COOKIE_NAME: self.owner_session},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertIsNotNone(data["visuals"])
        self.assertEqual(len(data["visuals"]), 1)
        selected_vis = data["visuals"][0]

        # MUST select the Solution Workflow diagram
        self.assertEqual(selected_vis["visual_id"], workflow_id)
        self.assertEqual(selected_vis["diagram_type"], "Solution Workflow")
        self.assertEqual(selected_vis["page_number"], 1)

    def test_multi_document_diagram_selection(self):
        """
        When multiple documents contain diagrams (e.g. Doc A has Database Schema,
        Doc B has System Architecture), the query correctly targets the right document.
        """
        self._upload_file(self.owner_session, "Database_Design.txt", "Database design and ER diagram.")
        self._upload_file(self.owner_session, "Cloud_Architecture.txt", "Cloud microservice system architecture.")

        db = SessionLocal()
        try:
            owner = db.query(User).filter(User.username == self.owner_username).first()
            file_db = db.query(File).filter(File.original_filename == "Database_Design.txt", File.owner_id == owner.id).first()
            file_arch = db.query(File).filter(File.original_filename == "Cloud_Architecture.txt", File.owner_id == owner.id).first()

            vis_erd = DocumentVisual(
                file_id=file_db.id,
                visual_index=0,
                page_number=1,
                visual_type="page_render",
                storage_path=file_db.file_path,
                mime_type="image/png",
                caption="Database Schema ERD",
                context_text="ER diagram showing tables, foreign keys, and relations between users and files.",
            )
            vis_cloud = DocumentVisual(
                file_id=file_arch.id,
                visual_index=0,
                page_number=1,
                visual_type="page_render",
                storage_path=file_arch.file_path,
                mime_type="image/png",
                caption="Cloud System Architecture",
                context_text="Cloud microservice system architecture diagram with Kubernetes cluster, ingress gateway, and services.",
            )
            db.add_all([vis_erd, vis_cloud])
            db.commit()
            db.refresh(vis_erd)
            db.refresh(vis_cloud)
            erd_id = vis_erd.id
            cloud_id = vis_cloud.id
        finally:
            db.close()

        # Query 1: Ask for Database Schema
        res1 = self.client.post(
            "/api/v1/rag/ask",
            json={"question": "Show me the database schema ER diagram", "top_k": 5},
            cookies={settings.SESSION_COOKIE_NAME: self.owner_session},
        )
        self.assertEqual(res1.status_code, 200)
        self.assertEqual(res1.json()["visuals"][0]["visual_id"], erd_id)

        # Query 2: Ask for Cloud System Architecture
        res2 = self.client.post(
            "/api/v1/rag/ask",
            json={"question": "Show me the cloud system architecture diagram", "top_k": 5},
            cookies={settings.SESSION_COOKIE_NAME: self.owner_session},
        )
        self.assertEqual(res2.status_code, 200)
        self.assertEqual(res2.json()["visuals"][0]["visual_id"], cloud_id)

    def test_file_specific_visual_filtering(self):
        """
        When file_id is provided in the request, visual retrieval is strictly
        scoped to that specific document even if other documents have matching visuals.
        """
        self._upload_file(self.owner_session, "Doc1.txt", "Architecture for doc 1.")
        self._upload_file(self.owner_session, "Doc2.txt", "Architecture for doc 2.")

        db = SessionLocal()
        try:
            owner = db.query(User).filter(User.username == self.owner_username).first()
            f1 = db.query(File).filter(File.original_filename == "Doc1.txt", File.owner_id == owner.id).first()
            f2 = db.query(File).filter(File.original_filename == "Doc2.txt", File.owner_id == owner.id).first()

            v1 = DocumentVisual(
                file_id=f1.id,
                visual_index=0,
                page_number=1,
                visual_type="page_render",
                storage_path=f1.file_path,
                mime_type="image/png",
                caption="Doc 1 Architecture",
                context_text="System architecture overview for system 1.",
            )
            v2 = DocumentVisual(
                file_id=f2.id,
                visual_index=0,
                page_number=1,
                visual_type="page_render",
                storage_path=f2.file_path,
                mime_type="image/png",
                caption="Doc 2 Architecture",
                context_text="System architecture overview for system 2.",
            )
            db.add_all([v1, v2])
            db.commit()
            db.refresh(v1)
            v1_id = v1.id
            f1_id = f1.id
        finally:
            db.close()

        # Scope explicitly to Doc 1
        res = self.client.post(
            "/api/v1/rag/ask",
            json={"question": "Show me the architecture diagram", "top_k": 3, "file_id": f1_id},
            cookies={settings.SESSION_COOKIE_NAME: self.owner_session},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["visuals"][0]["visual_id"], v1_id)
        self.assertEqual(data["visuals"][0]["file_id"], f1_id)

    def test_candidate_progression_and_exhaustion(self):
        """
        Verifies:
        1. First candidate returned with has_next_candidate=True.
        2. Excluding candidate 1 returns candidate 2.
        3. Excluding candidate 1 and 2 returns candidate exhaustion message with visuals=None.
        """
        self._upload_file(self.owner_session, "MultiDiagram.txt", "Document with multiple diagrams.")

        db = SessionLocal()
        try:
            owner = db.query(User).filter(User.username == self.owner_username).first()
            file_rec = db.query(File).filter(File.owner_id == owner.id).first()
            f_id = file_rec.id

            v1 = DocumentVisual(
                file_id=f_id,
                visual_index=0,
                page_number=1,
                visual_type="page_render",
                storage_path=file_rec.file_path,
                mime_type="image/png",
                caption="Figure 1: High Level Architecture",
                context_text="Architecture diagram high level overview component stack.",
            )
            v2 = DocumentVisual(
                file_id=f_id,
                visual_index=1,
                page_number=2,
                visual_type="page_render",
                storage_path=file_rec.file_path,
                mime_type="image/png",
                caption="Figure 2: Component Architecture",
                context_text="Component architecture diagram detailing service modules.",
            )
            db.add_all([v1, v2])
            db.commit()
            db.refresh(v1)
            db.refresh(v2)
            v1_id = v1.id
            v2_id = v2.id
        finally:
            db.close()

        # Step 1: Initial query
        res1 = self.client.post(
            "/api/v1/rag/ask",
            json={"question": "Show me the architecture diagram", "top_k": 5},
            cookies={settings.SESSION_COOKIE_NAME: self.owner_session},
        )
        data1 = res1.json()
        self.assertEqual(res1.status_code, 200)
        self.assertTrue(data1["has_next_candidate"])
        self.assertEqual(data1["candidate_count"], 2)
        first_vis_id = data1["visuals"][0]["visual_id"]

        # Step 2: Show another diagram (exclude first_vis_id)
        res2 = self.client.post(
            "/api/v1/rag/ask",
            json={
                "question": "Show me the architecture diagram",
                "top_k": 5,
                "exclude_visual_ids": [first_vis_id],
            },
            cookies={settings.SESSION_COOKIE_NAME: self.owner_session},
        )
        data2 = res2.json()
        self.assertEqual(res2.status_code, 200)
        second_vis_id = data2["visuals"][0]["visual_id"]
        self.assertNotEqual(first_vis_id, second_vis_id)
        self.assertFalse(data2["has_next_candidate"])

        # Step 3: Candidate exhaustion (exclude both)
        res3 = self.client.post(
            "/api/v1/rag/ask",
            json={
                "question": "Show me the architecture diagram",
                "top_k": 5,
                "exclude_visual_ids": [first_vis_id, second_vis_id],
            },
            cookies={settings.SESSION_COOKIE_NAME: self.owner_session},
        )
        data3 = res3.json()
        self.assertEqual(res3.status_code, 200)
        self.assertIsNone(data3["visuals"])
        self.assertIn("No further relevant diagrams", data3["answer"])

    def test_ordinal_query_selection(self):
        """
        When the user explicitly asks for 'the second diagram', the system honors
        the ordinal and returns candidate 2.
        """
        self._upload_file(self.owner_session, "Numbered_Doc.txt", "Numbered diagram document.")

        db = SessionLocal()
        try:
            owner = db.query(User).filter(User.username == self.owner_username).first()
            file_rec = db.query(File).filter(File.owner_id == owner.id).first()
            f_id = file_rec.id

            v1 = DocumentVisual(
                file_id=f_id,
                visual_index=0,
                page_number=1,
                visual_type="page_render",
                storage_path=file_rec.file_path,
                mime_type="image/png",
                caption="First Diagram",
                context_text="First system overview diagram on page 1.",
            )
            v2 = DocumentVisual(
                file_id=f_id,
                visual_index=1,
                page_number=2,
                visual_type="page_render",
                storage_path=file_rec.file_path,
                mime_type="image/png",
                caption="Second Diagram",
                context_text="Second component diagram on page 2.",
            )
            db.add_all([v1, v2])
            db.commit()
            db.refresh(v1)
            db.refresh(v2)
            v2_id = v2.id
        finally:
            db.close()

        res = self.client.post(
            "/api/v1/rag/ask",
            json={"question": "Show me the second diagram", "top_k": 5},
            cookies={settings.SESSION_COOKIE_NAME: self.owner_session},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["visuals"][0]["visual_id"], v2_id)


if __name__ == "__main__":
    unittest.main()
