#!/usr/bin/env bash
# Build script for Render deployment
set -o errexit

echo "=== Starting Render Build ==="
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# Tesseract installation in Render environments
if ! command -v tesseract &> /dev/null; then
    echo "Tesseract binary not found in PATH. Checking installation options..."
    if [ "$(id -u)" -eq 0 ]; then
        echo "Root permissions detected. Installing tesseract-ocr via apt-get..."
        apt-get update && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-eng || true
    elif command -v sudo &> /dev/null; then
        echo "sudo available. Installing tesseract-ocr via sudo apt-get..."
        sudo apt-get update && sudo apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-eng || true
    fi
fi

# Verification of Tesseract installation in build environment
if command -v tesseract &> /dev/null; then
    echo "=== Tesseract OCR verification: SUCCESS ==="
    tesseract --version
elif [ -f "/usr/bin/tesseract" ] || [ -f "/usr/local/bin/tesseract" ]; then
    echo "=== Tesseract OCR found in standard path ==="
    /usr/bin/tesseract --version 2>/dev/null || /usr/local/bin/tesseract --version 2>/dev/null || true
else
    echo "=== Warning: Tesseract not found during shell build. If deploying on Render, use the Docker runtime (backend/Dockerfile) ==="
fi

echo "=== Render Build Completed Successfully ==="
