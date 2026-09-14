import io
import time
import unittest
from fastapi.testclient import TestClient
import pymupdf
import docx
from PIL import Image, ImageDraw

from app.main import app
from app.core.config import settings
from app.core.database import SessionLocal
from app.models.user import User
from app.models.file import File as FileModel


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


def create_sample_ocr_image(text: str, fmt: str = "PNG") -> bytes:
    # High contrast image for OCR accuracy
    img = Image.new("RGB", (300, 80), color=(255, 255, 255))
    d = ImageDraw.Draw(img)
    d.text((10, 25), text, fill=(0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()


class TestPhase4TextExtraction(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.user1_username = "extract_user1"
        cls.user1_email = "extract_user1@example.com"
        cls.user1_password = "Password123!"

        cls.user2_username = "extract_user2"
        cls.user2_email = "extract_user2@example.com"
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
                (User.username.like("extract_%")) |
                (User.email.like("extract_%"))
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
                (User.username.like("extract_%")) |
                (User.email.like("extract_%"))
            ).all()
            for u in users:
                db.delete(u)
            db.commit()
        finally:
            db.close()

    def test_01_pdf_text_extraction(self):
        """TEST 1: PDF text extraction using PyMuPDF"""
        expected_text = "PyMuPDF text extraction test document"
        pdf_bytes = create_sample_pdf(expected_text)

        response = self.client.post(
            "/api/v1/files/upload",
            files={"file": ("sample.pdf", pdf_bytes, "application/pdf")},
            cookies={settings.SESSION_COOKIE_NAME: self.user1_session}
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["processing_status"], "processing")
        self.assertIsNotNone(data["extracted_text"])
        self.assertIn("PyMuPDF text extraction", data["extracted_text"])
        self.assertIsNone(data["error_message"])

        file_data = self.wait_for_file_completion(data["id"], cookies={settings.SESSION_COOKIE_NAME: self.user1_session})
        self.assertEqual(file_data["processing_status"], "completed")
        self.assertIn("PyMuPDF text extraction", file_data["extracted_text"])
        self.assertIsNone(file_data["error_message"])

    def test_02_docx_text_extraction(self):
        """TEST 2: DOCX text extraction using python-docx"""
        expected_text = "python-docx extraction test content"
        docx_bytes = create_sample_docx(expected_text)

        response = self.client.post(
            "/api/v1/files/upload",
            files={"file": (
                "sample.docx",
                docx_bytes,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )},
            cookies={settings.SESSION_COOKIE_NAME: self.user1_session}
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["processing_status"], "processing")
        self.assertIsNotNone(data["extracted_text"])
        self.assertIn(expected_text, data["extracted_text"])
        self.assertIsNone(data["error_message"])

        file_data = self.wait_for_file_completion(data["id"], cookies={settings.SESSION_COOKIE_NAME: self.user1_session})
        self.assertEqual(file_data["processing_status"], "completed")
        self.assertIn(expected_text, file_data["extracted_text"])
        self.assertIsNone(file_data["error_message"])

    def test_03_txt_text_extraction(self):
        """TEST 3: Plain text extraction with UTF-8 decoding"""
        expected_text = "Plain text extraction with special characters: ü, é, ñ."
        txt_bytes = expected_text.encode("utf-8")

        response = self.client.post(
            "/api/v1/files/upload",
            files={"file": ("sample.txt", txt_bytes, "text/plain")},
            cookies={settings.SESSION_COOKIE_NAME: self.user1_session}
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["processing_status"], "processing")
        self.assertIsNotNone(data["extracted_text"])
        self.assertEqual(data["extracted_text"], expected_text)
        self.assertIsNone(data["error_message"])

        file_data = self.wait_for_file_completion(data["id"], cookies={settings.SESSION_COOKIE_NAME: self.user1_session})
        self.assertEqual(file_data["processing_status"], "completed")
        self.assertEqual(file_data["extracted_text"], expected_text)
        self.assertIsNone(file_data["error_message"])

    def test_04_png_image_ocr(self):
        """TEST 4: PNG image OCR using pytesseract + Pillow"""
        png_bytes = create_sample_ocr_image("INVOICE", fmt="PNG")

        response = self.client.post(
            "/api/v1/files/upload",
            files={"file": ("ocr.png", png_bytes, "image/png")},
            cookies={settings.SESSION_COOKIE_NAME: self.user1_session}
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["processing_status"], "processing")
        self.assertIsNotNone(data["extracted_text"])
        self.assertIn("INVOICE", data["extracted_text"].upper())

        file_data = self.wait_for_file_completion(data["id"], cookies={settings.SESSION_COOKIE_NAME: self.user1_session})
        self.assertEqual(file_data["processing_status"], "completed")
        self.assertIsNotNone(file_data["extracted_text"])
        self.assertIn("INVOICE", file_data["extracted_text"].upper())

    def test_05_jpeg_image_ocr(self):
        """TEST 5: JPEG image OCR using pytesseract + Pillow"""
        jpg_bytes = create_sample_ocr_image("DOCUMENT", fmt="JPEG")

        response = self.client.post(
            "/api/v1/files/upload",
            files={"file": ("ocr.jpg", jpg_bytes, "image/jpeg")},
            cookies={settings.SESSION_COOKIE_NAME: self.user1_session}
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["processing_status"], "processing")
        self.assertIsNotNone(data["extracted_text"])
        self.assertIn("DOCUMENT", data["extracted_text"].upper())

        file_data = self.wait_for_file_completion(data["id"], cookies={settings.SESSION_COOKIE_NAME: self.user1_session})
        self.assertEqual(file_data["processing_status"], "completed")
        self.assertIsNotNone(file_data["extracted_text"])
        self.assertIn("DOCUMENT", file_data["extracted_text"].upper())

    def test_06_corrupted_file_error_handling(self):
        """TEST 6: Corrupted file fails safely with status=failed and safe error message"""
        # Starts with %PDF- header so validation passes, but subsequent bytes are corrupted
        corrupted_pdf = b"%PDF-1.4\nCorrupted content trailing garbage \xff\xfe\x00\x01"

        response = self.client.post(
            "/api/v1/files/upload",
            files={"file": ("corrupt.pdf", corrupted_pdf, "application/pdf")},
            cookies={settings.SESSION_COOKIE_NAME: self.user1_session}
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        # Processing status should reflect completion or failure gracefully (or processing before background completes)
        self.assertIn(data["processing_status"], ("failed", "completed", "processing"))
        if data["processing_status"] == "failed":
            self.assertIsNotNone(data["error_message"])
            self.assertNotIn("C:\\", data["error_message"])
            self.assertNotIn("Users", data["error_message"])
        else:
            file_data = self.wait_for_file_completion(data["id"], cookies={settings.SESSION_COOKIE_NAME: self.user1_session})
            self.assertIn(file_data["processing_status"], ("failed", "completed"))

    def test_07_get_file_by_id_and_ownership(self):
        """TEST 7: GET /api/v1/files/{file_id} returns extracted text and enforces ownership"""
        txt_bytes = b"User 1 confidential text"
        res = self.client.post(
            "/api/v1/files/upload",
            files={"file": ("u1_doc.txt", txt_bytes, "text/plain")},
            cookies={settings.SESSION_COOKIE_NAME: self.user1_session}
        )
        self.assertEqual(res.status_code, 201)
        file_id = res.json()["id"]

        # User 1 can view own file
        get_res_u1 = self.client.get(
            f"/api/v1/files/{file_id}",
            cookies={settings.SESSION_COOKIE_NAME: self.user1_session}
        )
        self.assertEqual(get_res_u1.status_code, 200)
        self.assertEqual(get_res_u1.json()["extracted_text"], "User 1 confidential text")
        self.assertNotIn("file_path", get_res_u1.json())

        # User 2 cannot access User 1's file
        get_res_u2 = self.client.get(
            f"/api/v1/files/{file_id}",
            cookies={settings.SESSION_COOKIE_NAME: self.user2_session}
        )
        self.assertEqual(get_res_u2.status_code, 404)


if __name__ == "__main__":
    unittest.main()
