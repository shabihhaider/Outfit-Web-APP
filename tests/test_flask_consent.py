"""
tests/test_flask_consent.py
Tests for consent, privacy, password change, and account deletion endpoints.
"""

from __future__ import annotations


class TestConsent:
    def test_get_consent_defaults(self, client, auth_headers):
        resp = client.get("/auth/consent", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert "consents" in data
        assert "data_training" in data["consents"]
        assert "analytics" in data["consents"]
        assert data["consents"]["data_training"]["granted"] is False
        assert data["consents"]["analytics"]["granted"] is False

    def test_grant_consent(self, client, auth_headers):
        resp = client.patch(
            "/auth/consent",
            json={"data_training": True},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert "data_training" in resp.get_json()["updated"]

        # Verify it persisted
        resp2 = client.get("/auth/consent", headers=auth_headers)
        assert resp2.get_json()["consents"]["data_training"]["granted"] is True

    def test_revoke_consent(self, client, auth_headers):
        client.patch("/auth/consent", json={"data_training": True}, headers=auth_headers)
        resp = client.patch(
            "/auth/consent",
            json={"data_training": False},
            headers=auth_headers,
        )
        assert resp.status_code == 200

        resp2 = client.get("/auth/consent", headers=auth_headers)
        assert resp2.get_json()["consents"]["data_training"]["granted"] is False

    def test_consent_invalid_type(self, client, auth_headers):
        resp = client.patch(
            "/auth/consent",
            json={"invalid_type": True},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_consent_invalid_value(self, client, auth_headers):
        resp = client.patch(
            "/auth/consent",
            json={"data_training": "yes"},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_consent_requires_auth(self, client):
        resp = client.get("/auth/consent")
        assert resp.status_code == 401


class TestPrivacySummary:
    def test_privacy_summary(self, client, auth_headers):
        resp = client.get("/auth/privacy-summary", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert "data_summary" in data
        assert "wardrobe_items" in data["data_summary"]
        assert "email" in data


class TestDataExport:
    def test_data_export(self, client, auth_headers):
        resp = client.get("/auth/data-export", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert "user" in data
        assert "wardrobe_items" in data
        assert "consents" in data


class TestChangePassword:
    def test_change_password_success(self, client, auth_headers):
        resp = client.post(
            "/auth/change-password",
            json={"current_password": "password123", "new_password": "newpass1234"},
            headers=auth_headers,
        )
        assert resp.status_code == 200

        # Can login with new password
        resp2 = client.post(
            "/auth/login",
            json={"email": "test@example.com", "password": "newpass1234"},
        )
        assert resp2.status_code == 200

    def test_change_password_wrong_current(self, client, auth_headers):
        resp = client.post(
            "/auth/change-password",
            json={"current_password": "wrongpass", "new_password": "newpass1234"},
            headers=auth_headers,
        )
        assert resp.status_code == 401

    def test_change_password_too_short(self, client, auth_headers):
        resp = client.post(
            "/auth/change-password",
            json={"current_password": "password123", "new_password": "short"},
            headers=auth_headers,
        )
        assert resp.status_code == 422


class TestDeleteAccount:
    def test_delete_account_success(self, client, auth_headers):
        resp = client.delete(
            "/auth/account",
            json={"password": "password123"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert "deleted" in resp.get_json()["message"].lower()

        # Can no longer login
        resp2 = client.post(
            "/auth/login",
            json={"email": "test@example.com", "password": "password123"},
        )
        assert resp2.status_code == 401

    def test_delete_account_wrong_password(self, client, auth_headers):
        resp = client.delete(
            "/auth/account",
            json={"password": "wrongpass"},
            headers=auth_headers,
        )
        assert resp.status_code == 401

    def test_delete_account_no_password(self, client, auth_headers):
        resp = client.delete(
            "/auth/account",
            json={},
            headers=auth_headers,
        )
        assert resp.status_code == 422
