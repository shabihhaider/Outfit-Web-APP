"""
Smoke test: verify FASHN VTON v1.5 HF Space API contract.
Run: python tests/test_fashn_smoke.py

Uses real images from uploads/ to call the FASHN Space directly.
No Flask, no database — just the raw gradio_client call.
"""
import os
import sys
import time
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PERSON_IMG = "uploads/person_8_48248fdf152f48809f7a0d3d74f3b044.jpg"
GARMENT_IMG = "uploads/6_2c8525b59a7e4c02852c6336def0e232.png"

HF_TOKEN = os.environ.get("HF_TOKEN", "")
FASHN_SPACE = os.environ.get("HF_FASHN_SPACE_ID", "fashn-ai/fashn-vton-1.5")


def main():
    # --- Preflight checks ---
    for label, path in [("Person", PERSON_IMG), ("Garment", GARMENT_IMG)]:
        if not os.path.exists(path):
            print(f"FAIL: {label} image not found at {path}")
            print("  Update PERSON_IMG / GARMENT_IMG paths in this script.")
            sys.exit(1)
        size_kb = os.path.getsize(path) / 1024
        print(f"  {label}: {path} ({size_kb:.0f} KB)")

    print(f"\nSpace:  {FASHN_SPACE}")
    print(f"Token:  {'set (' + HF_TOKEN[:8] + '...)' if HF_TOKEN else 'NOT SET (will use anonymous quota)'}")

    # --- Call FASHN Space ---
    from gradio_client import Client, handle_file

    print(f"\n[1/3] Connecting to {FASHN_SPACE}...")
    t0 = time.time()
    client = Client(FASHN_SPACE, token=HF_TOKEN or None)
    print(f"  Connected in {time.time() - t0:.1f}s")

    print("[2/3] Calling predict() — this may take 30-90s on ZeroGPU cold start...")
    t1 = time.time()
    try:
        result = client.predict(
            person_image=handle_file(PERSON_IMG),
            garment_image=handle_file(GARMENT_IMG),
            category="tops",
            garment_photo_type="flat-lay",
            num_timesteps=50,
            guidance_scale=1.5,
            seed=42,
            segmentation_free=True,
            api_name="/try_on",
        )
    except Exception as exc:
        elapsed = time.time() - t1
        print(f"\n  FAILED after {elapsed:.1f}s: {exc}")
        print("\n  If 'too many requests' / '429': ZeroGPU quota exhausted, try later.")
        print("  If 'queue is full': Space is busy, retry in a few minutes.")
        sys.exit(1)

    elapsed = time.time() - t1
    print(f"  predict() returned in {elapsed:.1f}s")

    # --- Inspect result ---
    print(f"\n[3/3] Result inspection:")
    print(f"  type(result) = {type(result).__name__}")
    print(f"  repr(result) = {repr(result)[:200]}")

    # Extract file path from result (API returns dict with 'path' key)
    import shutil
    out_path = "uploads/fashn_smoke_test_result.png"

    if isinstance(result, dict):
        file_path = result.get("path") or result.get("url", "")
        print(f"  Result dict keys: {list(result.keys())}")
        if file_path and os.path.exists(file_path):
            size_kb = os.path.getsize(file_path) / 1024
            print(f"  Result file: {file_path} ({size_kb:.0f} KB)")
            shutil.copy(file_path, out_path)
            print(f"  Copied to: {out_path}")
            print("\n  SUCCESS — open that file to visually verify the try-on result.")
        elif file_path and file_path.startswith(("http://", "https://")):
            print(f"  Result URL: {file_path}")
            import requests
            resp = requests.get(file_path, timeout=30)
            with open(out_path, "wb") as f:
                f.write(resp.content)
            print(f"  Downloaded to: {out_path}")
            print("\n  SUCCESS — open that file to verify.")
        else:
            print(f"  WARNING: Could not resolve file from dict: {result}")
    elif isinstance(result, str) and os.path.exists(result):
        size_kb = os.path.getsize(result) / 1024
        print(f"  Result is a file path: {result} ({size_kb:.0f} KB)")
        shutil.copy(result, out_path)
        print(f"  Copied to: {out_path}")
        print("\n  SUCCESS — open that file to verify.")
    else:
        print(f"  Unexpected result type: {type(result).__name__}")
        print(f"  Value: {repr(result)[:300]}")

    print(f"\nTotal wall time: {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
