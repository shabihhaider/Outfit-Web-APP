"""
app/storage.py
Supabase Storage helper — upload, download, delete, URL generation.
Uses requests directly (no SDK dependency).
"""

from __future__ import annotations

import logging
import mimetypes
import os

import requests
from flask import current_app

logger = logging.getLogger(__name__)


def _cfg():
    """Return (url, key, bucket) from Flask config."""
    return (
        current_app.config.get("SUPABASE_URL", ""),
        current_app.config.get("SUPABASE_SERVICE_KEY", ""),
        current_app.config.get("SUPABASE_BUCKET", "wardrobe-images"),
    )


def is_configured() -> bool:
    """True when Supabase Storage env vars are set."""
    try:
        url, key, _ = _cfg()
        return bool(url and key)
    except RuntimeError:
        # Outside Flask app context (e.g. tests)
        return bool(
            os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_SERVICE_KEY")
        )


def get_public_url(filename: str) -> str:
    """Build public CDN URL for a file. No network call."""
    try:
        url, _, bucket = _cfg()
    except RuntimeError:
        url = os.environ.get("SUPABASE_URL", "")
        bucket = "wardrobe-images"
    if not url:
        return f"/uploads/{filename}"
    return f"{url}/storage/v1/object/public/{bucket}/{filename}"


def upload_file(filename: str, file_bytes: bytes, content_type: str = "image/png") -> str:
    """Upload bytes to Supabase Storage. Returns public URL on success."""
    url, key, bucket = _cfg()
    if not url or not key:
        logger.debug("Supabase not configured, skipping upload for %s", filename)
        return f"/uploads/{filename}"

    endpoint = f"{url}/storage/v1/object/{bucket}/{filename}"
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": content_type,
        "x-upsert": "true",
    }
    try:
        resp = requests.post(endpoint, headers=headers, data=file_bytes, timeout=30)
        resp.raise_for_status()
        logger.info("Uploaded %s to Supabase (%d bytes)", filename, len(file_bytes))
        return get_public_url(filename)
    except requests.RequestException as exc:
        logger.warning("Supabase upload failed for %s: %s", filename, exc)
        return f"/uploads/{filename}"


def upload_file_from_path(filepath: str, filename: str) -> str:
    """Read a local file and upload it to Supabase Storage."""
    content_type = mimetypes.guess_type(filepath)[0] or "image/png"
    with open(filepath, "rb") as f:
        return upload_file(filename, f.read(), content_type)


def download_file(filename: str) -> bytes | None:
    """Download a file from Supabase public URL. Returns bytes or None."""
    public_url = get_public_url(filename)
    if not public_url.startswith("http"):
        return None
    try:
        resp = requests.get(public_url, timeout=30)
        resp.raise_for_status()
        return resp.content
    except requests.RequestException as exc:
        logger.warning("Supabase download failed for %s: %s", filename, exc)
        return None


def delete_file(filename: str) -> bool:
    """Delete a file from Supabase Storage."""
    url, key, bucket = _cfg()
    if not url or not key:
        return False

    endpoint = f"{url}/storage/v1/object/{bucket}/{filename}"
    headers = {"Authorization": f"Bearer {key}"}
    try:
        resp = requests.delete(endpoint, headers=headers, timeout=15)
        if resp.status_code in (200, 204, 404):
            return True
        resp.raise_for_status()
        return True
    except requests.RequestException as exc:
        logger.warning("Supabase delete failed for %s: %s", filename, exc)
        return False
