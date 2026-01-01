#!/usr/bin/env bash
# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache 2.0.
# See the LICENSE.md file in the project root for full license information.

set -euo pipefail

# Ensure keyring dir exists
mkdir -p /usr/share/keyrings

# Download Microsoft repo key if missing
if [ ! -f /usr/share/keyrings/microsoft-prod.gpg ]; then
    curl -sSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg
fi

# Detect architecture
ARCH=$(dpkg --print-architecture)
if [[ "$ARCH" != "amd64" && "$ARCH" != "arm64" ]]; then
    echo "Unsupported architecture: $ARCH; skipping MS ODBC installation" >&2
    exit 0
fi

# Add repo list if missing (using the detected architecture)
if [ ! -f /etc/apt/sources.list.d/mssql-release.list ]; then
    echo "deb [signed-by=/usr/share/keyrings/microsoft-prod.gpg arch=$ARCH] https://packages.microsoft.com/debian/12/prod bookworm main" > /etc/apt/sources.list.d/mssql-release.list
fi

apt-get update -qq
ACCEPT_EULA=Y apt-get install -y -qq --no-install-recommends msodbcsql17 msodbcsql18 || {
    echo "Microsoft packages not available for $ARCH; skipping" >&2
    exit 0
}
