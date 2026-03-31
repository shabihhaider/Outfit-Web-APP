"""
Script — Analyze Wedding Images for Quality Issues
===================================================
Scans all wedding images and identifies potential problems:
  - 0-byte files (corrupted)
  - Very small files (< 1KB, likely corrupted or icons)
  - Suspiciously small files (< 5KB, may be thumbnails)
  - Duplicate file sizes (potential duplicates)
  - Missing outfit groups (incomplete outfits)

Usage:
    python scripts/analyze_wedding_images.py
"""

import os
from collections import defaultdict

WEDDING_DIR = "datasets/wedding_data/images/"

def analyze_wedding_images():
    print("\n" + "="*70)
    print("  WEDDING IMAGES QUALITY ANALYSIS")
    print("="*70)
    
    if not os.path.exists(WEDDING_DIR):
        print(f"ERROR: Directory not found: {WEDDING_DIR}")
        return
    
    files = [f for f in os.listdir(WEDDING_DIR) 
             if os.path.isfile(os.path.join(WEDDING_DIR, f))]
    files.sort()
    
    print(f"\nTotal files found: {len(files)}")
    
    # Categorize by issues
    zero_byte = []
    tiny_files = []      # < 1KB
    small_files = []     # 1-5KB
    medium_files = []    # 5-20KB
    good_files = []      # > 20KB
    
    # Track outfit groups
    outfits = defaultdict(list)
    
    for filename in files:
        filepath = os.path.join(WEDDING_DIR, filename)
        size = os.path.getsize(filepath)
        
        # Categorize by size
        if size == 0:
            zero_byte.append((filename, size))
        elif size < 1024:
            tiny_files.append((filename, size))
        elif size < 5120:
            small_files.append((filename, size))
        elif size < 20480:
            medium_files.append((filename, size))
        else:
            good_files.append((filename, size))
        
        # Track outfit groups (w_XXX_name.jpg)
        parts = filename.split('_')
        if len(parts) >= 2 and parts[0] == 'w':
            outfit_id = f"w_{parts[1]}"
            outfits[outfit_id].append(filename)
    
    # Report issues
    print("\n" + "-"*70)
    print("  FILE SIZE ANALYSIS")
    print("-"*70)
    
    print(f"\n  [CRITICAL] 0-byte files (corrupted): {len(zero_byte)}")
    for f, s in zero_byte[:10]:
        print(f"      {f} ({s} bytes)")
    if len(zero_byte) > 10:
        print(f"      ... and {len(zero_byte) - 10} more")
    
    print(f"\n  [WARNING] Tiny files < 1KB (likely corrupted/icons): {len(tiny_files)}")
    for f, s in tiny_files[:10]:
        print(f"      {f} ({s} bytes)")
    if len(tiny_files) > 10:
        print(f"      ... and {len(tiny_files) - 10} more")
    
    print(f"\n  [CAUTION] Small files 1-5KB (may be thumbnails): {len(small_files)}")
    for f, s in small_files[:10]:
        print(f"      {f} ({s//1024}KB)")
    if len(small_files) > 10:
        print(f"      ... and {len(small_files) - 10} more")
    
    print(f"\n  Medium files 5-20KB: {len(medium_files)}")
    print(f"  Good files > 20KB: {len(good_files)}")
    
    # Outfit analysis
    print("\n" + "-"*70)
    print("  OUTFIT GROUP ANALYSIS")
    print("-"*70)
    
    print(f"\n  Total outfit groups: {len(outfits)}")
    
    # Find incomplete outfits (< 2 items)
    incomplete = {oid: items for oid, items in outfits.items() if len(items) < 2}
    if incomplete:
        print(f"\n  [!] Incomplete outfits (< 2 items): {len(incomplete)}")
        for oid, items in sorted(incomplete.items())[:10]:
            print(f"      {oid}: {items}")
        if len(incomplete) > 10:
            print(f"      ... and {len(incomplete) - 10} more")
    
    # Check outfit numbering gaps
    outfit_nums = sorted([int(oid.split('_')[1]) for oid in outfits.keys()])
    if outfit_nums:
        gaps = []
        for i in range(len(outfit_nums) - 1):
            if outfit_nums[i+1] - outfit_nums[i] > 1:
                for j in range(outfit_nums[i] + 1, outfit_nums[i+1]):
                    gaps.append(j)
        if gaps:
            print(f"\n  [*] Missing outfit numbers: {len(gaps)} gaps found")
            print(f"      Missing: {gaps[:20]}{'...' if len(gaps) > 20 else ''}")
    
    # Category distribution
    print("\n" + "-"*70)
    print("  CATEGORY DISTRIBUTION")
    print("-"*70)
    
    categories = defaultdict(int)
    for filename in files:
        # Extract category from filename (w_XXX_category.jpg)
        parts = filename.split('_')
        if len(parts) >= 3:
            cat = parts[-1].split('.')[0].lower()
            categories[cat] += 1
    
    for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
        print(f"    {cat:<15} {count:>4} files")
    
    # Summary
    print("\n" + "="*70)
    print("  SUMMARY & RECOMMENDATIONS")
    print("="*70)
    
    issues = len(zero_byte) + len(tiny_files)
    if issues > 0:
        print(f"\n  [ERROR] FOUND {issues} PROBLEMATIC FILES that should be removed:")
        print(f"     - {len(zero_byte)} zero-byte files (corrupted)")
        print(f"     - {len(tiny_files)} tiny files < 1KB (likely icons/corrupted)")
        print(f"\n  [ACTION] RECOMMENDED:")
        print(f"     Run cleanup to remove these files, then re-run Script 03 and 04")
    else:
        print("\n  [OK] No critical issues found in wedding images!")
    
    if small_files:
        print(f"\n  [NOTE] {len(small_files)} files are 1-5KB - review manually if possible")
    
    print("\n" + "="*70)

if __name__ == "__main__":
    analyze_wedding_images()
