"""
tests/test_flask_auth.py
Unit tests for POST /auth/register, POST /auth/login, POST /auth/refresh.
"""

from __future__ import annotations

import pytest


# ─── Register ─────────────────────────────────────────────────────────────────

class TestRegister:
    def test_register_success(self, client):
        resp = client.post(
            "/auth/register",
            json={
                "name": "Shabih",
                "email": "shabih@uet.edu.pk",
                "password": "securepass",
                "gender": "men",
            },
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["message"] == "Account created."
        assert "user_id" in data

    def test_register_duplicate_email(self, client):
        payload = {
            "name": "Shabih",
            "email": "dup@example.com",
            "password": "securepass",
            "gender": "men",
        }
        client.post("/auth/register", json=payload)
        resp = client.post("/auth/register", json=payload)
        assert resp.status_code == 400
        assert "already exists" in resp.get_json()["error"].lower()

    def test_register_missing_field(self, client):
        resp = client.post(
            "/auth/register",
            json={"name": "Shabih", "email": "x@x.com", "password": "pass1234"},
            # gender is missing
        )
        assert resp.status_code == 422

    def test_register_short_password(self, client):
        resp = client.post(
            "/auth/register",
            json={
                "name": "Shabih",
                "email": "short@x.com",
                "password": "abc",
                "gender": "women",
            },
        )
        assert resp.status_code == 422
        assert "8 characters" in resp.get_json()["error"]

    def test_register_invalid_gender(self, client):
        resp = client.post(
            "/auth/register",
            json={
                "name": "Shabih",
                "email": "g@x.com",
                "password": "password123",
                "gender": "other",
            },
        )
        assert resp.status_code == 422

    def test_register_invalid_email(self, client):
        resp = client.post(
            "/auth/register",
            json={
                "name": "Shabih",
                "email": "notanemail",
                "password": "password123",
                "gender": "unisex",
            },
        )
        assert resp.status_code == 422

    def test_register_all_gender_values(self, client):
        for i, gender in enumerate(["men", "women", "unisex"]):
            resp = client.post(
                "/auth/register",
                json={
                    "name": f"User{i}",
                    "email": f"user{i}@example.com",
                    "password": "password123",
                    "gender": gender,
                },
            )
            assert resp.status_code == 201, f"Failed for gender={gender}"


# ─── Login ────────────────────────────────────────────────────────────────────

class TestLogin:
    def _register(self, client):
        client.post(
            "/auth/register",
            json={
                "name": "Login Test",
                "email": "login@example.com",
                "password": "mypassword",
                "gender": "women",
            },
        )

    def test_login_success(self, client):
        self._register(client)
        resp = client.post(
            "/auth/login",
            json={"email": "login@example.com", "password": "mypassword"},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "access_token" in data
        assert data["name"] == "Login Test"
        assert data["gender"] == "women"

    def test_login_wrong_password(self, client):
        self._register(client)
        resp = client.post(
            "/auth/login",
            json={"email": "login@example.com", "password": "wrongpassword"},
        )
        assert resp.status_code == 401

    def test_login_unknown_email(self, client):
        resp = client.post(
            "/auth/login",
            json={"email": "nobody@example.com", "password": "whatever"},
        )
        assert resp.status_code == 401

    def test_login_missing_fields(self, client):
        resp = client.post("/auth/login", json={"email": "x@x.com"})
        assert resp.status_code == 422


# ─── Refresh ──────────────────────────────────────────────────────────────────

class TestRefresh:
    def test_refresh_success(self, client, auth_headers):
        resp = client.post("/auth/refresh", headers=auth_headers)
        assert resp.status_code == 200
        assert "access_token" in resp.get_json()

    def test_refresh_without_token(self, client):
        resp = client.post("/auth/refresh")
        assert resp.status_code == 401
