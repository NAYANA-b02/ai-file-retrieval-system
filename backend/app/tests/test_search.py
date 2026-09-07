import io
import unittest
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.core.database import SessionLocal
from app.models.user import User
from app.models.audit_log import AuditLog


class TestPhase6SemanticSearch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.user1_username = "search_user1"
        cls.user1_email = "search_user1@example.com"
        cls.user1_password = "Password123!"

        cls.user2_username = "search_user2"
        cls.user2_email = "search_user2@example.com"
        cls.user2_password = "Password123!"

    def setUp(self):
        db = SessionLocal()
        try:
            users = db.query(User).filter(
                (User.username.like("search_%")) |
                (User.email.like("search_%"))
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
                (User.username.like("search_%")) |
                (User.email.like("search_%"))
            ).all()
            for u in users:
                db.delete(u)
            db.commit()
        finally:
            db.close()

    def _upload_file(self, session_id: str, filename: str, content: str, content_type: str = "text/plain"):
        return self.client.post(
            "/api/v1/files/upload",
            files={"file": (filename, io.BytesIO(content.encode("utf-8")), content_type)},
            cookies={settings.SESSION_COOKIE_NAME: session_id},
        )

    def test_01_authenticated_semantic_search_post(self):
        """POST /api/v1/search/semantic returns valid schema with results."""
        self._upload_file(
            self.user1_session,
            "ml_overview.txt",
            "Machine learning algorithms build a mathematical model based on training sample data "
            "in order to make predictions or decisions without being explicitly programmed.",
        )

        res = self.client.post(
            "/api/v1/search/semantic",
            json={"query": "artificial intelligence training models", "top_k": 5},
            cookies={settings.SESSION_COOKIE_NAME: self.user1_session},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["query"], "artificial intelligence training models")
        self.assertGreaterEqual(data["total_results"], 1)
        self.assertIsInstance(data["results"], list)

        first = data["results"][0]
        self.assertIn("chunk_id", first)
        self.assertIn("chunk_index", first)
        self.assertIn("chunk_text", first)
        self.assertIn("file_id", first)
        self.assertEqual(first["original_filename"], "ml_overview.txt")
        self.assertIn("similarity_score", first)
        self.assertIsInstance(first["similarity_score"], float)
        self.assertEqual(first["extension"], ".txt")
        self.assertEqual(first["mime_type"], "text/plain")

    def test_02_authenticated_semantic_search_get(self):
        """GET /api/v1/search/semantic returns valid schema with query parameters."""
        self._upload_file(
            self.user1_session,
            "biology.txt",
            "Photosynthesis is a biological process used by plants to convert light energy into chemical energy.",
        )

        res = self.client.get(
            "/api/v1/search/semantic",
            params={"query": "plant solar energy conversion", "top_k": 3},
            cookies={settings.SESSION_COOKIE_NAME: self.user1_session},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["query"], "plant solar energy conversion")
        self.assertGreaterEqual(data["total_results"], 1)
        self.assertIn("Photosynthesis", data["results"][0]["chunk_text"])

    def test_03_relevance_ordering(self):
        """Semantically closer document ranks higher than an irrelevant document."""
        # Doc 1: Artificial Intelligence
        self._upload_file(
            self.user1_session,
            "deep_learning.txt",
            "Deep neural networks, backpropagation, and gradient descent optimization are core techniques in deep learning.",
        )
        # Doc 2: Baking Bread
        self._upload_file(
            self.user1_session,
            "baking.txt",
            "Sourdough bread recipe requires flour, water, salt, yeast fermentation, and high oven temperature.",
        )

        res = self.client.post(
            "/api/v1/search/semantic",
            json={"query": "neural network gradient descent", "top_k": 5},
            cookies={settings.SESSION_COOKIE_NAME: self.user1_session},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(len(data["results"]), 2)

        # First result should be the deep learning document
        top_result = data["results"][0]
        second_result = data["results"][1]
        self.assertEqual(top_result["original_filename"], "deep_learning.txt")
        self.assertEqual(second_result["original_filename"], "baking.txt")
        self.assertGreater(top_result["similarity_score"], second_result["similarity_score"])

    def test_04_top_k_parameter(self):
        """top_k restricts the number of returned chunks."""
        # Create a document with multiple chunks (over 1000 characters)
        long_content = "Artificial intelligence and computational intelligence. " * 30
        self._upload_file(self.user1_session, "long_ai.txt", long_content)

        # Request top_k=1
        res1 = self.client.post(
            "/api/v1/search/semantic",
            json={"query": "computational intelligence", "top_k": 1},
            cookies={settings.SESSION_COOKIE_NAME: self.user1_session},
        )
        self.assertEqual(res1.status_code, 200)
        self.assertEqual(len(res1.json()["results"]), 1)

        # Request top_k=2
        res2 = self.client.post(
            "/api/v1/search/semantic",
            json={"query": "computational intelligence", "top_k": 2},
            cookies={settings.SESSION_COOKIE_NAME: self.user1_session},
        )
        self.assertEqual(res2.status_code, 200)
        self.assertEqual(len(res2.json()["results"]), 2)

    def test_05_similarity_scores(self):
        """Similarity scores are properly bounded and sorted descending."""
        self._upload_file(self.user1_session, "doc1.txt", "Quantum computing uses qubits and superposition.")
        self._upload_file(self.user1_session, "doc2.txt", "Classical computing uses binary transistors 0 and 1.")

        res = self.client.post(
            "/api/v1/search/semantic",
            json={"query": "quantum superposition qubit", "top_k": 5},
            cookies={settings.SESSION_COOKIE_NAME: self.user1_session},
        )
        self.assertEqual(res.status_code, 200)
        results = res.json()["results"]
        scores = [r["similarity_score"] for r in results]

        # Verify scores are between -1.0 and 1.0
        for s in scores:
            self.assertGreaterEqual(s, -1.0)
            self.assertLessEqual(s, 1.0)

        # Verify sorted in descending order
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_06_empty_query_rejected(self):
        """Empty query string returns HTTP 400."""
        res_post = self.client.post(
            "/api/v1/search/semantic",
            json={"query": "", "top_k": 5},
            cookies={settings.SESSION_COOKIE_NAME: self.user1_session},
        )
        self.assertEqual(res_post.status_code, 400)
        self.assertIn("Query cannot be empty", res_post.json()["detail"])

        res_get = self.client.get(
            "/api/v1/search/semantic",
            params={"query": "", "top_k": 5},
            cookies={settings.SESSION_COOKIE_NAME: self.user1_session},
        )
        self.assertEqual(res_get.status_code, 400)

    def test_07_whitespace_query_rejected(self):
        """Whitespace-only query returns HTTP 400."""
        res = self.client.post(
            "/api/v1/search/semantic",
            json={"query": "   \n\t  ", "top_k": 5},
            cookies={settings.SESSION_COOKIE_NAME: self.user1_session},
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("Query cannot be empty or whitespace only", res.json()["detail"])

    def test_08_invalid_top_k_rejected(self):
        """Invalid top_k values (< 1 or > 50) return HTTP 400 or 422."""
        res_zero = self.client.post(
            "/api/v1/search/semantic",
            json={"query": "test query", "top_k": 0},
            cookies={settings.SESSION_COOKIE_NAME: self.user1_session},
        )
        self.assertIn(res_zero.status_code, [400, 422])

        res_excessive = self.client.post(
            "/api/v1/search/semantic",
            json={"query": "test query", "top_k": 100},
            cookies={settings.SESSION_COOKIE_NAME: self.user1_session},
        )
        self.assertIn(res_excessive.status_code, [400, 422])

    def test_09_ownership_isolation(self):
        """User A never receives chunks belonging to User B."""
        # User 1 uploads confidential file
        self._upload_file(
            self.user1_session,
            "confidential_payroll.txt",
            "Executive salary payroll and compensation details for leadership team.",
        )

        # User 2 uploads public gardening guide
        self._upload_file(
            self.user2_session,
            "gardening.txt",
            "Planting tomatoes and herbs in organic garden soil.",
        )

        # User 2 searches for executive payroll
        res_user2 = self.client.post(
            "/api/v1/search/semantic",
            json={"query": "executive salary payroll compensation", "top_k": 5},
            cookies={settings.SESSION_COOKIE_NAME: self.user2_session},
        )
        self.assertEqual(res_user2.status_code, 200)
        results_user2 = res_user2.json()["results"]
        # User 2 MUST NOT see confidential_payroll.txt
        filenames_user2 = [r["original_filename"] for r in results_user2]
        self.assertNotIn("confidential_payroll.txt", filenames_user2)

        # User 1 searches for executive payroll
        res_user1 = self.client.post(
            "/api/v1/search/semantic",
            json={"query": "executive salary payroll compensation", "top_k": 5},
            cookies={settings.SESSION_COOKIE_NAME: self.user1_session},
        )
        self.assertEqual(res_user1.status_code, 200)
        results_user1 = res_user1.json()["results"]
        filenames_user1 = [r["original_filename"] for r in results_user1]
        self.assertIn("confidential_payroll.txt", filenames_user1)

    def test_10_unauthenticated_rejected(self):
        """Unauthenticated requests are rejected with HTTP 401."""
        unauth_client = TestClient(app)
        res_post = unauth_client.post(
            "/api/v1/search/semantic",
            json={"query": "test query", "top_k": 5},
        )
        self.assertEqual(res_post.status_code, 401)

        res_get = unauth_client.get(
            "/api/v1/search/semantic",
            params={"query": "test query", "top_k": 5},
        )
        self.assertEqual(res_get.status_code, 401)

    def test_11_no_files_returns_empty_list(self):
        """User with no uploaded documents receives 200 OK with empty results."""
        res = self.client.post(
            "/api/v1/search/semantic",
            json={"query": "anything at all", "top_k": 5},
            cookies={settings.SESSION_COOKIE_NAME: self.user1_session},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["total_results"], 0)
        self.assertEqual(data["results"], [])

    def test_12_no_leakage_of_physical_paths(self):
        """Responses do not contain server filesystem paths."""
        self._upload_file(
            self.user1_session,
            "security_test.txt",
            "Verifying that server filesystem paths are never leaked in search results.",
        )

        res = self.client.post(
            "/api/v1/search/semantic",
            json={"query": "server security test", "top_k": 5},
            cookies={settings.SESSION_COOKIE_NAME: self.user1_session},
        )
        self.assertEqual(res.status_code, 200)
        raw_text = res.text.lower()
        self.assertNotIn("c:\\", raw_text)
        self.assertNotIn("uploads\\", raw_text)
        self.assertNotIn("app/data", raw_text)

    def test_13_audit_log_recorded(self):
        """Semantic search execution logs an entry into the audit_logs table."""
        self._upload_file(
            self.user1_session,
            "audit_doc.txt",
            "Audit logging verification text document.",
        )

        search_query = "audit logging verification"
        self.client.post(
            "/api/v1/search/semantic",
            json={"query": search_query, "top_k": 5},
            cookies={settings.SESSION_COOKIE_NAME: self.user1_session},
        )

        db = SessionLocal()
        try:
            log_entry = (
                db.query(AuditLog)
                .filter(AuditLog.action == "semantic_search", AuditLog.query == search_query)
                .first()
            )
            self.assertIsNotNone(log_entry)
            self.assertEqual(log_entry.query, search_query)
            self.assertIn("top_k=5", log_entry.details)
        finally:
            db.close()

    def test_14_search_alias_endpoint(self):
        """POST /api/v1/search also functions as semantic search alias."""
        self._upload_file(
            self.user1_session,
            "alias_test.txt",
            "Testing general search endpoint alias for semantic search.",
        )

        res = self.client.post(
            "/api/v1/search",
            json={"query": "general search endpoint", "top_k": 3},
            cookies={settings.SESSION_COOKIE_NAME: self.user1_session},
        )
        self.assertEqual(res.status_code, 200)
        self.assertGreaterEqual(res.json()["total_results"], 1)


if __name__ == "__main__":
    unittest.main()
