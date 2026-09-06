import unittest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.main import app
from app.core.config import settings
from app.core.database import SessionLocal, engine
from app.core.security import verify_password
from app.models.user import User
from app.models.session import Session as UserSession
from app.models.audit_log import AuditLog


class TestPhase2Authentication(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.test_username = "testuser_phase2"
        cls.test_email = "testuser_phase2@example.com"
        cls.test_password = "SecurePassword123!"

    def setUp(self):
        # Clean up any test users and sessions before each test
        db = SessionLocal()
        try:
            users = db.query(User).filter(
                (User.username == self.test_username) | 
                (User.email == self.test_email) |
                (User.username.like("test_%"))
            ).all()
            for u in users:
                db.delete(u)
            db.commit()
        finally:
            db.close()

    def test_01_user_registration(self):
        """TEST 1 — Registration: POST /api/v1/auth/register"""
        payload = {
            "username": self.test_username,
            "email": self.test_email,
            "password": self.test_password
        }
        response = self.client.post("/api/v1/auth/register", json=payload)
        self.assertEqual(response.status_code, 201)
        data = response.json()

        # Check safe response fields
        self.assertIn("id", data)
        self.assertEqual(data["username"], self.test_username)
        self.assertEqual(data["email"], self.test_email)
        self.assertTrue(data["is_active"])
        self.assertIn("created_at", data)

        # Assert no password or password_hash returned
        self.assertNotIn("password", data)
        self.assertNotIn("password_hash", data)

        # Verify in database
        db = SessionLocal()
        try:
            db_user = db.query(User).filter(User.username == self.test_username).first()
            self.assertIsNotNone(db_user)
            self.assertNotEqual(db_user.password_hash, self.test_password)
            self.assertTrue(verify_password(self.test_password, db_user.password_hash))
            self.assertTrue(db_user.password_hash.startswith("$2b$") or db_user.password_hash.startswith("$2a$"))
        finally:
            db.close()

    def test_02_duplicate_registration(self):
        """TEST 2 — Duplicate registration: Reject duplicate username and email"""
        # Register first user
        payload = {
            "username": self.test_username,
            "email": self.test_email,
            "password": self.test_password
        }
        res1 = self.client.post("/api/v1/auth/register", json=payload)
        self.assertEqual(res1.status_code, 201)

        # Duplicate username, different email
        res_dup_user = self.client.post("/api/v1/auth/register", json={
            "username": self.test_username,
            "email": "different_email@example.com",
            "password": "AnotherPassword123!"
        })
        self.assertEqual(res_dup_user.status_code, 400)
        self.assertIn("Username already registered", res_dup_user.json()["detail"])

        # Different username, duplicate email
        res_dup_email = self.client.post("/api/v1/auth/register", json={
            "username": "different_user",
            "email": self.test_email,
            "password": "AnotherPassword123!"
        })
        self.assertEqual(res_dup_email.status_code, 400)
        self.assertIn("Email already registered", res_dup_email.json()["detail"])

        # Verify only 1 user exists in DB
        db = SessionLocal()
        try:
            count = db.query(User).filter(User.username == self.test_username).count()
            self.assertEqual(count, 1)
        finally:
            db.close()

    def test_03_login_success(self):
        """TEST 3 — Login: POST /api/v1/auth/login with valid credentials"""
        # Register user
        self.client.post("/api/v1/auth/register", json={
            "username": self.test_username,
            "email": self.test_email,
            "password": self.test_password
        })

        # Login with username
        login_res = self.client.post("/api/v1/auth/login", json={
            "username_or_email": self.test_username,
            "password": self.test_password
        })
        self.assertEqual(login_res.status_code, 200)
        data = login_res.json()
        self.assertEqual(data["username"], self.test_username)
        self.assertNotIn("password", data)
        self.assertNotIn("password_hash", data)
        self.assertNotIn("session_id", data)

        # Verify HTTP-only cookie was set
        cookie_header = login_res.headers.get("set-cookie", "")
        self.assertIn(settings.SESSION_COOKIE_NAME, cookie_header)
        self.assertIn("HttpOnly", cookie_header, "Cookie must have HttpOnly flag")
        self.assertIn("samesite=lax", cookie_header.lower())

        # Verify session exists in PostgreSQL
        session_id = login_res.cookies.get(settings.SESSION_COOKIE_NAME)
        self.assertIsNotNone(session_id)
        db = SessionLocal()
        try:
            db_session = db.query(UserSession).filter(UserSession.id == session_id).first()
            self.assertIsNotNone(db_session)
            self.assertTrue(db_session.is_active)
            self.assertEqual(db_session.user_id, data["id"])
            self.assertIsNotNone(db_session.expires_at)
            self.assertIsNotNone(db_session.created_at)
        finally:
            db.close()

        # Login with email
        login_email_res = self.client.post("/api/v1/auth/login", json={
            "username_or_email": self.test_email,
            "password": self.test_password
        })
        self.assertEqual(login_email_res.status_code, 200)

    def test_04_invalid_login(self):
        """TEST 4 — Invalid login: Wrong password and nonexistent user"""
        self.client.post("/api/v1/auth/register", json={
            "username": self.test_username,
            "email": self.test_email,
            "password": self.test_password
        })

        # Wrong password
        res_wrong_pw = self.client.post("/api/v1/auth/login", json={
            "username_or_email": self.test_username,
            "password": "WrongPassword999!"
        })
        self.assertEqual(res_wrong_pw.status_code, 401)
        self.assertEqual(res_wrong_pw.json()["detail"], "Invalid username/email or password")
        self.assertNotIn("set-cookie", res_wrong_pw.headers)

        # Nonexistent user
        res_no_user = self.client.post("/api/v1/auth/login", json={
            "username_or_email": "nonexistent_user",
            "password": "Password123!"
        })
        self.assertEqual(res_no_user.status_code, 401)
        self.assertEqual(res_no_user.json()["detail"], "Invalid username/email or password")

    def test_05_current_user_authenticated(self):
        """TEST 5 — Current user: GET /api/v1/auth/me with valid session cookie"""
        self.client.post("/api/v1/auth/register", json={
            "username": self.test_username,
            "email": self.test_email,
            "password": self.test_password
        })
        login_res = self.client.post("/api/v1/auth/login", json={
            "username_or_email": self.test_username,
            "password": self.test_password
        })
        session_id = login_res.cookies.get(settings.SESSION_COOKIE_NAME)

        # Request /me with cookie
        me_res = self.client.get("/api/v1/auth/me", cookies={settings.SESSION_COOKIE_NAME: session_id})
        self.assertEqual(me_res.status_code, 200)
        data = me_res.json()
        self.assertEqual(data["username"], self.test_username)
        self.assertEqual(data["email"], self.test_email)

        # Verify last_seen_at updated in database
        db = SessionLocal()
        try:
            sess = db.query(UserSession).filter(UserSession.id == session_id).first()
            self.assertIsNotNone(sess.last_seen_at)
        finally:
            db.close()

    def test_06_missing_authentication(self):
        """TEST 6 — Missing authentication: GET /api/v1/auth/me without session cookie"""
        me_res = self.client.get("/api/v1/auth/me")
        self.assertEqual(me_res.status_code, 401)
        self.assertIn("detail", me_res.json())

    def test_07_logout(self):
        """TEST 7 — Logout: POST /api/v1/auth/logout invalidates session and clears cookie"""
        self.client.post("/api/v1/auth/register", json={
            "username": self.test_username,
            "email": self.test_email,
            "password": self.test_password
        })
        login_res = self.client.post("/api/v1/auth/login", json={
            "username_or_email": self.test_username,
            "password": self.test_password
        })
        session_id = login_res.cookies.get(settings.SESSION_COOKIE_NAME)

        logout_res = self.client.post(
            "/api/v1/auth/logout",
            cookies={settings.SESSION_COOKIE_NAME: session_id}
        )
        self.assertEqual(logout_res.status_code, 200)
        self.assertEqual(logout_res.json()["message"], "Successfully logged out")

        # Verify in DB that session is marked inactive
        db = SessionLocal()
        try:
            sess = db.query(UserSession).filter(UserSession.id == session_id).first()
            self.assertFalse(sess.is_active)
        finally:
            db.close()

    def test_08_current_user_after_logout(self):
        """TEST 8 — Current user after logout: GET /api/v1/auth/me returns 401"""
        self.client.post("/api/v1/auth/register", json={
            "username": self.test_username,
            "email": self.test_email,
            "password": self.test_password
        })
        login_res = self.client.post("/api/v1/auth/login", json={
            "username_or_email": self.test_username,
            "password": self.test_password
        })
        session_id = login_res.cookies.get(settings.SESSION_COOKIE_NAME)

        self.client.post(
            "/api/v1/auth/logout",
            cookies={settings.SESSION_COOKIE_NAME: session_id}
        )

        me_res = self.client.get(
            "/api/v1/auth/me",
            cookies={settings.SESSION_COOKIE_NAME: session_id}
        )
        self.assertEqual(me_res.status_code, 401)

    def test_09_expired_and_inactive_session(self):
        """TEST 9 — Expired/inactive session: Returns 401"""
        self.client.post("/api/v1/auth/register", json={
            "username": self.test_username,
            "email": self.test_email,
            "password": self.test_password
        })
        login_res = self.client.post("/api/v1/auth/login", json={
            "username_or_email": self.test_username,
            "password": self.test_password
        })
        session_id = login_res.cookies.get(settings.SESSION_COOKIE_NAME)

        # Manually expire the session in DB
        db = SessionLocal()
        try:
            sess = db.query(UserSession).filter(UserSession.id == session_id).first()
            sess.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
            db.commit()
        finally:
            db.close()

        me_res = self.client.get(
            "/api/v1/auth/me",
            cookies={settings.SESSION_COOKIE_NAME: session_id}
        )
        self.assertEqual(me_res.status_code, 401)
        self.assertEqual(me_res.json()["detail"], "Session expired")

        # Test inactive user
        db = SessionLocal()
        try:
            u = db.query(User).filter(User.username == self.test_username).first()
            u.is_active = False
            # Create a fresh valid session for inactive user
            fresh_sess = UserSession(
                id="inactive_user_session_test",
                user_id=u.id,
                expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
                is_active=True
            )
            db.add(fresh_sess)
            db.commit()
        finally:
            db.close()

        res_inactive_user = self.client.get(
            "/api/v1/auth/me",
            cookies={settings.SESSION_COOKIE_NAME: "inactive_user_session_test"}
        )
        self.assertEqual(res_inactive_user.status_code, 401)

    def test_10_database_verification(self):
        """TEST 10 — Database verification: users, sessions, bcrypt hashes, timestamps"""
        self.client.post("/api/v1/auth/register", json={
            "username": self.test_username,
            "email": self.test_email,
            "password": self.test_password
        })
        login_res = self.client.post("/api/v1/auth/login", json={
            "username_or_email": self.test_username,
            "password": self.test_password
        })
        session_id = login_res.cookies.get(settings.SESSION_COOKIE_NAME)

        db = SessionLocal()
        try:
            # Verify user record
            user = db.query(User).filter(User.username == self.test_username).first()
            self.assertIsNotNone(user)
            self.assertIsNotNone(user.created_at)
            self.assertTrue(user.is_active)
            self.assertFalse(self.test_password in user.password_hash)
            self.assertTrue(user.password_hash.startswith("$2"))

            # Verify session record
            session = db.query(UserSession).filter(UserSession.id == session_id).first()
            self.assertIsNotNone(session)
            self.assertIsNotNone(session.created_at)
            self.assertIsNotNone(session.expires_at)
            self.assertTrue(session.is_active)
            self.assertEqual(session.user_id, user.id)

            # Raw SQL check against PostgreSQL schema
            with engine.connect() as conn:
                res = conn.execute(text("SELECT id, username, email FROM users WHERE username=:u"), {"u": self.test_username}).mappings().first()
                self.assertIsNotNone(res)
                self.assertEqual(res["username"], self.test_username)
        finally:
            db.close()

    def test_phase1_regression(self):
        """PHASE 1 REGRESSION: Health check, root endpoint, Swagger UI /docs"""
        # Health check
        res_health = self.client.get("/api/v1/health")
        self.assertEqual(res_health.status_code, 200)
        data = res_health.json()
        self.assertEqual(data["status"], "healthy")
        self.assertTrue(data["database"]["connected"])

        # Root endpoint
        res_root = self.client.get("/")
        self.assertEqual(res_root.status_code, 200)

        # Swagger docs
        res_docs = self.client.get("/docs")
        self.assertEqual(res_docs.status_code, 200)


if __name__ == "__main__":
    unittest.main()
