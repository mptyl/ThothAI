# Docker Hub Push Instructions

## Prerequisites
- Docker installed and running
- Docker Hub account with `tylconsulting` organization access

## Login to Docker Hub

Before pushing images, you need to login to Docker Hub using the `tylconsulting` organization account:

```bash
docker login -u tylconsulting
```

Enter the password or access token for the `tylconsulting` organization account when prompted.

## Push Images to Docker Hub

Use the `push.sh` script to build and push all images to Docker Hub. **Important**: You must use `docker.io/tylconsulting` as the registry URL.

### Basic Usage

```bash
./push.sh docker.io/tylconsulting VERSION
```

### Examples

```bash
# Push version 1.0
./push.sh docker.io/tylconsulting 1.0

# Push version 2.1 without cache
./push.sh docker.io/tylconsulting 2.1 --no-cache

# Push only (skip build if images already exist)
./push.sh docker.io/tylconsulting 1.0 --push-only
```

### Options

- `--no-cache`: Build images without using Docker cache
- `--push-only`: Push only existing images, skip the build phase
- `--help`: Show usage information

## What Gets Pushed

The script builds and pushes the following images:

1. **thoth-backend** - Django backend service
2. **thoth-frontend** - Next.js frontend application
3. **thoth-sql-generator** - FastAPI SQL Generator with PydanticAI agents
4. **thoth-proxy** - Nginx proxy service
5. **thoth-mermaid-service** - Mermaid diagram rendering service
6. **thoth-qdrant** - Vector database (pulled and re-tagged)

Each image is pushed with two tags:
- `docker.io/tylconsulting/thoth-{service}:VERSION` (e.g., `docker.io/tylconsulting/thoth-backend:1.0`)
- `docker.io/tylconsulting/thoth-{service}:latest`

## Verification

After the push completes, verify the images on Docker Hub:

```bash
# List local images
docker images | grep thoth

# Or visit https://hub.docker.com/u/tylconsulting
```

## Troubleshooting

### Login Issues

If you encounter login errors:

```bash
# Logout first
docker logout

# Login again with tylconsulting organization account
docker login -u tylconsulting
```

### Permission Denied

Make sure you have push access to the `tylconsulting` organization on Docker Hub.

### "insufficient_scope: authorization failed" Error

This error typically occurs when using a **Personal Access Token (PAT)** with incorrect permissions:

**Solution 1: Use your account password instead of PAT**
```bash
docker logout
docker login -u tylconsulting
# Enter your account password when prompted
```

**Solution 2: Create a new PAT with proper scope**
1. Go to https://hub.docker.com/settings/security
2. Click "New Access Token"
3. Give it a description (e.g., "ThothAI Push")
4. **IMPORTANT**: Select **"Read & Write"** scope, NOT "Read Only"
5. Copy the token and use it as password when logging in

**Solution 3: Verify existing PAT scope**
- If you already have a PAT, check its scope in Docker Hub settings
- PATs with "Read Only" scope cannot push images
- Delete and recreate the PAT with "Read & Write" scope

### Push Fails

If push fails for a specific image, you can retry with `--push-only` after fixing the issue:

```bash
./push.sh docker.io/tylconsulting 1.0 --push-only
```

## Next Steps

After pushing images to Docker Hub:

1. Update your deployment configuration to use the new image tags
2. Deploy to your environment using `./deploy-swarm.sh`
3. Verify the deployment is running correctly

---

## Git History Cleanup - Force Push Instructions

### What was cleaned
- All `.env*` files (including `.envrc`, `.env.docker`, etc.)
- All local config files (`config.yml.local`, `config.local.yml`, etc.)
- All secrets files (`secrets.yml`, `api_keys.yml`, etc.)

### ⚠️  IMPORTANT: Force Push Required

The git history has been rewritten to remove sensitive files. To update the remote repository, you MUST force push:

```bash
git push --force-with-lease origin main
```

**Before you push:**
1. Make sure all collaborators are aware of the history rewrite
2. Coordinate with your team to avoid conflicts
3. Backup the current remote state if needed

### What will happen after force push
- The cleaned history will replace the remote history
- All sensitive files will be permanently removed from the remote
- Any local branches based on the old history will need to be rebased

### For collaborators
All collaborators should run:
```bash
git fetch origin
git reset --hard origin/main
```

### Verification
After pushing, you can verify the cleanup worked:
```bash
git log --all --full-history --name-only | grep -E "\.env|config\.local|secrets" | wc -l
# Should return 0
```