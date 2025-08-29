#!/bin/bash
# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

# Local test runner with isolated containers
# This script runs tests without modifying any code and generates reports

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

echo -e "${GREEN}Thoth Local Test Runner${NC}"
echo "========================"

# Check if virtual environment is active
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo -e "${YELLOW}Warning: No virtual environment detected${NC}"
    echo "Activating virtual environment..."
    source "$PROJECT_ROOT/venv/bin/activate" 2>/dev/null || {
        echo -e "${RED}Error: Could not activate virtual environment${NC}"
        echo "Please create a virtual environment first: python -m venv venv"
        exit 1
    }
fi

# Parse command line arguments
TEST_SCOPE="${1:-quick}"
KEEP_CONTAINERS="${2:-no}"

echo "Test scope: $TEST_SCOPE"
echo "Keep containers after test: $KEEP_CONTAINERS"

# Function to cleanup containers
cleanup_containers() {
    echo -e "\n${YELLOW}Cleaning up test containers...${NC}"
    docker stop thoth-test-postgres thoth-test-qdrant 2>/dev/null || true
    docker rm thoth-test-postgres thoth-test-qdrant 2>/dev/null || true
    docker network rm thoth-test-net 2>/dev/null || true
}

# Trap to ensure cleanup on exit
if [ "$KEEP_CONTAINERS" != "yes" ]; then
    trap cleanup_containers EXIT
fi

# Start test containers
echo -e "\n${GREEN}Starting test containers...${NC}"

# Create isolated test network
docker network create thoth-test-net 2>/dev/null || true

# Start PostgreSQL test container
echo "Starting PostgreSQL test container..."
docker run -d \
    --name thoth-test-postgres \
    --network thoth-test-net \
    -e POSTGRES_USER=test_user \
    -e POSTGRES_PASSWORD=test_pass \
    -e POSTGRES_DB=test_db \
    -p 5444:5432 \
    postgres:15

# Start Qdrant test container
echo "Starting Qdrant test container..."
docker run -d \
    --name thoth-test-qdrant \
    --network thoth-test-net \
    -p 6334:6333 \
    qdrant/qdrant:latest

# Wait for containers to be ready
echo -e "\n${YELLOW}Waiting for containers to be ready...${NC}"
sleep 5

# Check PostgreSQL
until docker exec thoth-test-postgres pg_isready -U test_user > /dev/null 2>&1; do
    echo -n "."
    sleep 1
done
echo -e "\n${GREEN}PostgreSQL is ready${NC}"

# Check Qdrant
until curl -s http://localhost:6334/health > /dev/null 2>&1; do
    echo -n "."
    sleep 1
done
echo -e "\n${GREEN}Qdrant is ready${NC}"

# Set up test environment
echo -e "\n${GREEN}Setting up test environment...${NC}"
cd "$PROJECT_ROOT"

# Create test environment file
cat > .env.test << EOF
DATABASE_URL=postgresql://test_user:test_pass@localhost:5444/test_db
QDRANT_URL=http://localhost:6334
SECRET_KEY=test-secret-key-local-run
DEBUG=True
TESTING=True
DJANGO_SETTINGS_MODULE=Thoth.settings
EOF

# Install test dependencies if needed
echo "Checking test dependencies..."
uv sync --extra test

# Run migrations
echo -e "\n${GREEN}Running database migrations...${NC}"
export DATABASE_URL=postgresql://test_user:test_pass@localhost:5444/test_db
uv run python manage.py migrate --noinput

# Create test reports directory
mkdir -p tests/reports

# Run tests based on scope
echo -e "\n${GREEN}Running tests (scope: $TEST_SCOPE)...${NC}"

case $TEST_SCOPE in
    "quick")
        echo "Running quick tests..."
        DJANGO_SETTINGS_MODULE=Thoth.settings uv run pytest tests/integration/test_core_views.py::TestCoreViews::test_api_login_view \
               tests/integration/test_authentication.py::TestAuthentication::test_token_authentication \
               -v --tb=short
        ;;

    "full")
        echo "Running full test suite..."
        DJANGO_SETTINGS_MODULE=Thoth.settings uv run pytest tests/ -v --cov=. --cov-report=html --cov-report=term
        ;;

    "views")
        echo "Running view tests..."
        DJANGO_SETTINGS_MODULE=Thoth.settings uv run pytest tests/integration/test_core_views.py \
               tests/integration/test_ai_backend_views.py \
               -v --tb=short
        ;;

    "security")
        echo "Running security tests..."
        DJANGO_SETTINGS_MODULE=Thoth.settings uv run pytest tests/integration/test_authentication.py -v --tb=short
        ;;
    
    *)
        echo -e "${RED}Unknown test scope: $TEST_SCOPE${NC}"
        echo "Valid options: quick, full, views, security"
        exit 1
        ;;
esac

# Generate summary report
echo -e "\n${GREEN}Generating test summary...${NC}"
python << EOF
import json
import os
from datetime import datetime
from pathlib import Path

report_dir = Path('tests/reports')
reports = list(report_dir.glob('*.json'))

# Calculate totals
total_errors = 0
total_warnings = 0
failed_views = set()
warned_views = set()

for report_file in reports:
    with open(report_file) as f:
        data = json.load(f)
        total_errors += len(data.get('errors', []))
        total_warnings += len(data.get('warnings', []))
        
        for error in data.get('errors', []):
            failed_views.add(error.get('view', 'unknown'))
        
        for warning in data.get('warnings', []):
            warned_views.add(warning.get('view', 'unknown'))

# Create summary
summary = {
    'test_run': 'local',
    'timestamp': datetime.now().isoformat(),
    'test_scope': '$TEST_SCOPE',
    'total_reports': len(reports),
    'total_errors': total_errors,
    'total_warnings': total_warnings,
    'failed_views': list(failed_views),
    'warned_views': list(warned_views)
}

# Save summary
summary_file = report_dir / f'local_run_summary_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
with open(summary_file, 'w') as f:
    json.dump(summary, f, indent=2)

# Print summary
print(f"\nTest Summary:")
print(f"  Reports generated: {len(reports)}")
print(f"  Total errors: {total_errors}")
print(f"  Total warnings: {total_warnings}")
if failed_views:
    print(f"  Failed views: {', '.join(failed_views)}")
if warned_views:
    print(f"  Views with warnings: {', '.join(warned_views)}")
print(f"\nFull report saved to: {summary_file}")
EOF

# Show coverage report location if full tests were run
if [ "$TEST_SCOPE" == "full" ]; then
    echo -e "\n${GREEN}Coverage report generated at: htmlcov/index.html${NC}"
fi

echo -e "\n${GREEN}Test run completed!${NC}"

# Cleanup test env file
rm -f .env.test

# Ask if user wants to view reports
echo -e "\n${YELLOW}Would you like to view the test reports? (y/n)${NC}"
read -r response
if [[ "$response" == "y" ]]; then
    uv run python scripts/view-test-reports.py
fi