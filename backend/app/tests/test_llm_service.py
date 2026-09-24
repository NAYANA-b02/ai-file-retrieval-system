import io
import unittest
from unittest.mock import patch, MagicMock
import httpx
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.core.database import SessionLocal
from app.models.user import User
from app.services.llm_service import call_llm_chat, call_groq_chat, GROQ_ENDPOINT


class TestLLMService(unittest.TestCase):
    def setUp(self):
        self.original_provider = settings.LLM_PROVIDER
        self.original_groq_key = settings.GROQ_API_KEY
        self.original_groq_model = settings.GROQ_MODEL
        self.messages = [
            {"role": "system", "content": "You are a test assistant."},
            {"role": "user", "content": "Hello test world."},
        ]

    def tearDown(self):
        settings.LLM_PROVIDER = self.original_provider
        settings.GROQ_API_KEY = self.original_groq_key
        settings.GROQ_MODEL = self.original_groq_model

    @patch("app.services.llm_service.call_ollama_chat")
    def test_01_ollama_provider_dispatches_to_ollama(self, mock_ollama):
        """When LLM_PROVIDER is 'ollama', call_llm_chat dispatches to call_ollama_chat."""
        settings.LLM_PROVIDER = "ollama"
        mock_ollama.return_value = "Ollama test response"

        result = call_llm_chat(self.messages)
        self.assertEqual(result, "Ollama test response")
        mock_ollama.assert_called_once_with(self.messages)

    @patch("app.services.llm_service.httpx.Client")
    def test_02_groq_provider_sends_expected_http_request(self, mock_client_cls):
        """When LLM_PROVIDER is 'groq', call_llm_chat sends valid POST to Groq endpoint."""
        settings.LLM_PROVIDER = "groq"
        settings.GROQ_API_KEY = "gsk_mock_valid_api_key_12345"
        settings.GROQ_MODEL = "openai/gpt-oss-120b"

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "Grounded answer from Groq LLM."
                    }
                }
            ]
        }
        mock_client = MagicMock()
        mock_client.post.return_value = mock_resp
        mock_client_cls.return_value.__enter__.return_value = mock_client

        result = call_llm_chat(self.messages)
        self.assertEqual(result, "Grounded answer from Groq LLM.")

        # Verify request parameters
        mock_client.post.assert_called_once()
        call_args, call_kwargs = mock_client.post.call_args
        self.assertEqual(call_args[0], GROQ_ENDPOINT)
        self.assertEqual(call_kwargs["headers"]["Authorization"], "Bearer gsk_mock_valid_api_key_12345")
        self.assertEqual(call_kwargs["headers"]["Content-Type"], "application/json")
        self.assertEqual(call_kwargs["json"]["model"], "openai/gpt-oss-120b")
        self.assertEqual(call_kwargs["json"]["messages"], self.messages)
        self.assertEqual(call_kwargs["json"]["temperature"], 0.1)
        self.assertFalse(call_kwargs["json"]["stream"])

    def test_03_missing_groq_api_key_fails_safely(self):
        """When GROQ_API_KEY is missing or empty, returns HTTP 503 without leaking details."""
        settings.LLM_PROVIDER = "groq"
        settings.GROQ_API_KEY = None

        with self.assertRaises(HTTPException) as ctx:
            call_llm_chat(self.messages)
        self.assertEqual(ctx.exception.status_code, 503)
        self.assertIn("Groq API key is not configured", ctx.exception.detail)

        settings.GROQ_API_KEY = "   "
        with self.assertRaises(HTTPException) as ctx2:
            call_llm_chat(self.messages)
        self.assertEqual(ctx2.exception.status_code, 503)

    @patch("app.services.llm_service.httpx.Client")
    def test_04_groq_connection_error_fails_safely(self, mock_client_cls):
        """Connection failure to Groq returns HTTP 503 Service Unavailable."""
        settings.LLM_PROVIDER = "groq"
        settings.GROQ_API_KEY = "gsk_test_mock"

        mock_client = MagicMock()
        mock_client.post.side_effect = httpx.ConnectError("Network unreachable")
        mock_client_cls.return_value.__enter__.return_value = mock_client

        with self.assertRaises(HTTPException) as ctx:
            call_llm_chat(self.messages)
        self.assertEqual(ctx.exception.status_code, 503)
        self.assertIn("Groq service is unavailable", ctx.exception.detail)

    @patch("app.services.llm_service.httpx.Client")
    def test_05_groq_timeout_fails_safely(self, mock_client_cls):
        """Request timeout to Groq returns HTTP 504 Gateway Timeout."""
        settings.LLM_PROVIDER = "groq"
        settings.GROQ_API_KEY = "gsk_test_mock"

        mock_client = MagicMock()
        mock_client.post.side_effect = httpx.TimeoutException("Timed out")
        mock_client_cls.return_value.__enter__.return_value = mock_client

        with self.assertRaises(HTTPException) as ctx:
            call_llm_chat(self.messages)
        self.assertEqual(ctx.exception.status_code, 504)
        self.assertIn("Groq request timed out", ctx.exception.detail)

    @patch("app.services.llm_service.httpx.Client")
    def test_06_malformed_groq_response_fails_safely(self, mock_client_cls):
        """Missing or malformed choices in Groq response returns HTTP 502."""
        settings.LLM_PROVIDER = "groq"
        settings.GROQ_API_KEY = "gsk_test_mock"

        malformed_cases = [
            {},
            {"choices": []},
            {"choices": [{}]},
            {"choices": [{"message": {}}]},
            "non-json string",
        ]

        for malformed in malformed_cases:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = malformed
            mock_client = MagicMock()
            mock_client.post.return_value = mock_resp
            mock_client_cls.return_value.__enter__.return_value = mock_client

            with self.assertRaises(HTTPException) as ctx:
                call_llm_chat(self.messages)
            self.assertEqual(ctx.exception.status_code, 502)
            self.assertIn("Unexpected response format", ctx.exception.detail)

    def test_07_unsupported_provider_fails(self):
        """Unsupported provider name returns HTTP 500."""
        settings.LLM_PROVIDER = "anthropic_unsupported"

        with self.assertRaises(HTTPException) as ctx:
            call_llm_chat(self.messages)
        self.assertEqual(ctx.exception.status_code, 500)
        self.assertIn("Unsupported LLM provider", ctx.exception.detail)


class TestRAGWithGroqIntegration(unittest.TestCase):
    """Integration test verifying RAG flow and ownership isolation when using Groq."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.user1_username = "groq_user1"
        cls.user1_email = "groq_user1@example.com"
        cls.user1_password = "Password123!"

        cls.user2_username = "groq_user2"
        cls.user2_email = "groq_user2@example.com"
        cls.user2_password = "Password123!"

    def setUp(self):
        self.original_provider = settings.LLM_PROVIDER
        self.original_groq_key = settings.GROQ_API_KEY
        settings.LLM_PROVIDER = "groq"
        settings.GROQ_API_KEY = "gsk_test_integration_key"

        db = SessionLocal()
        try:
            users = db.query(User).filter(
                (User.username.like("groq_%")) |
                (User.email.like("groq_%"))
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
        login1 = self.client.post("/api/v1/auth/login", json={
            "username_or_email": self.user1_username,
            "password": self.user1_password,
        })
        self.user1_session = login1.cookies.get(settings.SESSION_COOKIE_NAME)

        # Register and login User 2
        self.client.post("/api/v1/auth/register", json={
            "username": self.user2_username,
            "email": self.user2_email,
            "password": self.user2_password,
        })
        login2 = self.client.post("/api/v1/auth/login", json={
            "username_or_email": self.user2_username,
            "password": self.user2_password,
        })
        self.user2_session = login2.cookies.get(settings.SESSION_COOKIE_NAME)

    def tearDown(self):
        settings.LLM_PROVIDER = self.original_provider
        settings.GROQ_API_KEY = self.original_groq_key

        db = SessionLocal()
        try:
            users = db.query(User).filter(
                (User.username.like("groq_%")) |
                (User.email.like("groq_%"))
            ).all()
            for u in users:
                db.delete(u)
            db.commit()
        finally:
            db.close()

    def _upload_file(self, session_id: str, filename: str, content: str):
        return self.client.post(
            "/api/v1/files/upload",
            files={"file": (filename, io.BytesIO(content.encode("utf-8")), "text/plain")},
            cookies={settings.SESSION_COOKIE_NAME: session_id},
        )

    @patch("app.services.llm_service.httpx.Client")
    def test_08_authenticated_rag_with_groq_success(self, mock_client_cls):
        """RAG end-to-end flow succeeds with Groq, returning citations and grounded answer."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "Superposition allows qubits to exist in multiple states simultaneously."
                    }
                }
            ]
        }
        mock_client = MagicMock()
        mock_client.post.return_value = mock_resp
        mock_client_cls.return_value.__enter__.return_value = mock_client

        self._upload_file(
            self.user1_session,
            "quantum_overview.txt",
            "Superposition allows qubits to exist in multiple states simultaneously, vastly speeding up matrix calculations.",
        )

        res = self.client.post(
            "/api/v1/rag/ask",
            json={"question": "How does superposition work in quantum computing?", "top_k": 3},
            cookies={settings.SESSION_COOKIE_NAME: self.user1_session},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("Superposition allows qubits", data["answer"])
        self.assertGreaterEqual(len(data["citations"]), 1)
        self.assertEqual(data["citations"][0]["original_filename"], "quantum_overview.txt")

    @patch("app.services.llm_service.httpx.Client")
    def test_09_ownership_isolation_with_groq(self, mock_client_cls):
        """User 2 cannot access User 1's documents through Groq RAG flow."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [{"message": {"role": "assistant", "content": "Secret information."}}]
        }
        mock_client = MagicMock()
        mock_client.post.return_value = mock_resp
        mock_client_cls.return_value.__enter__.return_value = mock_client

        # Upload private file for User 1
        self._upload_file(
            self.user1_session,
            "confidential_roadmap.txt",
            "Project Odyssey top secret quarterly financial allocation.",
        )

        # User 2 asks about User 1's private document
        res = self.client.post(
            "/api/v1/rag/ask",
            json={"question": "What is the budget for Project Odyssey?", "top_k": 3},
            cookies={settings.SESSION_COOKIE_NAME: self.user2_session},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        # Should return grounded not-enough-info response without calling Groq
        self.assertEqual(data["answer"], "The uploaded documents do not contain enough information to answer this question.")
        self.assertEqual(len(data["citations"]), 0)
        mock_client.post.assert_not_called()


if __name__ == "__main__":
    unittest.main()
