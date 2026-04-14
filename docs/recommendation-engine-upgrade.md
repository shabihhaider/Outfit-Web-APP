# Recommendation Engine Upgrade Plan

## Current System Assessment

### Architecture (3-Gate Pipeline)
```
Wardrobe → Gender Filter → Gate 2 (Occasion) → Gate 1 (Hard Rules) → Gate 3 (Scoring) → Top N
```

### What Works Well
- **Model 2 (Polyvore MLP):** Real learned compatibility from human-curated outfits (45% weight)
- **Hard Rules:** 5 structural rules + 11 blocked sub-category pairs prevent invalid combos
- **Color Harmony:** Itten color theory (complementary, analogous, etc.) — real fashion theory
- **Weather Comfort:** ASHRAE CLO thermal scoring — functional fashion logic
- **CLIP Sub-categories:** 34 sub-categories across 6 coarse categories with South Asian coverage (kurta, shalwar, sherwani, kameez, chappal, anarkali)
- **Filtering and scoring are already separated** — Gate 1 (hard_rules.py) and Gate 3 (scorer.py) are independent modules

### What's Missing
1. **`style_intelligence.py` is dead code** — 18 synergy bonuses (kurta+shalwar, polo+chinos, etc.) exist but are never imported into the scoring pipeline
2. **Cross-cultural mismatches pass through** — polo+shalwar, tshirt+shalwar are structurally valid (top+bottom) but fashion-incoherent
3. **Model 2 is Western-biased** — trained on Polyvore (Western fashion). Produces unreliable OOD scores for South Asian combos
4. **Score display lacks context** — "72% Match" is a weighted average, not a probability. Absolute number is not meaningful to users

---

## Upgrade Plan

### 1. Block Embarrassing Combinations

Add to `BLOCKED_SUBCATEGORY_PAIRS` in `engine/hard_rules.py`.

**Rule: if a normal person would say "what is this?" → block it.**

**Pakistan-specific:**
| Pair | Reason |
|------|--------|
| polo_shirt + shalwar | Western casual + Eastern traditional mismatch |
| casual_tshirt + shalwar | Western casual + Eastern traditional mismatch |
| hoodie + shalwar | Streetwear + Eastern traditional mismatch |

**Global (additions to existing 11 pairs):**
| Pair | Reason |
|------|--------|
| blazer + joggers | Formal outerwear + athleisure clash |

Note: `sherwani + jeans`, `hoodie + formal_shoes`, and `sherwani + sneakers` are already blocked.

**File:** `engine/hard_rules.py` — add 4 new entries to `BLOCKED_SUBCATEGORY_PAIRS`

### 2. Integrate Style Intelligence into Scoring

Activate `engine/style_intelligence.py` as the 5th scoring component.

**Current weights:**
```
M2=0.45, Color=0.25, Weather=0.15, Cohesion=0.15
```

**New weights:**
```
M2=0.35, Color=0.20, Weather=0.15, Cohesion=0.10, Synergy=0.20
```

Synergy score range: 0.5 (no synergy detected) to 1.0 (strong known pairing). Items without CLIP sub-categories score 0.5 (neutral — no penalty, no boost).

**File:** `engine/scorer.py` — import `score_outfit_intelligence`, add to `WEIGHTS`, include in `final_score` formula

### 3. Add High-Value Synergy Pairs

Add to `SYNERGY_BONUSES` in `engine/style_intelligence.py`. Focus on high-frequency combos only.

**Pakistan:**
| Pair | Bonus | Note |
|------|-------|------|
| kurta + jeans | 0.30 | Common fusion — widely accepted |
| kurta + chinos | 0.30 | Smart fusion |
| kameez + jeans | 0.25 | Women's fusion |

**Global:**
| Pair | Bonus | Note |
|------|-------|------|
| blazer + jeans | 0.35 | Smart casual staple |
| blazer + chinos | 0.40 | Business casual |
| hoodie + joggers | 0.35 | Athleisure core |
| casual_tshirt + shorts | 0.30 | Summer casual |
| blazer + casual_tshirt | 0.30 | Modern smart casual |

**Already present (no changes):** kurta+shalwar (0.50), kameez+shalwar (0.50), polo+chinos (0.45), formal_shirt+dress_trousers (0.50), sherwani+shalwar (0.50)

**File:** `engine/style_intelligence.py` — add 8 new entries to `SYNERGY_BONUSES`

### 4. Allow Controlled Mixing (Don't Over-Restrict)

The system should NOT blindly block all casual+formal mixing. Modern fashion allows intentional mixing:

**Already allowed (no changes needed):**
- blazer + tshirt → passes hard rules, synergy bonus added (0.30)
- kurta + sneakers → passes hard rules, no blocked pair
- kurta + jeans → passes hard rules, synergy bonus added (0.30)

**Blocked (correctly):**
- hoodie + formal_shoes → existing blocked pair
- hoodie + dress_trousers → existing blocked pair
- sherwani + sneakers → existing blocked pair

Rule 5 (no casual+formal mixing) only blocks when ALL items have strict formality tags. Items tagged "both" (kurta, chinos, loafers, boots, coat) act as bridges — this already enables smart casual combinations without code changes.

### 5. Improve Score Display (Simple UX Win)

Replace raw percentage with human-readable labels alongside the number:

| Score Range | Label | Badge Color |
|-------------|-------|-------------|
| ≥ 75% | Great Match | Green |
| ≥ 55% | Good Match | Green |
| ≥ 40% | Fair Match | Amber |
| < 40% | Weak Match | Red |

Add tooltip: "Score based on style compatibility, color harmony, weather comfort, and visual cohesion"

**Files:** `frontend/src/components/recommendations/OutfitCard.jsx`, `frontend/src/pages/OutfitEditorPage.jsx`

---

## What We Are NOT Doing (and Why)

| Proposal | Why Skipped |
|----------|-------------|
| Amazon-level 10-layer pipeline | Over-architected for current scale. Current 3-gate pipeline is correct. |
| JSON rules engine | Python dicts (SYNERGY_BONUSES, BLOCKED_PAIRS) ARE the rules engine. JSON adds indirection with zero capability gain. |
| Region/culture tag per item | Requires DB migration, re-upload of all items, new UI. Blocked pairs + synergy bonuses achieve the same result at 5% of the cost. |
| Style families 5×5 matrix | Verbose encoding of what blocked pairs + synergy bonuses already express. |
| Formality as 0–4 scale | Current casual/formal/both works. Existing Rule 5 + blocked pairs handle all the team's examples. |
| CLIP as scoring signal | CLIP labels garments but cannot reason about outfit grammar. Synergy bonuses handle that concretely. |
| Train custom South Asian model | No dataset exists yet. Synergy+blocked-pairs is the 80/20 solution. |
| Explainability layer | Already exists: WhyThisOutfit.jsx shows Style/Color/Weather/Cohesion breakdown. |

---

## Implementation Checklist

- [x] Add 3 blocked pairs to `engine/hard_rules.py` (polo+shalwar, tshirt+shalwar, hoodie+shalwar)
- [x] Add 8 synergy pairs to `engine/style_intelligence.py`
- [x] Integrate `style_intelligence.py` into `engine/scorer.py` (5th weight)
- [x] Rebalance scoring weights (M2=0.35, Color=0.20, Weather=0.15, Cohesion=0.10, Synergy=0.20)
- [x] Add `sub_category` field to `WardrobeItem` model + pass through `item_db_to_engine()`
- [x] Add `synergy_score` field to `OutfitCandidate` model + all 3 API response formatters
- [x] Add score labels (Great/Good/Fair/Weak Match) in OutfitCard + OutfitEditorPage
- [x] Add Synergy bar to WhyThisOutfit breakdown + OutfitEditorPage score stats
- [x] Add synergy context to `buildWhyText()` in formatters.js
- [x] Add 4 new hard rule tests (polo+shalwar blocked, tshirt+shalwar blocked, hoodie+shalwar blocked, kurta+shalwar allowed)
- [x] Update 3 scorer tests for new 5-component weight formula
- [x] Run preflight, verify all tests pass

## Verification

- `pytest tests/` — all existing + new tests pass
- Manual test: kurta+shalwar wardrobe → synergy boosts score visibly
- Manual test: polo+shalwar → blocked by hard rules, never recommended
- Manual test: blazer+tshirt+jeans → allowed, gets smart casual synergy bonus
- Frontend: score shows "Good Match" label + tooltip on hover
