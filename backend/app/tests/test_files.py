import io
import os
import re
import unittest
from pathlib import Path
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.core.database import SessionLocal
from app.models.user import User
from app.models.file import File as FileModel
from app.services.file_storage_service import get_private_upload_dir

UUID_REGEX = re.compile(r"^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}\.[a-z0-9]+$", re.IGNORECASE)


class TestPhase3FileManagement(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.user1_username = "filetest_user1"
        cls.user1_email = "filetest_user1@example.com"
        cls.user1_password = "Password123!"

        cls.user2_username = "filetest_user2"
        cls.user2_email = "filetest_user2@example.com"
        cls.user2_password = "Password123!"

    def setUp(self):
        # Clean up test users and files before each test run
        db = SessionLocal()
        try:
            users = db.query(User).filter(
                (User.username.like("filetest_%")) |
                (User.email.like("filetest_%"))
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
        # Clean up database records
        db = SessionLocal()
        try:
            users = db.query(User).filter(
                (User.username.like("filetest_%")) |
                (User.email.like("filetest_%"))
            ).all()
            for u in users:
                db.delete(u)
            db.commit()
        finally:
            db.close()

    def test_01_valid_pdf_upload(self):
        """TEST 1: Valid PDF upload"""
        pdf_content = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
        files = {"file": ("document.pdf", pdf_content, "application/pdf")}
        response = self.client.post(
            "/api/v1/files/upload",
            files=files,
            cookies={settings.SESSION_COOKIE_NAME: self.user1_session}
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["original_filename"], "document.pdf")
        self.assertEqual(data["extension"], ".pdf")
        self.assertEqual(data["mime_type"], "application/pdf")
        self.assertEqual(data["size"], len(pdf_content))
        self.assertEqual(data["processing_status"], "uploaded")
        self.assertEqual(data["text_chunk_count"], 0)
        self.assertNotIn("file_path", data)

    def test_02_valid_docx_upload(self):
        """TEST 2: Valid DOCX upload"""
        docx_content = b"PK\x03\x04\x14\x00\x06\x00" + b"\x00" * 30
        files = {
            "file": (
                "document.docx",
                docx_content,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        }
        response = self.client.post(
            "/api/v1/files/upload",
            files=files,
            cookies={settings.SESSION_COOKIE_NAME: self.user1_session}
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["original_filename"], "document.docx")
        self.assertEqual(data["extension"], ".docx")
        self.assertNotIn("file_path", data)

    def test_03_valid_txt_upload(self):
        """TEST 3: Valid TXT upload"""
        txt_content = "This is a valid plain text document for test 3.".encode("utf-8")
        files = {"file": ("notes.txt", txt_content, "text/plain")}
        response = self.client.post(
            "/api/v1/files/upload",
            files=files,
            cookies={settings.SESSION_COOKIE_NAME: self.user1_session}
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["original_filename"], "notes.txt")
        self.assertEqual(data["extension"], ".txt")
        self.assertEqual(data["mime_type"], "text/plain")
        self.assertEqual(data["size"], len(txt_content))
        self.assertNotIn("file_path", data)

    def test_04_valid_jpg_png_upload(self):
        """TEST 4: Valid JPG/PNG upload"""
        # JPG test
        jpg_content = b"\xff\xd8\xff\xe0\x00\x10JFIF" + b"\x00" * 20
        files_jpg = {"file": ("photo.jpg", jpg_content, "image/jpeg")}
        res_jpg = self.client.post(
            "/api/v1/files/upload",
            files=files_jpg,
            cookies={settings.SESSION_COOKIE_NAME: self.user1_session}
        )
        self.assertEqual(res_jpg.status_code, 201)
        self.assertEqual(res_jpg.json()["extension"], ".jpg")
        self.assertEqual(res_jpg.json()["mime_type"], "image/jpeg")

        # PNG test
        png_content = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + b"\x00" * 20
        files_png = {"file": ("image.png", png_content, "image/png")}
        res_png = self.client.post(
            "/api/v1/files/upload",
            files=files_png,
            cookies={settings.SESSION_COOKIE_NAME: self.user1_session}
        )
        self.assertEqual(res_png.status_code, 201)
        self.assertEqual(res_png.json()["extension"], ".png")
        self.assertEqual(res_png.json()["mime_type"], "image/png")

    def test_05_unsupported_extension(self):
        """TEST 5: Unsupported extension rejection"""
        exe_content = b"MZ\x90\x00\x03\x00\x00\x00"
        files = {"file": ("malware.exe", exe_content, "application/octet-stream")}
        response = self.client.post(
            "/api/v1/files/upload",
            files=files,
            cookies={settings.SESSION_COOKIE_NAME: self.user1_session}
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Unsupported file extension", response.json()["detail"])

    def test_06_empty_file(self):
        """TEST 6: Empty file rejection (0 bytes)"""
        files = {"file": ("empty.txt", b"", "text/plain")}
        response = self.client.post(
            "/api/v1/files/upload",
            files=files,
            cookies={settings.SESSION_COOKIE_NAME: self.user1_session}
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("empty", response.json()["detail"].lower())

    def test_07_oversized_file(self):
        """TEST 7: Oversized file rejection (> MAX_UPLOAD_SIZE_MB)"""
        # Create oversized payload exceeding settings.MAX_UPLOAD_SIZE_MB
        oversized_bytes = b"A" * ((settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024) + 1024)
        files = {"file": ("large.txt", oversized_bytes, "text/plain")}
        response = self.client.post(
            "/api/v1/files/upload",
            files=files,
            cookies={settings.SESSION_COOKIE_NAME: self.user1_session}
        )
        self.assertEqual(response.status_code, 413)
        self.assertIn("exceeds maximum limit", response.json()["detail"])

    def test_08_unauthenticated_upload(self):
        """TEST 8: Unauthenticated upload rejected with 401"""
        unauth_client = TestClient(app)
        txt_content = b"Hello unauthenticated world"
        files = {"file": ("test.txt", txt_content, "text/plain")}
        response = unauth_client.post("/api/v1/files/upload", files=files)
        self.assertEqual(response.status_code, 401)

    def test_09_authenticated_user_file_listing(self):
        """TEST 9: Authenticated user's file listing (GET /api/v1/files)"""
        # Upload 2 files for User 1
        txt_content = b"File 1 content"
        pdf_content = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"

        self.client.post(
            "/api/v1/files/upload",
            files={"file": ("f1.txt", txt_content, "text/plain")},
            cookies={settings.SESSION_COOKIE_NAME: self.user1_session}
        )
        self.client.post(
            "/api/v1/files/upload",
            files={"file": ("f2.pdf", pdf_content, "application/pdf")},
            cookies={settings.SESSION_COOKIE_NAME: self.user1_session}
        )

        res = self.client.get(
            "/api/v1/files",
            cookies={settings.SESSION_COOKIE_NAME: self.user1_session}
        )
        self.assertEqual(res.status_code, 200)
        items = res.json()
        self.assertEqual(len(items), 2)
        filenames = {f["original_filename"] for f in items}
        self.assertIn("f1.txt", filenames)
        self.assertIn("f2.pdf", filenames)
        for item in items:
            self.assertNotIn("file_path", item)

    def test_10_ownership_isolation(self):
        """TEST 10: Ownership isolation — User B cannot see User A's files"""
        # Upload file as User 1
        txt_content_u1 = b"User 1 secret file"
        self.client.post(
            "/api/v1/files/upload",
            files={"file": ("secret_u1.txt", txt_content_u1, "text/plain")},
            cookies={settings.SESSION_COOKIE_NAME: self.user1_session}
        )

        # Upload file as User 2
        txt_content_u2 = b"User 2 file"
        self.client.post(
            "/api/v1/files/upload",
            files={"file": ("visible_u2.txt", txt_content_u2, "text/plain")},
            cookies={settings.SESSION_COOKIE_NAME: self.user2_session}
        )

        # User 2 lists files
        res_u2 = self.client.get(
            "/api/v1/files",
            cookies={settings.SESSION_COOKIE_NAME: self.user2_session}
        )
        self.assertEqual(res_u2.status_code, 200)
        files_u2 = res_u2.json()
        self.assertEqual(len(files_u2), 1)
        self.assertEqual(files_u2[0]["original_filename"], "visible_u2.txt")
        self.assertNotEqual(files_u2[0]["original_filename"], "secret_u1.txt")

        # User 1 lists files
        res_u1 = self.client.get(
            "/api/v1/files",
            cookies={settings.SESSION_COOKIE_NAME: self.user1_session}
        )
        self.assertEqual(res_u1.status_code, 200)
        files_u1 = res_u1.json()
        self.assertEqual(len(files_u1), 1)
        self.assertEqual(files_u1[0]["original_filename"], "secret_u1.txt")

    def test_11_stored_filename_is_uuid_based(self):
        """TEST 11: Stored filename is UUID-based"""
        txt_content = b"UUID validation check"
        res = self.client.post(
            "/api/v1/files/upload",
            files={"file": ("my_sensitive_resume.txt", txt_content, "text/plain")},
            cookies={settings.SESSION_COOKIE_NAME: self.user1_session}
        )
        self.assertEqual(res.status_code, 201)
        data = res.json()
        stored_filename = data["stored_filename"]
        self.assertTrue(
            bool(UUID_REGEX.match(stored_filename)),
            f"stored_filename '{stored_filename}' does not conform to UUID pattern"
        )
        self.assertNotIn("my_sensitive_resume", stored_filename)

    def test_12_physical_path_not_exposed_in_api_response(self):
        """TEST 12: Physical path is not exposed in API response"""
        txt_content = b"Content for leak check"
        res = self.client.post(
            "/api/v1/files/upload",
            files={"file": ("safe.txt", txt_content, "text/plain")},
            cookies={settings.SESSION_COOKIE_NAME: self.user1_session}
        )
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertNotIn("file_path", data)
        for key in data.keys():
            self.assertFalse("path" in key.lower())

        # Check list endpoint as well
        list_res = self.client.get(
            "/api/v1/files",
            cookies={settings.SESSION_COOKIE_NAME: self.user1_session}
        )
        for item in list_res.json():
            self.assertNotIn("file_path", item)

    def test_13_uploaded_file_stored_in_private_upload_dir(self):
        """TEST 13: Uploaded file is stored in private upload directory"""
        txt_content = b"Checking private upload directory storage"
        res = self.client.post(
            "/api/v1/files/upload",
            files={"file": ("storage_check.txt", txt_content, "text/plain")},
            cookies={settings.SESSION_COOKIE_NAME: self.user1_session}
        )
        self.assertEqual(res.status_code, 201)
        stored_filename = res.json()["stored_filename"]

        upload_dir = get_private_upload_dir()
        physical_file = upload_dir / stored_filename
        self.assertTrue(physical_file.exists(), "Physical file must exist in upload dir")
        self.assertEqual(physical_file.read_bytes(), txt_content)

    def test_14_metadata_persisted_correctly(self):
        """TEST 14: Metadata is persisted correctly in PostgreSQL"""
        pdf_content = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
        res = self.client.post(
            "/api/v1/files/upload",
            files={"file": ("meta_doc.pdf", pdf_content, "application/pdf")},
            cookies={settings.SESSION_COOKIE_NAME: self.user1_session}
        )
        self.assertEqual(res.status_code, 201)
        file_id = res.json()["id"]

        db = SessionLocal()
        try:
            db_record = db.query(FileModel).filter(FileModel.id == file_id).first()
            self.assertIsNotNone(db_record)
            self.assertEqual(db_record.original_filename, "meta_doc.pdf")
            self.assertEqual(db_record.extension, ".pdf")
            self.assertEqual(db_record.mime_type, "application/pdf")
            self.assertEqual(db_record.size, len(pdf_content))
            self.assertEqual(db_record.processing_status, "uploaded")
            self.assertIsNone(db_record.extracted_text)
            self.assertIsNone(db_record.error_message)
            self.assertEqual(db_record.text_chunk_count, 0)
            self.assertIsNotNone(db_record.uploaded_at)
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
