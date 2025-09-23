#!/usr/bin/env bash
set -euo pipefail

# Ensure keyring dir exists
mkdir -p /usr/share/keyrings

# Download Microsoft repo key if missing
if [ ! -f /usr/share/keyrings/microsoft-prod.gpg ]; then
    curl -sSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg
fi

# Add repo list if missing
if [ ! -f /etc/apt/sources.list.d/mssql-release.list ]; then
    echo "deb [signed-by=/usr/share/keyrings/microsoft-prod.gpg arch=amd64] https://packages.microsoft.com/debian/12/prod bookworm main" > /etc/apt/sources.list.d/mssql-release.list
fi

apt-get update -qq
ACCEPT_EULA=Y apt-get install -y -qq --no-install-recommends msodbcsql17 msodbcsql18 || {
    echo "Microsoft packages not available; skipping" >&2
    exit 0
}
