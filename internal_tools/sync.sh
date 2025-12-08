#!/usr/bin/env bash
set -euo pipefail

REMOTE="${1:-origin}"
BRANCH="${2:-main}"

echo "[sync] Using $REMOTE/$BRANCH"

# Asegurarnos de estar en un repo git
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "[sync] ❌ Not inside a git repository."
  exit 1
fi

echo "[sync] Fetching latest refs..."
git fetch "$REMOTE"

# Mostrar estado corto
echo
git status -sb

# Calcular ahead/behind
AHEAD_BEHIND=$(git rev-list --left-right --count "$REMOTE/$BRANCH"...HEAD || echo "0 0")
BEHIND=$(echo "$AHEAD_BEHIND" | awk '{print $1}')
AHEAD=$(echo "$AHEAD_BEHIND" | awk '{print $2}')

echo
echo "[sync] Behind: $BEHIND  |  Ahead: $AHEAD"

if [[ "$BEHIND" -eq 0 && "$AHEAD" -eq 0 ]]; then
  echo "[sync] ✅ Local branch is up to date with $REMOTE/$BRANCH."
  exit 0
fi

if [[ "$BEHIND" -gt 0 && "$AHEAD" -eq 0 ]]; then
  echo "[sync] You are BEHIND. Recommended: git pull."
  read -r -p "[sync] Run 'git pull --rebase' now? [y/N] " ans
  if [[ "$ans" == "y" || "$ans" == "Y" ]]; then
    git pull --rebase "$REMOTE" "$BRANCH"
  fi
  exit 0
fi

if [[ "$BEHIND" -eq 0 && "$AHEAD" -gt 0 ]]; then
  echo "[sync] You are AHEAD. Recommended: git push."
  read -r -p "[sync] Run 'git push'? [y/N] " ans
  if [[ "$ans" == "y" || "$ans" == "Y" ]]; then
    git push "$REMOTE" "$BRANCH"
  fi
  exit 0
fi

# Divergencia
echo "[sync] ⚠️ Branch has diverged (both ahead and behind)."
echo "       You probably need to do:"
echo "         git pull --rebase $REMOTE $BRANCH"
echo "       or handle manually (rebase/merge)."