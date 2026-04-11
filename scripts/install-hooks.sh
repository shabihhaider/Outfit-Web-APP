#!/usr/bin/env bash
# scripts/install-hooks.sh — one-time setup for new clones
# Run this once after cloning: bash scripts/install-hooks.sh

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

git config core.hooksPath scripts/hooks
chmod +x scripts/hooks/pre-push
chmod +x scripts/preflight.sh

echo "Git hooks installed. Preflight will run before every push."
