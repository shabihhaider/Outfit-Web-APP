"""
Script — Cleanup Problematic Wedding Images
===========================================
Deletes all identified problematic files:
  - 0-byte files (corrupted)
  - Files < 1KB (likely icons/placeholders)

Then re-runs:
  - Script 03 (create_wedding_json.py)
  - Script 04 (merge_datasets.py)

Usage:
    python scripts/cleanup_and_regenerate.py
"""

import os

# Configuration
WEDDING_DIR = "datasets/wedding_data/images/"

# Files to delete (identified from analysis)
FILES_TO_DELETE = [
    # Zero-byte files
    "w_003_outwear.jpg",
    
    # Tiny files < 1KB
    "w_010_shoes.jpg",
    "w_024_shoes.jpg",
    "w_032_shoes.jpg",
    "w_037_shoes.jpg",
    "w_040_shoes.jpg",
    "w_042_shoes.jpg",
    "w_048_shoes.jpg",
    "w_049_shoes.jpg",
    "w_074_outwear.jpg",
    "w_080_outwear.jpg",
    "w_081_outwear.jpg",
    "w_082_outwear.jpg",
    "w_083_outwear.jpg",
    "w_084_outwear.jpg",
    "w_085_outwear.jpg",
    "w_086_outwear.jpg",
    "w_087_outwear.jpg",
    "w_088_outwear.jpg",
    "w_089_outwear.jpg",
    "w_090_outwear.jpg",
    "w_091_outwear.jpg",
    "w_092_outwear.jpg",
    "w_093_outwear.jpg",
    "w_094_outwear.jpg",
    "w_095_outwear.jpg",
    "w_134_outwear.jpg",
    "w_136_outwear.jpg",
    "w_137_outwear.jpg",
    "w_138_outwear.jpg",
]

def main():
    print("\n" + "="*70)
    print("  CLEANUP: Deleting Problematic Wedding Images")
    print("="*70)
    
    if not os.path.exists(WEDDING_DIR):
        print(f"ERROR: Directory not found: {WEDDING_DIR}")
        return
    
    deleted = []
    not_found = []
    
    for filename in FILES_TO_DELETE:
        filepath = os.path.join(WEDDING_DIR, filename)
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
                deleted.append(filename)
                print(f"  [DELETED] {filename}")
            except Exception as e:
                print(f"  [ERROR] Failed to delete {filename}: {e}")
        else:
            not_found.append(filename)
            print(f"  [NOT FOUND] {filename}")
    
    print(f"\n  Summary:")
    print(f"    Deleted: {len(deleted)} files")
    print(f"    Not found: {len(not_found)} files")
    
    print("\n" + "="*70)
    print("  Now re-running Script 03 and 04 to regenerate dataset...")
    print("="*70 + "\n")
    
    # Re-run Script 03
    print("\n>>> Running Script 03: Create Wedding JSON")
    os.system("python scripts/03_create_wedding_json.py")
    
    # Re-run Script 04
    print("\n>>> Running Script 04: Merge Datasets")
    os.system("python scripts/04_merge_datasets.py")
    
    print("\n" + "="*70)
    print("  Cleanup and regeneration complete!")
    print("="*70)

if __name__ == "__main__":
    main()
