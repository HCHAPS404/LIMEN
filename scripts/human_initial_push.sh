#!/usr/bin/env bash
# Run this yourself from the repo root. Do not ask the assistant to commit/push/PR.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

REMOTE_URL="${REMOTE_URL:-https://github.com/HCHAPS404/LIMEN.git}"
BRANCH="${BRANCH:-main}"

echo "==> Sanity: .cursor must NOT be staged"
if git check-ignore -q .cursor 2>/dev/null || grep -q '^\.cursor/' .gitignore; then
  echo "    .cursor is ignored (good)"
else
  echo "ERROR: .cursor is not ignored. Aborting."
  exit 1
fi

echo "==> Configure identity for this repo only (optional if already set globally)"
git config user.name "hchaps404"
git config user.email "helmut.chs@gmail.com"

echo "==> Init / remote"
if [ ! -d .git ]; then
  git init -b "$BRANCH"
fi
if git remote get-url origin >/dev/null 2>&1; then
  git remote set-url origin "$REMOTE_URL"
else
  git remote add origin "$REMOTE_URL"
fi

echo "==> Stage public files"
git add -A
# Belt-and-suspenders: never stage local tooling
git rm -r --cached .cursor 2>/dev/null || true

echo "==> Review what will be committed (look for .cursor — should be empty)"
git status
echo
git diff --cached --stat
echo
if git diff --cached --name-only | grep -E '(^\.cursor/|SKILL\.md$|agents/)' >/dev/null; then
  echo "ERROR: staging includes local tooling paths. Aborting."
  exit 1
fi

read -r -p "Create commit and push to origin/$BRANCH? [y/N] " confirm
if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
  echo "Stopped before commit. Staging left as-is for your review."
  exit 0
fi

git commit -m "$(cat <<'EOF'
chore: scaffold LIMEN foundation for Tech Sphere Challenge

Establish modular monolith, provider contracts, API health, web shell,
safety governor stub, docs/ADRs, and reproducible verify gates.
EOF
)"

git push -u origin "$BRANCH"
echo "==> Done: https://github.com/HCHAPS404/LIMEN"
