import os
import hashlib
import re
from collections import defaultdict

# --- CONFIGURATION ---
# Folder containing your wedding images
FOLDER = r"e:\Final\datasets\wedding_data\images" 

# Set to False to actually delete files
DRY_RUN = True 

# Regex for naming convention: w_XXX_type.jpg
NAME_PATTERN = re.compile(r"^w_\d{3}_(top|bottom|dress|shoes|outwear)\.(jpg|jpeg|png)$", re.IGNORECASE)

def get_file_hash(filepath, chunk_size=8192):
    """Calculate MD5 hash of a file in chunks."""
    hasher = hashlib.md5()
    with open(filepath, "rb") as f:
        while chunk := f.read(chunk_size):
            hasher.update(chunk)
    return hasher.hexdigest()

def clean_wedding_data():
    if not os.path.exists(FOLDER):
        print(f"[ERROR] Folder not found: {FOLDER}")
        return

    print(f"--- Starting Wedding Data Cleaning ---")
    print(f"Directory: {FOLDER}")
    print(f"Mode: {'DRY RUN (No changes)' if DRY_RUN else 'LIVE (Files will be deleted)'}\n")

    files = [f for f in os.listdir(FOLDER) if os.path.isfile(os.path.join(FOLDER, f))]
    
    seen_hashes = {} # hash -> original_filename
    outfits = defaultdict(list) # outfit_id -> [filenames]
    
    removed = 0
    invalid_names = []

    # 1. Hashing and Naming Validation
    for filename in files:
        filepath = os.path.join(FOLDER, filename)
        
        # Check Naming Convention
        if not NAME_PATTERN.match(filename):
            invalid_names.append(filename)
        
        # Check Duplicates
        file_hash = get_file_hash(filepath)
        if file_hash in seen_hashes:
            print(f"[DUPLICATE] '{filename}' matches '{seen_hashes[file_hash]}'")
            if not DRY_RUN:
                os.remove(filepath)
            removed += 1
        else:
            seen_hashes[file_hash] = filename
            # Track outfits for integrity check
            match = re.match(r"^w_(\d{3})_", filename)
            if match:
                outfit_id = match.group(1)
                outfits[outfit_id].append(filename)

    # 2. Output Summary
    print(f"\n--- Cleaning Summary ---")
    print(f"Total files scanned: {len(files)}")
    print(f"Duplicates found: {removed}")
    
    if invalid_names:
        print(f"\n[WARNING] Found {len(invalid_names)} files violating naming convention:")
        for name in invalid_names[:5]: # Show first 5
            print(f"  - {name}")
        if len(invalid_names) > 5:
            print(f"  ... and {len(invalid_names)-5} more.")
            
    # 3. Outfit Integrity Check
    broken_outfits = [oid for oid, items in outfits.items() if len(items) < 2]
    if broken_outfits:
        print(f"\n[CRITICAL] Data Integrity Issue: {len(broken_outfits)} outfits have < 2 items:")
        for oid in broken_outfits[:5]:
            print(f"  - Outfit {oid}: {outfits[oid]}")
        print(f"Required by DATASET_GUIDE_v2.md: Minimum 2 items per outfit.")

    if DRY_RUN and (removed > 0 or broken_outfits or invalid_names):
        print(f"\n[ACTION] To apply changes and delete duplicates, set DRY_RUN = False in the script.")
    elif not DRY_RUN:
        print(f"\n[SUCCESS] Deletion completed. {removed} files removed.")

if __name__ == "__main__":
    clean_wedding_data()
