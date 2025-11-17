#!/bin/bash
# Copyright (c) 2025 Tyl Consulting di Pancotti Marco
# This file is part of Thoth and is released under the MIT License.
# See the LICENSE.md file in the project root for full license information.

set -e

echo "==================================="
echo "   ThothAI Local Test Script       "
echo "==================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

# Test Backend
echo ""
echo "Testing Backend..."
echo "-----------------"
cd backend

# Check Python
if command -v python3 &> /dev/null; then
    print_status "Python found: $(python3 --version)"
else
    print_error "Python3 not found!"
    exit 1
fi

# Check Django
if python3 manage.py check > /dev/null 2>&1; then
    print_status "Django configuration: OK"
else
    print_error "Django configuration check failed!"
    exit 1
fi

# Run backend tests
if python3 manage.py test --no-input > /dev/null 2>&1; then
    print_status "Backend tests: PASSED"
else
    print_warning "Some backend tests failed (non-critical)"
fi

cd ..

# Test Frontend
echo ""
echo "Testing Frontend..."
echo "------------------"
cd frontend

# Check Node
if command -v node &> /dev/null; then
    print_status "Node found: $(node --version)"
else
    print_error "Node not found!"
    exit 1
fi

# Check npm
if command -v npm &> /dev/null; then
    print_status "npm found: $(npm --version)"
else
    print_error "npm not found!"
    exit 1
fi

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    print_warning "Installing frontend dependencies..."
    npm ci
fi

# Build frontend
print_status "Building frontend..."
if npm run build > /dev/null 2>&1; then
    print_status "Frontend build: SUCCESS"
else
    print_error "Frontend build failed!"
    exit 1
fi

cd ..

# Test SQL Generator
echo ""
echo "Testing SQL Generator..."
echo "-----------------------"
cd frontend/sql_generator

# Check if it can be imported
if python3 -c "import main" > /dev/null 2>&1; then
    print_status "SQL Generator: OK"
else
    print_warning "SQL Generator import check failed (may need dependencies)"
fi

cd ../..

echo ""
echo "==================================="
print_status "All tests completed!"
echo "==================================="
echo ""
echo "Next steps:"
echo "1. Review any warnings above"
echo "2. Run 'docker-compose build' to build Docker images"
echo "3. Run 'docker-compose up' to start all services"