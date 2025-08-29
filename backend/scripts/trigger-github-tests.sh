#!/bin/bash
# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

# Trigger GitHub Actions tests manually
# Requires GitHub CLI (gh) to be installed and authenticated

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}GitHub Actions Test Trigger${NC}"
echo "==========================="

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    echo -e "${RED}Error: GitHub CLI (gh) is not installed${NC}"
    echo "Install it with: brew install gh (macOS) or see https://cli.github.com/"
    exit 1
fi

# Check if authenticated
if ! gh auth status &> /dev/null; then
    echo -e "${RED}Error: Not authenticated with GitHub${NC}"
    echo "Run: gh auth login"
    exit 1
fi

# Get test scope from argument or ask user
if [ -n "$1" ]; then
    TEST_SCOPE="$1"
else
    echo -e "\n${YELLOW}Select test scope:${NC}"
    echo "1) quick    - Only critical tests (5 min)"
    echo "2) full     - All tests (15 min)"
    echo "3) views    - Only view/URL tests"
    echo "4) security - Only security/auth tests"
    echo -n "Enter your choice (1-4): "
    read -r choice
    
    case $choice in
        1) TEST_SCOPE="quick" ;;
        2) TEST_SCOPE="full" ;;
        3) TEST_SCOPE="views" ;;
        4) TEST_SCOPE="security" ;;
        *) echo -e "${RED}Invalid choice${NC}"; exit 1 ;;
    esac
fi

echo -e "\n${BLUE}Selected scope: $TEST_SCOPE${NC}"

# Get current repository info
REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null || echo "")
if [ -z "$REPO" ]; then
    echo -e "${YELLOW}Warning: Could not detect repository. Using manual input.${NC}"
    echo -n "Enter repository (owner/name): "
    read -r REPO
fi

echo -e "Repository: ${BLUE}$REPO${NC}"

# Check if workflow exists
echo -e "\n${YELLOW}Checking workflow status...${NC}"
if ! gh workflow view test-suite.yml --repo "$REPO" &> /dev/null; then
    echo -e "${RED}Error: Workflow 'test-suite.yml' not found${NC}"
    echo "Make sure the workflow file exists in .github/workflows/"
    exit 1
fi

# Show recent runs
echo -e "\n${GREEN}Recent test runs:${NC}"
gh run list --workflow=test-suite.yml --repo "$REPO" --limit 5 || echo "No recent runs"

# Confirm trigger
echo -e "\n${YELLOW}Ready to trigger test run${NC}"
echo "Repository: $REPO"
echo "Workflow: test-suite.yml"
echo "Test scope: $TEST_SCOPE"
echo -n "Continue? (y/n): "
read -r confirm

if [[ "$confirm" != "y" ]]; then
    echo "Cancelled"
    exit 0
fi

# Trigger the workflow
echo -e "\n${GREEN}Triggering workflow...${NC}"
RUN_ID=$(gh workflow run test-suite.yml \
    --repo "$REPO" \
    -f test_scope="$TEST_SCOPE" \
    --json \
    2>&1 | grep -o '"id":[0-9]*' | grep -o '[0-9]*' || echo "")

if [ -z "$RUN_ID" ]; then
    # Fallback: trigger without capturing ID
    gh workflow run test-suite.yml \
        --repo "$REPO" \
        -f test_scope="$TEST_SCOPE"
    
    echo -e "\n${GREEN}Workflow triggered successfully!${NC}"
    echo "Check status at: https://github.com/$REPO/actions"
else
    echo -e "\n${GREEN}Workflow triggered successfully!${NC}"
    echo "Run ID: $RUN_ID"
    
    # Wait a moment for the run to register
    sleep 3
    
    # Show run URL
    echo -e "\n${BLUE}View run at:${NC}"
    echo "https://github.com/$REPO/actions/runs/$RUN_ID"
    
    # Ask if user wants to watch the run
    echo -e "\n${YELLOW}Watch the run in terminal? (y/n)${NC}"
    read -r watch
    
    if [[ "$watch" == "y" ]]; then
        echo -e "\n${GREEN}Watching workflow run...${NC}"
        echo "(Press Ctrl+C to stop watching)"
        gh run watch "$RUN_ID" --repo "$REPO"
    fi
fi

# Show how to download artifacts later
echo -e "\n${BLUE}To download test reports later:${NC}"
echo "gh run download $RUN_ID --repo $REPO"

echo -e "\n${GREEN}Done!${NC}"