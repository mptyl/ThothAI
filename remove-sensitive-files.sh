#!/bin/bash

# Script to remove sensitive files from git history
# Copyright (c) 2025 Tyl Consulting di Pancotti Marco
# This file is part of ThothAI and is released under the Apache 2.0.
# See the LICENSE.md file in the project root for full license information.

echo "Starting removal of sensitive files from git history..."

# Backup current branch
BACKUP_BRANCH="backup-before-cleanup-$(date +%s)"
git branch $BACKUP_BRANCH
echo "Created backup branch: $BACKUP_BRANCH"

# Files to remove from history
SENSITIVE_FILES=(
    "*.env*"
    "config.yml.local"
    "config.local.yml"
    "config.yaml.local"
    "config.local.yaml"
    "config.toml.local"
    "config.local.toml"
    "secrets.yml"
    "secrets.yaml"
    "api_keys.yml"
    "api_keys.yaml"
    ".envrc"
    "config.yml"
)

# Remove files from history using git filter-branch
echo "Removing sensitive files from git history..."
git filter-branch --force --index-filter '
    # Remove .env files
    git rm --cached --ignore-unmatch "*.env*" 2>/dev/null || true

    # Remove config.yml.local files
    git rm --cached --ignore-unmatch "config.yml.local" 2>/dev/null || true
    git rm --cached --ignore-unmatch "config.local.yml" 2>/dev/null || true
    git rm --cached --ignore-unmatch "config.yaml.local" 2>/dev/null || true
    git rm --cached --ignore-unmatch "config.local.yaml" 2>/dev/null || true
    git rm --cached --ignore-unmatch "config.toml.local" 2>/dev/null || true
    git rm --cached --ignore-unmatch "config.local.toml" 2>/dev/null || true

    # Remove other sensitive files
    git rm --cached --ignore-unmatch "secrets.yml" 2>/dev/null || true
    git rm --cached --ignore-unmatch "secrets.yaml" 2>/dev/null || true
    git rm --cached --ignore-unmatch "api_keys.yml" 2>/dev/null || true
    git rm --cached --ignore-unmatch "api_keys.yaml" 2>/dev/null || true
    git rm --cached --ignore-unmatch ".envrc" 2>/dev/null || true

    # Remove config.yml only if it contains API keys (keep templates)
    if [ -f "config.yml" ]; then
        if grep -q "api_key:" config.yml 2>/dev/null; then
            git rm --cached --ignore-unmatch "config.yml" 2>/dev/null || true
        fi
    fi
' --prune-empty --tag-name-filter cat -- --all

echo "Cleaning up git history..."
git for-each-ref --format="delete %(refname)" refs/original | git update-ref --stdin

echo "Running garbage collection..."
git reflog expire --expire=now --all
git gc --prune=now --aggressive

echo "Sensitive files removal completed!"
echo ""
echo "⚠️  IMPORTANT: If you have already pushed this repository to a remote,"
echo "   you will need to force push the cleaned history:"
echo "   git push --force-with-lease origin main"
echo ""
echo "   Make sure all collaborators are aware of this history rewrite!"
echo ""
echo "Backup branch created: $BACKUP_BRANCH"