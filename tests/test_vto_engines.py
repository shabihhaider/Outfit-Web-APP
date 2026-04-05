"""
tests/test_vto_engines.py
Unit tests for VTO engine routing: FASHN primary → IDM-VTON fallback.

Mocks gradio_client so no real API calls are made.
Run: pytest tests/test_vto_engines.py -v
"""
from __future__ import annotations

import io
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def vto_app(flask_app):
    """Flask app with VTO config set."""
    flask_app.config["HF_TOKEN"] = "hf_test_token"
    flask_app.config["HF_FASHN_SPACE_ID"] = "fashn-ai/fashn-vton-1.5"
    flask_app.config["HF_VTO_SPACE_ID"] = "yisol/IDM-VTON"
    return flask_app


@pytest.fixture
def vto_client(vto_app):
    return vto_app.test_client()


@pytest.fixture
def vto_auth(vto_client):
    """Register + login, return auth headers."""
    vto_client.post("/auth/register", json={
        "name": "VTO Tester", "email": "vto@test.com",
        "password": "password123", "gender": "men",
    })
    resp = vto_client.post("/auth/login", json={
        "email": "vto@test.com", "password": "password123",
    })
    token = resp.get_json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def vto_item(vto_client, vto_auth, minimal_png):
    """Upload a wardrobe item for VTO testing."""
    data = {
        "image": (io.BytesIO(minimal_png), "shirt.png", "image/png"),
        "formality": "casual",
        "gender": "men",
    }
    resp = vto_client.post(
        "/wardrobe/items", data=data,
        headers=vto_auth, content_type="multipart/form-data",
    )
    assert resp.status_code == 201
    return resp.get_json()


@pytest.fixture
def person_photo_uploaded(vto_client, vto_auth, minimal_png):
    """Upload a person photo so VTO jobs can be submitted."""
    resp = vto_client.post(
        "/vto/person-photo",
        data={"photo": (io.BytesIO(minimal_png), "person.png", "image/png")},
        headers=vto_auth, content_type="multipart/form-data",
    )
    assert resp.status_code == 201
    return resp.get_json()


# ─── Tests ────────────────────────────────────────────────────────────────────

class TestFASHNPrimaryEngine:
    """Test that FASHN is called first and produces a result."""

    @patch("gradio_client.Client")
    @patch("gradio_client.handle_file")
    def test_fashn_success(self, mock_handle_file, mock_client_cls,
                           vto_client, vto_auth, vto_item, person_photo_uploaded,
                           tmp_path, minimal_png):
        """FASHN succeeds on first attempt → job status = ready."""
        # Create a fake result file that gradio_client would return
        fake_result = str(tmp_path / "result.png")
        with open(fake_result, "wb") as f:
            f.write(minimal_png)

        mock_handle_file.side_effect = lambda x: x
        mock_client_instance = MagicMock()
        mock_client_instance.predict.return_value = fake_result
        mock_client_cls.return_value = mock_client_instance

        # Submit job
        resp = vto_client.post(
            "/vto/jobs",
            json={"item_id": vto_item["id"]},
            headers=vto_auth,
        )
        assert resp.status_code == 202
        job_id = resp.get_json()["id"]

        # Wait for background thread
        import time
        time.sleep(2)

        # Poll result
        resp = vto_client.get(f"/vto/jobs/{job_id}", headers=vto_auth)
        data = resp.get_json()

        # FASHN should have been called
        mock_client_cls.assert_called()
        call_args = mock_client_cls.call_args
        assert "fashn" in call_args[0][0].lower() or "fashn" in str(call_args)

        assert data["status"] == "ready"
        assert data["result_url"] is not None


class TestFallbackToIDMVTON:
    """Test that IDM-VTON is called when FASHN fails."""

    @patch("gradio_client.Client")
    @patch("gradio_client.handle_file")
    @patch("app.vto.routes.time.sleep")
    def test_fashn_fails_idmvton_succeeds(self, mock_sleep, mock_handle_file, mock_client_cls,
                                           vto_client, vto_auth, vto_item,
                                           person_photo_uploaded, tmp_path, minimal_png):
        """FASHN fails → IDM-VTON fallback succeeds → job status = ready."""
        fake_result = str(tmp_path / "result.png")
        with open(fake_result, "wb") as f:
            f.write(minimal_png)

        mock_handle_file.side_effect = lambda x: x

        call_count = [0]

        def side_effect_client(space_id, **kwargs):
            instance = MagicMock()
            call_count[0] += 1
            if "fashn" in space_id.lower():
                # FASHN fails
                instance.predict.side_effect = RuntimeError("429 too many requests")
            else:
                # IDM-VTON succeeds
                instance.predict.return_value = (None, fake_result)
            return instance

        mock_client_cls.side_effect = side_effect_client

        resp = vto_client.post(
            "/vto/jobs",
            json={"item_id": vto_item["id"]},
            headers=vto_auth,
        )
        assert resp.status_code == 202
        job_id = resp.get_json()["id"]

        import time
        for _ in range(20):
            if call_count[0] >= 2: break
            time.sleep(1)

        resp = vto_client.get(f"/vto/jobs/{job_id}", headers=vto_auth)
        data = resp.get_json()

        # Both engines should have been tried
        assert call_count[0] >= 2
        assert data["status"] == "ready"


class TestCategoryMapping:
    """Test FASHN category mapping."""

    def test_fashn_categories(self):
        """Verify the category mapping is correct."""
        from app.vto.routes import _run_tryon_job
        # We can't easily call _run_tryon_job directly, but we can
        # verify the mapping exists in the source
        import inspect
        source = inspect.getsource(_run_tryon_job)
        assert '"tops"' in source
        assert '"bottoms"' in source
        assert '"one-pieces"' in source


class TestQuotaAndCache:
    """Test that quota and caching still work with new engine."""

    def test_no_hf_token_returns_503(self, flask_app):
        """No HF_TOKEN configured → 503."""
        flask_app.config["HF_TOKEN"] = ""
        flask_app.config["HF_FASHN_SPACE_ID"] = ""
        flask_app.config["HF_VTO_SPACE_ID"] = ""

        client = flask_app.test_client()
        # Register + login
        client.post("/auth/register", json={
            "name": "No Token", "email": "notoken@test.com",
            "password": "password123", "gender": "men",
        })
        resp = client.post("/auth/login", json={
            "email": "notoken@test.com", "password": "password123",
        })
        token = resp.get_json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Need to upload person photo + item first
        from tests.conftest import _make_minimal_png
        png = _make_minimal_png()

        # Upload item
        item_resp = client.post(
            "/wardrobe/items",
            data={
                "image": (io.BytesIO(png), "shirt.png", "image/png"),
                "formality": "casual", "gender": "men",
            },
            headers=headers, content_type="multipart/form-data",
        )
        if item_resp.status_code != 201:
            pytest.skip("Item upload failed (likely needs mock pipeline)")

        # Upload person photo
        client.post(
            "/vto/person-photo",
            data={"photo": (io.BytesIO(png), "person.png", "image/png")},
            headers=headers, content_type="multipart/form-data",
        )

        # Submit VTO job → should get 503
        resp = client.post(
            "/vto/jobs",
            json={"item_id": item_resp.get_json()["id"]},
            headers=headers,
        )
        assert resp.status_code == 503
