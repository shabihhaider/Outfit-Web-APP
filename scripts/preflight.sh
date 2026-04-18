#!/usr/bin/env bash
# scripts/preflight.sh — OutfitAI quality gate
# Run before every push/merge: lint, security scan, migration check, tests.
# Usage: bash scripts/preflight.sh
# Exit code: 0 = all clear, 1 = any check failed.

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# ── Fast-path: skip slow checks when only CI/docs/scripts changed ────────────
CHANGED=$(git diff --cached --name-only 2>/dev/null || git diff HEAD~1 --name-only 2>/dev/null || true)
CODE_CHANGED=$(echo "$CHANGED" | grep -vE '^(\.github/|scripts/|docs/|README|CLAUDE\.md|frontend/\.gitignore)' | head -1)
if [ -z "$CODE_CHANGED" ] && [ -n "$CHANGED" ]; then
  echo ""
  echo "===== OutfitAI Preflight (fast-path) =================================="
  echo "  Only CI/scripts/docs changed — skipping slow checks."
  echo "  Remote CI will run the full gate."
  echo "======================================================================="
  echo ""
  exit 0
fi

PASS=0
FAIL=0
PYTHON="${PYTHON:-python}"

# Resolve python (prefer 3.11)
if command -v py &>/dev/null; then
  PYTHON="py -3.11"
elif command -v python3.11 &>/dev/null; then
  PYTHON="python3.11"
elif command -v python3 &>/dev/null; then
  PYTHON="python3"
fi

_ok()   { echo "  [OK]   $1"; PASS=$((PASS+1)); }
_fail() { echo "  [FAIL] $1"; FAIL=$((FAIL+1)); }
_skip() { echo "  [SKIP] $1 (tool not installed)"; }

echo ""
echo "===== OutfitAI Preflight =============================================="
echo ""

# ── 1. Python lint (flake8) ─────────────────────────────────────────────────
echo "[1/5] Lint (flake8)"
if $PYTHON -m flake8 --version &>/dev/null 2>&1; then
  if $PYTHON -m flake8 app/ engine/ \
      --max-line-length=110 \
      --extend-ignore=E203,W503,E501,E221,E251,E272 \
      --exclude=app/migrations/,__pycache__ \
      --count --statistics 2>&1; then
    _ok "flake8 — no errors"
  else
    _fail "flake8 — fix lint errors above"
  fi
else
  _skip "flake8 (pip install flake8 to enable)"
fi
echo ""

# ── 2. Security scan (bandit) ───────────────────────────────────────────────
echo "[2/5] Security scan (bandit)"
if $PYTHON -m bandit --version &>/dev/null 2>&1; then
  if $PYTHON -m bandit -r app/ engine/ \
      -ll -ii \
      --exclude app/migrations,app/tests \
      -q 2>&1; then
    _ok "bandit — no high-severity issues"
  else
    _fail "bandit — review security issues above"
  fi
else
  _skip "bandit (pip install bandit to enable)"
fi
echo ""

# ── 3. Migration check ──────────────────────────────────────────────────────
echo "[3/5] Migration check (flask db upgrade)"
MIGRATION_DB="$(mktemp /tmp/outfitai_migration_XXXX.db)"
if FLASK_CONFIG=testing \
   SQLALCHEMY_DATABASE_URI="sqlite:///$MIGRATION_DB" \
   $PYTHON -m flask db upgrade 2>&1; then
  _ok "flask db upgrade — all migrations applied cleanly"
else
  _fail "flask db upgrade — migration failed (check alembic scripts)"
fi
rm -f "$MIGRATION_DB"
echo ""

# ── 4. Core test suite ──────────────────────────────────────────────────────
echo "[4/5] Core tests (pytest)"
CORE_TESTS=(
  tests/test_hard_rules.py
  tests/test_scorer.py
  tests/test_occasion_filter.py
  tests/test_color_scorer.py
  tests/test_weather_scorer.py
  tests/test_flask_auth.py
  tests/test_flask_wardrobe.py
  tests/test_flask_consent.py
  tests/test_flask_outfits.py
  tests/test_flask_recommendations.py
)
if FLASK_CONFIG=testing TQDM_DISABLE=1 $PYTHON -m pytest "${CORE_TESTS[@]}" \
    -q --tb=short -p no:warnings 2>&1; then
  _ok "pytest — all core tests passed"
else
  _fail "pytest — tests failed (see above)"
fi
echo ""

# ── 5. Frontend build ───────────────────────────────────────────────────────
echo "[5/5] Frontend build (vite)"
if command -v npm &>/dev/null && [ -f frontend/package.json ]; then
  cd frontend
  if npm run build --silent 2>&1 | tail -3; then
    _ok "vite build — no errors"
  else
    _fail "vite build — fix build errors above"
  fi
  cd "$ROOT"
else
  _skip "npm not found or no frontend/package.json"
fi
echo ""

# ── Summary ─────────────────────────────────────────────────────────────────
echo "======================================================================="
echo "  Results: $PASS passed, $FAIL failed"
echo "======================================================================="
echo ""

if [ "$FAIL" -gt 0 ]; then
  echo "Preflight FAILED — fix the issues above before pushing."
  exit 1
else
  echo "Preflight PASSED — safe to push."
  exit 0
fi
