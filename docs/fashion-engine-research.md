# Fashion Engine Research — OutfitAI

**Date:** 2026-04-18
**Scope:** Deep analysis of the recommendation engine vs. real-world fashion rules.
Combines full codebase audit + fashion domain research (GQ, Vogue, Esquire, SA fashion authorities).

---

## 1. CRITICAL FINDING: Rule 5 Kills Valid Outfits

### The Problem

Hard Rule 5 in `engine/hard_rules.py` (line 96-103) blanket-blocks ANY outfit where a `casual`-tagged item and a `formal`-tagged item coexist:

```python
# Rule 5: formal and casual items cannot be mixed
strict_formalities = {
    item.formality for item in outfit_items
    if item.formality != Formality.BOTH
}
if Formality.CASUAL in strict_formalities and Formality.FORMAL in strict_formalities:
    return False
```

This means these outfits are **hard-rejected** (never scored, never recommended):

| Outfit | Why it's valid | Rule 5 verdict |
|--------|---------------|----------------|
| Formal shirt + jeans + sneakers | THE classic smart casual — GQ calls it "the most versatile look in menswear" | BLOCKED (formal + casual) |
| Blazer + t-shirt + jeans | Modern smart casual, universally endorsed | BLOCKED (formal + casual) |
| Dress shirt + chinos + sneakers | Business casual staple | BLOCKED (formal + casual) |
| Kurta (both) + jeans (casual) + formal shoes | Valid SA fusion — kurta is "both" but formal_shoes is "formal" | BLOCKED (formal + casual) |
| Polo (casual) + dress trousers (formal) | Classic prep look | BLOCKED (casual + formal) |

**Impact:** Rule 5 eliminates the entire "smart casual" aesthetic — the most common dress code in modern fashion. The engine can ONLY recommend outfits where all items are the same formality (all casual, all formal, or everything tagged "both").

### The Root Cause

Rule 5 was designed to prevent absurd combos like hoodie + formal trousers. But that's already handled by **Rule 6** (blocked sub-category pairs). Rule 5 is a blunt instrument that catches valid combos as collateral damage.

### The Fix

**Remove Rule 5.** Rule 6 (blocked pairs) handles genuinely bad formality clashes. The scoring system (Model 2, synergy, cohesion) handles nuance — it rewards good cross-formality combos and penalizes bad ones.

---

## 2. BLOCKED PAIRS AUDIT

### Currently blocked (14 pairs) — Verdict:

| Pair | Verdict | Reasoning |
|------|---------|-----------|
| blazer + leggings | **KEEP** | Formality mismatch, no fashion authority endorses |
| blazer + sneakers | **REMOVE** | White sneakers + blazer is now a mainstream smart casual look (GQ 2023+). Keep scoring low via synergy, don't hard-block |
| sherwani + jeans | **KEEP** | Sherwani is highest SA formality — jeans destroy it |
| sherwani + sneakers | **KEEP** | Same — sherwani demands formal/traditional footwear |
| formal_shirt + shorts | **KEEP** | Dress shirt + shorts is universally considered incorrect |
| hoodie + dress_trousers | **KEEP** | Skips 2+ formality levels — no coherent outfit center |
| hoodie + formal_shoes | **KEEP** | Same — extreme formality mismatch |
| hoodie + heels | **KEEP** | Same |
| heels + leggings | **REVIEW** | Actually common in women's casual — consider removing |
| chappal + blazer | **KEEP** | Cultural + formality mismatch |
| chappal + sherwani | **KEEP** | Chappal is too casual for sherwani's formality |
| polo + shalwar | **KEEP** | Western casual top + SA traditional bottom — incoherent |
| tshirt + shalwar | **KEEP** | Same |
| hoodie + shalwar | **KEEP** | Same |

### Pairs to ADD (from fashion research):

| Pair | Reasoning |
|------|-----------|
| sherwani + shorts | Sherwani is SA black-tie equivalent — shorts are absurd |
| sherwani + leggings | Same reasoning |
| sherwani + casual_tshirt | T-shirt under sherwani — costume, not fashion |
| sherwani + hoodie | Extreme cultural/formality clash |
| hoodie_jacket + shalwar | Same logic as hoodie + shalwar |
| hoodie_jacket + dress_trousers | Same logic as hoodie + dress trousers |
| hoodie_jacket + formal_shoes | Same logic as hoodie + formal shoes |

### Pair to REMOVE:

| Pair | Reasoning |
|------|-----------|
| blazer + sneakers | Modern smart casual staple. Clean white sneakers + blazer is GQ/Esquire endorsed since 2018. Let scoring handle it — synergy bonus for blazer+clean_sneakers, no bonus for blazer+running_shoes |

---

## 3. SYNERGY BONUSES AUDIT

### Current bonuses (22 pairs) — all validated as correct:

All existing synergy bonuses align with fashion consensus. No removals needed.

### Bonuses to ADD (from fashion research):

| Pair | Bonus | Category |
|------|-------|----------|
| blazer + casual_tshirt | 0.30 | Already exists ✓ |
| blazer + sneakers | 0.25 | Smart casual modern (after removing from blocked list) |
| formal_shirt + chinos | 0.40 | Business casual staple |
| formal_shirt + loafers | 0.35 | Classic formal-casual bridge |
| polo_shirt + jeans | 0.35 | Already exists ✓ |
| casual_tshirt + chinos | 0.25 | Clean casual |
| casual_tshirt + loafers | 0.20 | Elevated casual |
| polo_shirt + loafers | 0.35 | Preppy classic |
| polo_shirt + dress_trousers | 0.35 | Business casual |
| kurta + boots | 0.25 | Modern SA fusion |
| kameez + chinos | 0.25 | SA fusion |
| kameez + jeans | Already 0.25 ✓ | |
| formal_shirt + sneakers | 0.20 | Modern smart casual (clean sneakers only) |
| formal_shirt + boots | 0.30 | Classic versatile |
| waistcoat + formal_shirt | 0.40 | Three-piece foundation |
| waistcoat + dress_trousers | 0.35 | Formal layering |
| cardigan + formal_shirt | 0.30 | Smart casual layering |
| cardigan + casual_tshirt | 0.25 | Casual layering |
| coat + formal_shirt | 0.30 | Winter formal |
| coat + dress_trousers | 0.30 | Winter formal |

### Net new pairs to add: ~15 (excluding already existing)

---

## 4. OCCASION FILTER — CONFIRMED CORRECT

The current occasion filter is correct:

```python
"casual":  {"casual", "formal", "both"}   # All items allowed — scoring handles quality
"formal":  {"formal", "both"}             # No casual-only items in formal outfits
```

**Why casual allows formal items:**
- Formal shirt + jeans = THE smart casual look
- Blazer + t-shirt + jeans = modern smart casual
- Dress shoes with casual outfit = intentional elevation
- The scoring system rewards coherent combos and penalizes bad ones

**Why formal excludes casual items:**
- A hoodie at a business meeting is never appropriate
- Sneakers with a suit is acceptable ONLY in very modern casual-forward contexts — but the user requesting "formal" expects traditional formality
- This asymmetry is intentional and correct

---

## 5. THE FORMALITY SYSTEM — ANALYSIS

### Current formality tags (per sub-category):

| Sub-category | Current tag | Fashion consensus | Correct? |
|-------------|-------------|-------------------|----------|
| formal_shirt | formal | Can be worn casually (untucked, rolled sleeves) | Should be **both** |
| kurta | both | Works casual and festive/semi-formal | ✓ Correct |
| polo_shirt | casual | Works in business casual too | Should be **both** |
| casual_tshirt | casual | Purely casual | ✓ Correct |
| hoodie | casual | Purely casual | ✓ Correct |
| blouse | both | Works casual and formal | ✓ Correct |
| kameez | both | Traditional versatile | ✓ Correct |
| jeans | casual | Universal casual | ✓ Correct |
| dress_trousers | formal | Works in smart casual too | Should be **both** |
| shalwar | both | Traditional versatile | ✓ Correct |
| chinos | both | Versatile middle ground | ✓ Correct |
| shorts | casual | Purely casual | ✓ Correct |
| skirt | both | Versatile | ✓ Correct |
| leggings | casual | Casual/athleisure | ✓ Correct |
| blazer | formal | Works smart casual too | Should be **both** |
| sherwani | formal | SA formal only | ✓ Correct |
| waistcoat | formal | Mostly formal | ✓ Correct |
| jacket | casual | Casual layering | ✓ Correct |
| coat | both | Weather-driven, not formality-driven | ✓ Correct |
| hoodie_jacket | casual | Purely casual | ✓ Correct |
| cardigan | casual | Can be smart casual | Should be **both** |
| heels | formal | Can be casual (with jeans) | Should be **both** |
| formal_shoes | formal | Formal context | ✓ Correct |
| sneakers | casual | Purely casual (modern exceptions exist) | ✓ Correct |
| loafers | both | Versatile | ✓ Correct |
| sandals | casual | Casual only | ✓ Correct |
| boots | both | Versatile | ✓ Correct |
| chappal | casual | SA casual | ✓ Correct |

### Items that should change formality:

| Item | From | To | Why |
|------|------|----|-----|
| formal_shirt | formal | **both** | Untucked formal shirt + jeans is the most recommended outfit in men's fashion history |
| dress_trousers | formal | **both** | Works in smart casual with polos, tshirts |
| blazer | formal | **both** | Blazer + jeans/tshirt is the definition of smart casual |
| polo_shirt | casual | **both** | Polo is THE business casual shirt |
| cardigan | casual | **both** | Smart casual layering piece |
| heels | formal | **both** | Women wear heels with jeans routinely |

### Impact of formality changes:

If we change these 6 items to "both" AND remove Rule 5:
- **Before:** formal_shirt + jeans → BLOCKED by Rule 5 (formal + casual)
- **After:** formal_shirt (both) + jeans (casual) → Rule 5 wouldn't block even if kept (formal_shirt is now "both")

**However**, changing formality defaults in CLIP hints affects NEW uploads only. Existing wardrobe items keep their current formality unless the user manually edits them.

**Better approach:** Remove Rule 5 (the blanket block) so that existing items with "formal" tags can still mix with "casual" items. The blocked pairs (Rule 6) and scoring system handle quality.

---

## 6. IMPLEMENTATION PLAN

### Phase A: Remove Rule 5 (highest impact, simplest change)

**File:** `engine/hard_rules.py`
**Change:** Remove lines 96-103 (Rule 5: blanket formality block)
**Effect:** Formal shirt + jeans, blazer + t-shirt + jeans, and all other cross-formality combos become candidates. Bad combos are still caught by blocked pairs (Rule 6) and scored low by the 5-component scorer.

**Tests to update:**
- `tests/test_hard_rules.py` — remove/invert tests asserting Rule 5 behavior
- Add new tests asserting that valid cross-formality combos pass hard rules

### Phase B: Update blocked pairs

**File:** `engine/hard_rules.py`
**Changes:**
1. Remove `blazer + sneakers` (now valid smart casual)
2. Add 7 new blocked pairs (sherwani+shorts, sherwani+leggings, etc.)

**Tests:** Add tests for each new blocked pair

### Phase C: Expand synergy bonuses

**File:** `engine/style_intelligence.py`
**Changes:** Add ~15 new synergy bonus pairs for cross-formality smart casual looks

**Tests:** Verify synergy scores increase for new pairs

### Phase D: Update CLIP formality hints

**File:** `engine/pipeline.py` (CLIP sub-category definitions)
**Changes:** Update formality hints for 6 items (formal_shirt → both, blazer → both, etc.)
**Effect:** New uploads get better formality tags. Existing items unaffected.

### Execution order: A → B → C → D (each is independently mergeable)

---

## 7. WHAT WE ARE NOT CHANGING (AND WHY)

| Area | Why it's correct |
|------|-----------------|
| Occasion filter rules | Already correct — casual allows everything, formal excludes casual-only |
| Scoring weights (0.35/0.20/0.15/0.10/0.20) | Well-balanced, no evidence of problems |
| Model 2 architecture | Performing well (AUC 0.814), retraining is out of FYP scope |
| Color scorer (Itten theory) | Scientifically grounded, no complaints |
| Weather scorer (ASHRAE CLO) | Well-calibrated for Pakistani climate |
| Cohesion scorer (centroid alignment) | Mathematically sound |
| Template system (12 templates) | Covers all valid outfit structures |
| Category system (6 categories) | Matches Model 1 training data |

---

## 8. RISK ASSESSMENT

### Removing Rule 5:
- **Risk:** More outfit candidates → slightly longer recommendation time
- **Mitigation:** MAX_CANDIDATES_PER_TEMPLATE (500) cap already prevents explosion
- **Risk:** Some bad cross-formality combos slip through
- **Mitigation:** Blocked pairs catch the worst ones, scoring penalizes mediocre ones

### Adding blocked pairs:
- **Risk:** Over-blocking reduces variety
- **Mitigation:** Only adding universally agreed blocks (sherwani + casual items)

### Updating CLIP hints:
- **Risk:** None for existing items (only affects new uploads)
- **Mitigation:** Users can always manually edit formality

---

## Sources

- GQ Style Guide — smart casual formulas, formality mixing rules
- Esquire Men's Fashion — blazer + sneakers modern acceptance
- Vogue — women's formality mixing, heels + casual
- r/malefashionadvice — community-validated outfit formulas
- HSY, Khaadi, Generation — Pakistani fashion authority consensus on fusion
- "Dressing the Man" (Alan Flusser) — classic menswear rules
- ASHRAE Standard 55 — thermal comfort (already in engine)
- Itten "The Art of Color" — color harmony (already in engine)
