#!/usr/bin/env bash
# ThothAI - Frontend housekeeping script
# Moves legacy files, removes redundant artifacts, and ensures logs/.gitkeep exists.
# Safe by default (no git mutations). Use --git to stage deletions/moves.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
LEGACY_DIR="$ROOT_DIR/legacy/frontend"
FRONTEND_DIR="$ROOT_DIR/frontend"

# Create legacy directory
mkdir -p "$LEGACY_DIR"

info() { echo -e "\033[0;34m[info]\033[0m $*"; }
success() { echo -e "\033[0;32m[ok]\033[0m   $*"; }
warn() { echo -e "\033[1;33m[warn]\033[0m $*"; }
error() { echo -e "\033[0;31m[err]\033[0m  $*"; }

USE_GIT=false
if [[ "${1:-}" == "--git" ]]; then
  USE_GIT=true
  info "Git staging enabled (--git)"
fi

# Items to move to legacy
MOVE_TO_LEGACY=(
  "frontend/Dockerfile"
  "frontend/build.sh"
  "frontend/clean-docker.sh"
  "frontend/debug-all.sh"
  "frontend/docker-compose.yml"
  "frontend/orchestrator-setup.sh"
  "frontend/run.sh"
  "frontend/start-all.sh"
  "frontend/start.sh"
  "frontend/stop-all.sh"
  "frontend/installer"
  "frontend/ThothSlScreenshot.png"
)

# Items to remove completely (artifacts/unused)
REMOVE_COMPLETELY=(
  "frontend/.next"
  "frontend/.pytest_cache"
  "frontend/.ruff_cache"
  "frontend/.venv"
  "frontend/data"
  "frontend/docker-entrypoint.sh"
  "frontend/node_modules"
  "frontend/pyproject.toml"
  "frontend/pyproject.local.toml"
  "frontend/pyproject.local.toml.example"
  "frontend/scripts"
  "frontend/thoth_ui_backend.egg-info"
  "frontend/uv.lock"
)

moved=()
removed=()
skipped=()

# Move items to legacy
for rel in "${MOVE_TO_LEGACY[@]}"; do
  src="$ROOT_DIR/$rel"
  if [[ -e "$src" ]]; then
    dest_dir="$LEGACY_DIR/$(dirname "${rel#frontend/}")"
    mkdir -p "$dest_dir"
    info "Moving $rel -> legacy/frontend/$(dirname "${rel#frontend/}")/"
    mv "$src" "$dest_dir/"
    moved+=("$rel")
    if $USE_GIT && git -C "$ROOT_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
      git -C "$ROOT_DIR" add -A "$dest_dir" || true
    fi
  else
    skipped+=("$rel (not found)")
  fi
done

# Remove items
for rel in "${REMOVE_COMPLETELY[@]}"; do
  target="$ROOT_DIR/$rel"
  if [[ -e "$target" ]]; then
    info "Removing $rel"
    rm -rf "$target"
    removed+=("$rel")
    if $USE_GIT && git -C "$ROOT_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
      # Stage deletions
      if git -C "$ROOT_DIR" ls-files --error-unmatch "$rel" >/dev/null 2>&1; then
        git -C "$ROOT_DIR" rm -rf --cached --quiet "$rel" || true
      fi
    fi
  else
    skipped+=("$rel (not found)")
  fi
done

# Ensure frontend/logs/.gitkeep exists
LOGS_DIR="$FRONTEND_DIR/logs"
mkdir -p "$LOGS_DIR"
if [[ ! -f "$LOGS_DIR/.gitkeep" ]]; then
  info "Creating frontend/logs/.gitkeep"
  : > "$LOGS_DIR/.gitkeep"
  if $USE_GIT && git -C "$ROOT_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    git -C "$ROOT_DIR" add "$FRONTEND_DIR/logs/.gitkeep" || true
  fi
else
  info "frontend/logs/.gitkeep already present"
fi

# Summary
echo
success "Cleanup completed"
if (( ${#moved[@]} > 0 )); then
  echo "Moved to legacy:"; for x in "${moved[@]}"; do echo "  - $x"; done
fi
if (( ${#removed[@]} > 0 )); then
  echo "Removed:"; for x in "${removed[@]}"; do echo "  - $x"; done
fi
if (( ${#skipped[@]} > 0 )); then
  echo "Skipped (missing):"; for x in "${skipped[@]}"; do echo "  - $x"; done
fi

echo
info "Legacy folder: $LEGACY_DIR"
info "Run again with --git to stage changes in git"
