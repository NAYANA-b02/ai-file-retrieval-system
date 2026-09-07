import io
import unittest
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.core.database import SessionLocal
from app.models.user import User
from app.models.audit_log import AuditLog


class TestPhase7HybridSearch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.user1_username = "hybrid_user1"
        cls.user1_email = "hybrid_user1@example.com"
        cls.user1_password = "Password123!"

        cls.user2_username = "hybrid_user2"
        cls.user2_email = "hybrid_user2@example.com"
        cls.user2_password = "Password123!"

    def setUp(self):
        db = SessionLocal()
        try:
            users = db.query(User).filter(
                (User.username.like("hybrid_%")) |
                (User.email.like("hybrid_%"))
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
                (User.username.like("hybrid_%")) |
                (User.email.like("hybrid_%"))
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

    def test_01_keyword_search_post(self):
        """POST /api/v1/search/keyword returns valid schema with keyword results."""
        self._upload_file(
            self.user1_session,
            "database.txt",
            "PostgreSQL full text search utilizes GIN indexes and tsvector to parse and rank documents efficiently.",
        )

        res = self.client.post(
            "/api/v1/search/keyword",
            json={"query": "PostgreSQL GIN indexes", "top_k": 5},
            cookies={settings.SESSION_COOKIE_NAME: self.user1_session},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["query"], "PostgreSQL GIN indexes")
        self.assertEqual(data["search_mode"], "keyword")
        self.assertGreaterEqual(data["total_results"], 1)

        first = data["results"][0]
        self.assertIn("chunk_id", first)
        self.assertIn("chunk_index", first)
        self.assertIn("chunk_text", first)
        self.assertEqual(first["original_filename"], "database.txt")
        self.assertIsNotNone(first["keyword_score"])
        self.assertGreater(first["keyword_score"], 0.0)

    def test_02_keyword_search_get(self):
        """GET /api/v1/search/keyword returns valid schema with query params."""
        self._upload_file(
            self.user1_session,
            "vision.txt",
            "Convolutional neural networks are specifically tailored for digital image processing and classification.",
        )

        res = self.client.get(
            "/api/v1/search/keyword",
            params={"query": "convolutional image classification", "top_k": 3},
            cookies={settings.SESSION_COOKIE_NAME: self.user1_session},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["search_mode"], "keyword")
        self.assertGreaterEqual(data["total_results"], 1)
        self.assertIn("Convolutional", data["results"][0]["chunk_text"])

    def test_03_exact_keyword_matching(self):
        """Exact token match surfaces the exact document even among semantically related ones."""
        # Doc 1: Has exact configuration token
        self._upload_file(
            self.user1_session,
            "config_code.txt",
            "System error occurred with status code ERROR_TOKEN_XYZ_9912 during database write.",
        )
        # Doc 2: General error discussion
        self._upload_file(
            self.user1_session,
            "general_error.txt",
            "General error troubleshooting guide for system administration and write failures.",
        )

        res = self.client.post(
            "/api/v1/search/keyword",
            json={"query": "ERROR_TOKEN_XYZ_9912", "top_k": 5},
            cookies={settings.SESSION_COOKIE_NAME: self.user1_session},
        )
        self.assertEqual(res.status_code, 200)
        results = res.json()["results"]
        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(results[0]["original_filename"], "config_code.txt")

    def test_04_hybrid_search_post(self):
        """POST /api/v1/search/hybrid returns combined score and mode."""
        self._upload_file(
            self.user1_session,
            "physics.txt",
            "Thermodynamics principles describe the relationships between heat, work, temperature, and energy.",
        )

        res = self.client.post(
            "/api/v1/search/hybrid",
            json={"query": "thermodynamics heat temperature energy", "top_k": 5},
            cookies={settings.SESSION_COOKIE_NAME: self.user1_session},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["search_mode"], "hybrid")
        self.assertEqual(data["keyword_weight"], 0.4)
        self.assertEqual(data["semantic_weight"], 0.6)
        self.assertGreaterEqual(data["total_results"], 1)

        first = data["results"][0]
        self.assertIsNotNone(first["similarity_score"])
        self.assertIsNotNone(first["semantic_score"])
        self.assertIsNotNone(first["keyword_score"])

    def test_05_hybrid_search_get(self):
        """GET /api/v1/search/hybrid returns valid response with query parameters."""
        self._upload_file(
            self.user1_session,
            "ocean.txt",
            "Marine biology explores organisms that inhabit salt water ecosystems and coral reefs.",
        )

        res = self.client.get(
            "/api/v1/search/hybrid",
            params={"query": "marine biology coral reefs", "top_k": 3},
            cookies={settings.SESSION_COOKIE_NAME: self.user1_session},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["search_mode"], "hybrid")
        self.assertGreaterEqual(data["total_results"], 1)

    def test_06_hybrid_relevance_combination(self):
        """Document matching both keyword and semantic aspects outranks document matching only one."""
        # Doc 1: Matches both exact keywords AND semantic topic
        self._upload_file(
            self.user1_session,
            "solar_cells.txt",
            "Photovoltaic solar cells convert solar sunlight radiation into electricity using silicon semiconductors.",
        )
        # Doc 2: Matches general renewable energy topic (semantic match, low keyword match)
        self._upload_file(
            self.user1_session,
            "wind_turbines.txt",
            "Wind turbines harness kinetic atmospheric wind energy to generate clean electrical power.",
        )
        # Doc 3: Totally irrelevant
        self._upload_file(
            self.user1_session,
            "pasta.txt",
            "Traditional Italian pasta preparation with semolina flour and boiling salted water.",
        )

        res = self.client.post(
            "/api/v1/search/hybrid",
            json={"query": "photovoltaic solar sunlight silicon", "top_k": 5},
            cookies={settings.SESSION_COOKIE_NAME: self.user1_session},
        )
        self.assertEqual(res.status_code, 200)
        results = res.json()["results"]
        self.assertGreaterEqual(len(results), 2)
        # Doc 1 must be #1
        self.assertEqual(results[0]["original_filename"], "solar_cells.txt")
        self.assertGreater(results[0]["similarity_score"], results[1]["similarity_score"])

    def test_07_custom_weights_configuration(self):
        """Custom keyword_weight and semantic_weight are correctly applied and normalized."""
        self._upload_file(
            self.user1_session,
            "weights_doc.txt",
            "Testing custom weights configuration in hybrid search ranking formula.",
        )

        res = self.client.post(
            "/api/v1/search/hybrid",
            json={
                "query": "weights configuration",
                "top_k": 5,
                "keyword_weight": 0.8,
                "semantic_weight": 0.2,
            },
            cookies={settings.SESSION_COOKIE_NAME: self.user1_session},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["keyword_weight"], 0.8)
        self.assertEqual(data["semantic_weight"], 0.2)

    def test_08_semantic_only_fallback(self):
        """When keywords do not match directly, semantic component still scores and retrieves document."""
        self._upload_file(
            self.user1_session,
            "autonomous_cars.txt",
            "Motor vehicles capable of sensing surrounding environment and driving safely without human intervention.",
        )

        # Query uses synonyms: 'self-driving automobiles'
        res = self.client.post(
            "/api/v1/search/hybrid",
            json={"query": "self driving automobiles transit", "top_k": 5},
            cookies={settings.SESSION_COOKIE_NAME: self.user1_session},
        )
        self.assertEqual(res.status_code, 200)
        results = res.json()["results"]
        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(results[0]["original_filename"], "autonomous_cars.txt")
        self.assertGreater(results[0]["semantic_score"], 0.0)

    def test_09_keyword_only_fallback(self):
        """Specific unique identifier keyword match boosts document in hybrid search."""
        self._upload_file(
            self.user1_session,
            "unique_id_doc.txt",
            "System patch release notes for PATCH_IDENTIFIER_ALPHA_9942 deployment.",
        )

        res = self.client.post(
            "/api/v1/search/hybrid",
            json={"query": "PATCH_IDENTIFIER_ALPHA_9942", "top_k": 5},
            cookies={settings.SESSION_COOKIE_NAME: self.user1_session},
        )
        self.assertEqual(res.status_code, 200)
        results = res.json()["results"]
        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(results[0]["original_filename"], "unique_id_doc.txt")
        self.assertGreater(results[0]["keyword_score"], 0.5)

    def test_10_top_k_parameter(self):
        """top_k restricts the number of returned chunks for keyword and hybrid."""
        long_text = "Data storage architectures and distributed indexing algorithms. " * 30
        self._upload_file(self.user1_session, "storage.txt", long_text)

        # Hybrid top_k=2
        res_h = self.client.post(
            "/api/v1/search/hybrid",
            json={"query": "distributed indexing", "top_k": 2},
            cookies={settings.SESSION_COOKIE_NAME: self.user1_session},
        )
        self.assertEqual(res_h.status_code, 200)
        self.assertEqual(len(res_h.json()["results"]), 2)

        # Keyword top_k=1
        res_kw = self.client.post(
            "/api/v1/search/keyword",
            json={"query": "distributed indexing", "top_k": 1},
            cookies={settings.SESSION_COOKIE_NAME: self.user1_session},
        )
        self.assertEqual(res_kw.status_code, 200)
        self.assertEqual(len(res_kw.json()["results"]), 1)

    def test_11_score_bounds_and_ordering(self):
        """Scores are bounded in [0.0, 1.0] and sorted strictly descending."""
        self._upload_file(self.user1_session, "doc_a.txt", "Quantum physics involves entanglement and superposition.")
        self._upload_file(self.user1_session, "doc_b.txt", "Classical computing works with binary digital bits.")

        res = self.client.post(
            "/api/v1/search/hybrid",
            json={"query": "quantum entanglement physics", "top_k": 5},
            cookies={settings.SESSION_COOKIE_NAME: self.user1_session},
        )
        self.assertEqual(res.status_code, 200)
        results = res.json()["results"]
        scores = [r["similarity_score"] for r in results]

        for s in scores:
            self.assertGreaterEqual(s, 0.0)
            self.assertLessEqual(s, 1.0)

        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_12_empty_and_whitespace_query_validation(self):
        """Empty and whitespace queries are rejected with HTTP 400."""
        # Empty keyword POST
        res1 = self.client.post(
            "/api/v1/search/keyword",
            json={"query": "", "top_k": 5},
            cookies={settings.SESSION_COOKIE_NAME: self.user1_session},
        )
        self.assertEqual(res1.status_code, 400)

        # Whitespace hybrid POST
        res2 = self.client.post(
            "/api/v1/search/hybrid",
            json={"query": "   \n\t ", "top_k": 5},
            cookies={settings.SESSION_COOKIE_NAME: self.user1_session},
        )
        self.assertEqual(res2.status_code, 400)

        # Empty hybrid GET
        res3 = self.client.get(
            "/api/v1/search/hybrid",
            params={"query": ""},
            cookies={settings.SESSION_COOKIE_NAME: self.user1_session},
        )
        self.assertEqual(res3.status_code, 400)

    def test_13_invalid_top_k_validation(self):
        """Invalid top_k values (< 1 or > 50) return HTTP 400 or 422."""
        res_zero = self.client.post(
            "/api/v1/search/hybrid",
            json={"query": "test query", "top_k": 0},
            cookies={settings.SESSION_COOKIE_NAME: self.user1_session},
        )
        self.assertIn(res_zero.status_code, [400, 422])

        res_excess = self.client.post(
            "/api/v1/search/keyword",
            json={"query": "test query", "top_k": 99},
            cookies={settings.SESSION_COOKIE_NAME: self.user1_session},
        )
        self.assertIn(res_excess.status_code, [400, 422])

    def test_14_ownership_isolation(self):
        """User A never receives User B's chunks via keyword or hybrid search."""
        # User 1 uploads confidential file
        self._upload_file(
            self.user1_session,
            "private_financials.txt",
            "Top secret executive compensation and quarterly revenue breakdown.",
        )
        # User 2 uploads gardening file
        self._upload_file(
            self.user2_session,
            "gardening_guide.txt",
            "Spring gardening tips for growing cucumbers and tomatoes in soil.",
        )

        # User 2 searches for secret executive compensation
        res_kw = self.client.post(
            "/api/v1/search/keyword",
            json={"query": "executive compensation quarterly revenue", "top_k": 5},
            cookies={settings.SESSION_COOKIE_NAME: self.user2_session},
        )
        self.assertEqual(res_kw.status_code, 200)
        self.assertEqual(res_kw.json()["total_results"], 0)

        res_hy = self.client.post(
            "/api/v1/search/hybrid",
            json={"query": "executive compensation quarterly revenue", "top_k": 5},
            cookies={settings.SESSION_COOKIE_NAME: self.user2_session},
        )
        self.assertEqual(res_hy.status_code, 200)
        filenames_user2 = [r["original_filename"] for r in res_hy.json()["results"]]
        self.assertNotIn("private_financials.txt", filenames_user2)

    def test_15_unauthenticated_access_rejected(self):
        """Unauthenticated requests to keyword and hybrid endpoints return HTTP 401."""
        unauth_client = TestClient(app)

        res_kw = unauth_client.post("/api/v1/search/keyword", json={"query": "test", "top_k": 5})
        self.assertEqual(res_kw.status_code, 401)

        res_hy = unauth_client.post("/api/v1/search/hybrid", json={"query": "test", "top_k": 5})
        self.assertEqual(res_hy.status_code, 401)

        res_kw_get = unauth_client.get("/api/v1/search/keyword", params={"query": "test"})
        self.assertEqual(res_kw_get.status_code, 401)

        res_hy_get = unauth_client.get("/api/v1/search/hybrid", params={"query": "test"})
        self.assertEqual(res_hy_get.status_code, 401)

    def test_16_no_results_empty_list(self):
        """User with no uploaded documents receives 200 OK with empty results."""
        res_kw = self.client.post(
            "/api/v1/search/keyword",
            json={"query": "anything", "top_k": 5},
            cookies={settings.SESSION_COOKIE_NAME: self.user1_session},
        )
        self.assertEqual(res_kw.status_code, 200)
        self.assertEqual(res_kw.json()["total_results"], 0)
        self.assertEqual(res_kw.json()["results"], [])

        res_hy = self.client.post(
            "/api/v1/search/hybrid",
            json={"query": "anything", "top_k": 5},
            cookies={settings.SESSION_COOKIE_NAME: self.user1_session},
        )
        self.assertEqual(res_hy.status_code, 200)
        self.assertEqual(res_hy.json()["total_results"], 0)
        self.assertEqual(res_hy.json()["results"], [])

    def test_17_no_filesystem_path_leakage(self):
        """Responses contain no server filesystem paths."""
        self._upload_file(
            self.user1_session,
            "leak_check.txt",
            "Verifying security constraints against server directory exposure.",
        )

        res = self.client.post(
            "/api/v1/search/hybrid",
            json={"query": "security constraints directory", "top_k": 5},
            cookies={settings.SESSION_COOKIE_NAME: self.user1_session},
        )
        self.assertEqual(res.status_code, 200)
        body = res.text.lower()
        self.assertNotIn("c:\\", body)
        self.assertNotIn("uploads\\", body)
        self.assertNotIn("app/data", body)

    def test_18_audit_logging_recorded(self):
        """Audit log entries are recorded for both keyword and hybrid searches."""
        self._upload_file(
            self.user1_session,
            "audit_hybrid.txt",
            "Document for validating audit logging in keyword and hybrid search.",
        )

        self.client.post(
            "/api/v1/search/keyword",
            json={"query": "audit logging keyword", "top_k": 5},
            cookies={settings.SESSION_COOKIE_NAME: self.user1_session},
        )
        self.client.post(
            "/api/v1/search/hybrid",
            json={"query": "audit logging hybrid", "top_k": 5},
            cookies={settings.SESSION_COOKIE_NAME: self.user1_session},
        )

        db = SessionLocal()
        try:
            kw_log = db.query(AuditLog).filter(
                AuditLog.action == "keyword_search",
                AuditLog.query == "audit logging keyword",
            ).first()
            self.assertIsNotNone(kw_log)

            hy_log = db.query(AuditLog).filter(
                AuditLog.action == "hybrid_search",
                AuditLog.query == "audit logging hybrid",
            ).first()
            self.assertIsNotNone(hy_log)
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
