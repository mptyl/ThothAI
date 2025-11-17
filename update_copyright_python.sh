#!/bin/bash
# Script temporaneo per aggiornare il copyright nei file Python

# SQL Generator
find /Users/mp/ThothAI/frontend/sql_generator -type f -name "*.py" \
  ! -path "*/.venv/*" \
  ! -path "*/__pycache__/*" \
  ! -path "*/dist/*" \
  -exec sed -i '' 's/# Copyright (c) 2025 Marco Pancotti/# Copyright (c) 2025 Tyl Consulting di Pancotti Marco/g' {} \;

# Backend
find /Users/mp/ThothAI/backend -type f -name "*.py" \
  ! -path "*/.venv/*" \
  ! -path "*/__pycache__/*" \
  ! -path "*/migrations/*" \
  ! -path "*/dist/*" \
  ! -path "*/vendor/*" \
  -exec sed -i '' 's/# Copyright (c) 2025 Marco Pancotti/# Copyright (c) 2025 Tyl Consulting di Pancotti Marco/g' {} \;

# Altri file Python nella root
find /Users/mp/ThothAI -maxdepth 1 -type f -name "*.py" \
  -exec sed -i '' 's/# Copyright (c) 2025 Marco Pancotti/# Copyright (c) 2025 Tyl Consulting di Pancotti Marco/g' {} \;

# Docker scripts
find /Users/mp/ThothAI/docker -type f -name "*.py" \
  ! -path "*/.venv/*" \
  -exec sed -i '' 's/# Copyright (c) 2025 Marco Pancotti/# Copyright (c) 2025 Tyl Consulting di Pancotti Marco/g' {} \;

echo "Python files updated"
