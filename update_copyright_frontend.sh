#!/bin/bash
# Script temporaneo per aggiornare il copyright nei file frontend

find /Users/mp/ThothAI/frontend -type f \( -name "*.ts" -o -name "*.tsx" -o -name "*.js" \) \
  ! -path "*/node_modules/*" \
  ! -path "*/.next/*" \
  ! -path "*/dist/*" \
  -exec sed -i '' 's/\/\/ Copyright (c) 2025 Marco Pancotti/\/\/ Copyright (c) 2025 Tyl Consulting di Pancotti Marco/g' {} \;

echo "Frontend TypeScript/JavaScript files updated"
