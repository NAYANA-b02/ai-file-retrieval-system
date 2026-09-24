#!/usr/bin/env bash
# Build script for Render deployment
set -o errexit

pip install --upgrade pip
pip install -r requirements.txt

# If running in environment with apt permissions
if command -v apt-get &> /dev/null && [ "$(id -u)" -eq 0 ]; then
    apt-get update && apt-get install -y tesseract-ocr tesseract-ocr-eng || true
fi
