"""
Tests for enhancement features:
- OCR / text extraction improvements
- Search highlighting (keyword + semantic)
- File-specific search and RAG
- Visual retrieval
- Ownership security checks
"""

import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Ensure app module resolution
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestDetectVisualIntent(unittest.TestCase):
    """Tests for visual_service.detect_visual_intent"""

    def setUp(self):
        from app.services.visual_service import detect_visual_intent
        self.detect = detect_visual_intent

    def test_empty_query_returns_false(self):
        self.assertFalse(self.detect(""))
        self.assertFalse(self.detect(None))

    def test_architecture_diagram_detected(self):
        self.assertTrue(self.detect("Show the architecture diagram"))
        self.assertTrue(self.detect("display system architecture diagram"))

    def test_flow_diagram_detected(self):
        self.assertTrue(self.detect("Show the flow diagram"))

    def test_figure_with_action_detected(self):
        self.assertTrue(self.detect("show figure 1"))

    def test_plain_question_not_detected(self):
        self.assertFalse(self.detect("What is the summary of my document?"))
        self.assertFalse(self.detect("How many pages does it have?"))

    def test_chart_schema_detected(self):
        self.assertTrue(self.detect("show the database schema"))
        self.assertTrue(self.detect("display the chart"))


class TestSearchHighlighting(unittest.TestCase):
    """Tests for search_service.compute_keyword_highlights and compute_semantic_highlights"""

    def test_keyword_highlights_basic(self):
        from app.services.search_service import compute_keyword_highlights
        text = "The quick brown fox jumps over the lazy dog"
        highlights = compute_keyword_highlights(text, "fox dog")
        self.assertTrue(len(highlights) >= 2)
        # All highlights should be keyword type
        for h in highlights:
            self.assertEqual(h.type, "keyword")
            # Verify the highlighted substring matches the query term
            self.assertIn(text[h.start:h.end].lower(), ["fox", "dog"])

    def test_keyword_highlights_empty(self):
        from app.services.search_service import compute_keyword_highlights
        highlights = compute_keyword_highlights("some text", "")
        self.assertEqual(len(highlights), 0)

    def test_keyword_highlights_no_match(self):
        from app.services.search_service import compute_keyword_highlights
        highlights = compute_keyword_highlights("some text", "xyz123")
        self.assertEqual(len(highlights), 0)

    def test_keyword_highlights_case_insensitive(self):
        from app.services.search_service import compute_keyword_highlights
        text = "Python is Great"
        highlights = compute_keyword_highlights(text, "python great")
        matched_words = {text[h.start:h.end].lower() for h in highlights}
        self.assertIn("python", matched_words)
        self.assertIn("great", matched_words)


class TestRAGSchemas(unittest.TestCase):
    """Tests for updated RAG schemas"""

    def test_rag_request_with_file_id(self):
        from app.schemas.rag import RAGQuestionRequest
        req = RAGQuestionRequest(question="What is the summary?", file_id=42)
        self.assertEqual(req.file_id, 42)
        self.assertEqual(req.question, "What is the summary?")
        self.assertEqual(req.top_k, 5)  # default

    def test_rag_request_without_file_id(self):
        from app.schemas.rag import RAGQuestionRequest
        req = RAGQuestionRequest(question="What is the summary?")
        self.assertIsNone(req.file_id)

    def test_rag_response_with_visuals(self):
        from app.schemas.rag import RAGAnswerResponse, VisualItem
        visual = VisualItem(
            visual_id=1,
            file_id=10,
            original_filename="test.pdf",
            page_number=3,
            visual_type="page_render",
            caption="Architecture diagram",
            content_url="/api/v1/files/10/visuals/1",
        )
        resp = RAGAnswerResponse(
            question="Show diagram",
            answer="Here is the diagram.",
            citations=[],
            visuals=[visual],
            file_id=10,
        )
        self.assertEqual(len(resp.visuals), 1)
        self.assertEqual(resp.visuals[0].visual_type, "page_render")
        self.assertEqual(resp.file_id, 10)

    def test_rag_response_without_visuals(self):
        from app.schemas.rag import RAGAnswerResponse
        resp = RAGAnswerResponse(
            question="Summary?",
            answer="The document discusses...",
            citations=[],
        )
        self.assertIsNone(resp.visuals)
        self.assertIsNone(resp.file_id)


class TestSearchSchemas(unittest.TestCase):
    """Tests for updated search schemas"""

    def test_highlight_range_schema(self):
        from app.schemas.search import HighlightRange
        hr = HighlightRange(start=10, end=20, type="keyword")
        self.assertEqual(hr.start, 10)
        self.assertEqual(hr.end, 20)
        self.assertEqual(hr.type, "keyword")

    def test_semantic_search_request_with_file_id(self):
        from app.schemas.search import SemanticSearchRequest
        req = SemanticSearchRequest(query="financial growth", file_id=5)
        self.assertEqual(req.file_id, 5)

    def test_hybrid_search_request_with_file_id(self):
        from app.schemas.search import HybridSearchRequest
        req = HybridSearchRequest(query="revenue report", file_id=99)
        self.assertEqual(req.file_id, 99)

    def test_search_result_item_with_highlights(self):
        from app.schemas.search import SearchResultItem, HighlightRange
        item = SearchResultItem(
            chunk_id=1,
            chunk_index=0,
            chunk_text="The quick brown fox",
            file_id=1,
            original_filename="test.txt",
            similarity_score=0.85,
            highlight_ranges=[
                HighlightRange(start=4, end=9, type="keyword"),
                HighlightRange(start=16, end=19, type="semantic"),
            ],
        )
        self.assertEqual(len(item.highlight_ranges), 2)
        self.assertEqual(item.highlight_ranges[0].type, "keyword")
        self.assertEqual(item.highlight_ranges[1].type, "semantic")


class TestDocumentVisualModel(unittest.TestCase):
    """Tests for DocumentVisual model structure"""

    def test_model_has_required_columns(self):
        from app.models.document_visual import DocumentVisual
        # Check that the model has the expected column names
        mapper = DocumentVisual.__table__
        column_names = {c.name for c in mapper.columns}
        expected = {"id", "file_id", "visual_index", "page_number", "visual_type",
                     "storage_path", "mime_type", "caption", "context_text", "created_at"}
        self.assertTrue(expected.issubset(column_names),
                       f"Missing columns: {expected - column_names}")


class TestVisualItemSchema(unittest.TestCase):
    """Tests for VisualItem schema"""

    def test_visual_item_creation(self):
        from app.schemas.rag import VisualItem
        vi = VisualItem(
            visual_id=5,
            file_id=10,
            original_filename="doc.pdf",
            page_number=2,
            visual_type="embedded_image",
            caption="Figure 1",
            content_url="/api/v1/files/10/visuals/5",
        )
        self.assertEqual(vi.visual_id, 5)
        self.assertEqual(vi.content_url, "/api/v1/files/10/visuals/5")

    def test_visual_item_optional_fields(self):
        from app.schemas.rag import VisualItem
        vi = VisualItem(
            visual_id=1,
            file_id=1,
            original_filename="img.png",
            visual_type="uploaded_image",
            content_url="/api/v1/files/1/visuals/1",
        )
        self.assertIsNone(vi.page_number)
        self.assertIsNone(vi.caption)


if __name__ == "__main__":
    unittest.main()
