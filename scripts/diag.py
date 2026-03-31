import os, json

MODEL2_DIR = r"E:\Final\datasets\for_model2"
IMG_DIR = os.path.join(MODEL2_DIR, "images")
JSON_PATH = r"E:\Final\datasets\processed\final_dataset.json"
NEW_JSON_TRAIN = os.path.join(MODEL2_DIR, "metadata", "train_no_dup.json")
NEW_JSON_VALID = os.path.join(MODEL2_DIR, "metadata", "valid_no_dup.json")

POLYVORE_CATEGORY_MAP = {
    11: "top", 15: "top", 17: "top", 18: "top", 19: "top",
    21: "top", 104: "top", 252: "top", 272: "top", 273: "top",
    275: "top", 309: "top", 342: "top", 4454: "top", 4495: "top",
    4496: "top", 4497: "top", 4498: "top",
    7: "bottom", 8: "bottom", 9: "bottom", 10: "bottom",
    27: "bottom", 28: "bottom", 29: "bottom", 237: "bottom",
    238: "bottom", 239: "bottom", 240: "bottom", 241: "bottom",
    253: "bottom", 254: "bottom", 255: "bottom", 279: "bottom",
    280: "bottom", 287: "bottom", 288: "bottom", 310: "bottom",
    332: "bottom", 4452: "bottom", 4458: "bottom", 4459: "bottom",
    23: "outwear", 24: "outwear", 25: "outwear", 26: "outwear", 
    30: "outwear", 236: "outwear", 256: "outwear", 276: "outwear",
    277: "outwear", 4455: "outwear", 4456: "outwear", 4457: "outwear",
    281: "outwear",
    41: "shoes", 42: "shoes", 43: "shoes", 46: "shoes",
    47: "shoes", 48: "shoes", 49: "shoes", 50: "shoes",
    261: "shoes", 262: "shoes", 263: "shoes", 264: "shoes",
    265: "shoes", 266: "shoes", 267: "shoes", 268: "shoes",
    291: "shoes", 292: "shoes", 293: "shoes", 294: "shoes",
    295: "shoes", 296: "shoes", 297: "shoes", 298: "shoes",
    4464: "shoes", 4465: "shoes",
    3: "dress", 4: "dress", 5: "dress", 6: "dress",
    4516: "dress", 243: "dress", 244: "dress",
}

with open(JSON_PATH, "r", encoding="utf-8") as f:
    occasion_data = json.load(f)

item_lookup = {}
for meta_path in [NEW_JSON_TRAIN, NEW_JSON_VALID]:
    with open(meta_path, "r", encoding="utf-8") as f:
        meta_json = json.load(f)
    for outfit in meta_json:
        oid = outfit["set_id"]
        for item in outfit["items"]:
            idx = str(item["index"])
            cat_id = item.get("categoryid", -1)
            mapped_cat = POLYVORE_CATEGORY_MAP.get(cat_id, "unknown")
            item_lookup[f"{oid}_{idx}"] = {
                "image_path": os.path.join(IMG_DIR, mapped_cat, f"{oid}_{idx}.jpg"),
            }

existing = sum(1 for v in item_lookup.values() if os.path.exists(v['image_path']))
missing_samples = [v['image_path'] for v in item_lookup.values() if not os.path.exists(v['image_path'])][:5]
existing_samples = [v['image_path'] for v in item_lookup.values() if os.path.exists(v['image_path'])][:5]

print("=== DIAGNOSTIC ===")
print(f"Total items in lookup: {len(item_lookup)}")
print(f"Images that EXIST on disk: {existing}")
print(f"Images that are MISSING: {len(item_lookup) - existing}")
print("Sample MISSING:", missing_samples)
print("Sample EXISTING:", existing_samples)
