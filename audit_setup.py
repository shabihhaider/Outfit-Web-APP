import requests
import json
import os

BASE_URL = "http://localhost:5000"
EMAIL = "audit@test.com"
PASSWORD = "password123"

def setup():
    # Login
    resp = requests.post(f"{BASE_URL}/auth/login", json={"email": EMAIL, "password": PASSWORD})
    if resp.status_code != 200:
        print(f"Login failed: {resp.text}")
        return
    token = resp.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}
    print(f"Logged in. Token: {token[:10]}...")

    # Upload specialized items
    items = [
        {"file": r"C:\Users\shabi\.gemini\antigravity\brain\c783aafb-ae1d-45bf-a35a-f0f033a7bfe9\audit_dress_women_1774764828932.png", "category": "dress", "formality": "casual", "gender": "women"},
        {"file": r"C:\Users\shabi\.gemini\antigravity\brain\c783aafb-ae1d-45bf-a35a-f0f033a7bfe9\audit_formal_shirt_1774764856628.png", "category": "top", "formality": "formal", "gender": "men"}
    ]

    for item in items:
        with open(item["file"], "rb") as f:
            r = requests.post(
                f"{BASE_URL}/wardrobe/items",
                headers=headers,
                files={"image": f},
                data={"formality": item["formality"], "gender": item["gender"]}
            )
            print(f"Upload {item['file']}: {r.status_code} {r.text}")

if __name__ == "__main__":
    setup()
