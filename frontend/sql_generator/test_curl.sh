#!/bin/bash
# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache License 2.0.

# Configuration
PORT=8001
BASE_URL="http://localhost:${PORT}"

echo "Testing SQL Generator on port ${PORT}..."

# Simple test
echo "Test 1: How many schools are exclusively virtual?"
curl -X POST "${BASE_URL}/generate-sql" \
    -H "Content-Type: application/json" \
    -H "Accept: text/plain" \
    -H "X-Username: marco" \
    --no-buffer \
    -d '{
        "workspace_id": 4,
        "question": "How many schools are exclusively virtual?",
        "functionality_level": "BASIC",
        "flags": {
            "show_sql": true,
            "explain_generated_query": true,
            "treat_empty_result_as_error": false,
            "belt_and_suspenders": false
        }
    }'

echo ""
echo "----------------------------------------"
echo ""

# Complex test
echo "Test 2: Schools with Math scores > 400"
curl -X POST "${BASE_URL}/generate-sql" \
    -H "Content-Type: application/json" \
    -H "Accept: text/plain" \
    -H "X-Username: marco" \
    --no-buffer \
    -d '{
        "workspace_id": 4,
        "question": "How many schools with an average score in Math greater than 400 in the SAT test are exclusively virtual?",
        "functionality_level": "BASIC",
        "flags": {
            "show_sql": true,
            "explain_generated_query": true,
            "treat_empty_result_as_error": false,
            "belt_and_suspenders": false
        }
    }'

echo ""
echo "Tests completed!"