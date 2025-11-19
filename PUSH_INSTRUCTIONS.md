# Git History Cleanup - Push Instructions

## What was cleaned
- All `.env*` files (including `.envrc`, `.env.docker`, etc.)
- All local config files (`config.yml.local`, `config.local.yml`, etc.)
- All secrets files (`secrets.yml`, `api_keys.yml`, etc.)

## ⚠️  IMPORTANT: Force Push Required

The git history has been rewritten to remove sensitive files. To update the remote repository, you MUST force push:

```bash
git push --force-with-lease origin main
```

**Before you push:**
1. Make sure all collaborators are aware of the history rewrite
2. Coordinate with your team to avoid conflicts
3. Backup the current remote state if needed

## What will happen after force push
- The cleaned history will replace the remote history
- All sensitive files will be permanently removed from the remote
- Any local branches based on the old history will need to be rebased

## For collaborators
All collaborators should run:
```bash
git fetch origin
git reset --hard origin/main
```

## Verification
After pushing, you can verify the cleanup worked:
```bash
git log --all --full-history --name-only | grep -E "\.env|config\.local|secrets" | wc -l
# Should return 0
```