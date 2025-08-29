#!/bin/bash
# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

# Test script for CA Schools SQL generation via direct curl
# This script simulates the exact request that NextJS makes to the backend

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PORT=8001  # Correct port for local SQL generator
BASE_URL="http://localhost:${PORT}"

echo -e "${YELLOW}Testing SQL Generator on port ${PORT}...${NC}"

# Test function
test_sql_generation() {
    local question="$1"
    local workspace_id="$2"
    local username="${3:-marco}"
    local functionality_level="${4:-BASIC}"
    
    echo -e "\n${GREEN}Testing: ${question}${NC}"
    echo "Workspace: ${workspace_id}, User: ${username}, Level: ${functionality_level}"
    echo "----------------------------------------"
    
    # Make the request with proper headers matching NextJS
    curl -X POST "${BASE_URL}/generate-sql" \
        -H "Content-Type: application/json" \
        -H "Accept: text/plain" \
        -H "X-Username: ${username}" \
        --no-buffer \
        -d "{
            \"workspace_id\": ${workspace_id},
            \"question\": \"${question}\",
            \"functionality_level\": \"${functionality_level}\",
            \"flags\": {
                \"use_schema\": true,
                \"use_examples\": true,
                \"use_lsh\": true,
                \"use_vector\": true
            }
        }" 2>/dev/null
    
    echo -e "\n----------------------------------------\n"
}

# Check if server is running
echo -e "${YELLOW}Checking if SQL Generator is running on port ${PORT}...${NC}"
if ! curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}/health" | grep -q "200"; then
    echo -e "${RED}SQL Generator is not running on port ${PORT}!${NC}"
    echo "Please start it with: cd sql_generator && python -m uvicorn main:app --port ${PORT}"
    exit 1
fi
echo -e "${GREEN}Server is running!${NC}\n"

# Run test cases
echo -e "${YELLOW}Running CA Schools test cases...${NC}"

# Test 1: Simple count query
test_sql_generation \
    "How many schools are exclusively virtual?" \
    4 \
    "marco" \
    "BASIC"

# Test 2: Complex query with Math scores
test_sql_generation \
    "How many schools with an average score in Math greater than 400 in the SAT test are exclusively virtual?" \
    4 \
    "marco" \
    "BASIC"

# Test 3: Query with different functionality level
test_sql_generation \
    "What are the top 5 schools by Math scores?" \
    4 \
    "marco" \
    "ADVANCED"

echo -e "${GREEN}Tests completed!${NC}"