#!/usr/bin/env python
# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache 2.0.
# See the LICENSE.md file in the project root for full license information.

"""
Test script for the simplified evaluation flow.

This script tests the new simplified evaluation system that:
1. Generates tests (7-14 tests)
2. Evaluates each SQL against each test
3. Automatically selects the best SQL based on pass rate
"""

import asyncio
import logging
from typing import List, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MockState:
    """Mock state object for testing"""
    def __init__(self):
        self.question = "Please list the lowest three eligible free rates for students aged 5-17 in continuation schools."
        self.generated_sqls = [
            "SELECT school_name, eligible_free_rate FROM schools WHERE type='continuation' ORDER BY eligible_free_rate LIMIT 3",
            "SELECT school_name, eligible_free_rate FROM schools WHERE school_type='continuation' ORDER BY eligible_free_rate ASC LIMIT 3",
            "SELECT name, rate FROM school_data WHERE category='continuation' ORDER BY rate LIMIT 3"
        ]
        self.generated_tests = [
            ("Test generation thinking", [
                "The SQL query should select school names and eligible free rates",
                "The SQL query should filter for continuation schools",
                "The SQL query should order results by eligible free rate in ascending order",
                "The SQL query should limit results to 3 records",
                "The SQL query should handle NULL values appropriately",
                "The SQL query should use correct table and column names",
                "The SQL query should include proper JOIN conditions if needed"
            ])
        ]
        self.functionality_level = "BASIC"
        self.evaluation_results = None  # Will be set during test


def simulate_evaluation_results(sqls: List[str], tests: List[str]) -> List[str]:
    """
    Simulate evaluation results for testing.
    Returns evaluation in format: "SQL #n: OK, OK, KO - reason, ..."
    """
    results = []
    
    # SQL #1: 6/7 tests pass (85.7%)
    results.append("SQL #1: OK, OK, OK, OK, OK, OK, KO - incorrect column name for school type")
    
    # SQL #2: 7/7 tests pass (100%)
    results.append("SQL #2: OK, OK, OK, OK, OK, OK, OK")
    
    # SQL #3: 4/7 tests pass (57.1%)
    results.append("SQL #3: OK, KO - wrong column names, OK, OK, KO - no NULL handling, KO - wrong table name, OK")
    
    return results


async def test_simplified_flow():
    """Test the simplified evaluation flow"""
    
    logger.info("Starting simplified evaluation flow test...")
    
    # Create mock state
    state = MockState()
    
    # Simulate evaluation results
    evaluation_results = simulate_evaluation_results(
        state.generated_sqls,
        state.generated_tests[0][1]
    )
    
    # Set evaluation results in state
    state.evaluation_results = ("Evaluation thinking", evaluation_results)
    
    logger.info(f"Generated {len(state.generated_sqls)} SQLs")
    logger.info(f"Generated {len(state.generated_tests[0][1])} tests")
    logger.info(f"Evaluation results: {evaluation_results}")
    
    # Import and test the enhanced evaluation flow
    from helpers.main_helpers.enhanced_evaluation_flow import EnhancedEvaluationFlow
    
    # Create a mock agents_and_tools object
    class MockAgentsAndTools:
        def __init__(self):
            self.evaluator_agent = True  # Just needs to exist
    
    agents_and_tools = MockAgentsAndTools()
    
    # Create evaluation flow with 90% threshold
    eval_flow = EnhancedEvaluationFlow(
        agents_and_tools, 
        session_id="test_session",
        evaluation_threshold=90
    )
    
    # Test pass rate calculation
    pass_rates = eval_flow.calculate_pass_rates(evaluation_results)
    logger.info(f"Calculated pass rates: {pass_rates}")
    
    # Test direct selection
    selected_index, selected_sql, status, best_rate = eval_flow.select_best_sql_directly(
        pass_rates,
        state.generated_sqls
    )
    
    logger.info(f"Selected SQL index: {selected_index}")
    logger.info(f"Selected status: {status}")
    logger.info(f"Best pass rate: {best_rate:.1%}")
    
    # Test the full simplified evaluation
    try:
        result = await eval_flow.run_simplified_evaluation(state)
        
        logger.info(f"Final status: {result.status}")
        logger.info(f"Selected SQL index: {result.selected_sql_index}")
        logger.info(f"Evaluation case: {result.evaluation_case}")
        logger.info(f"Best pass rate: {result.best_pass_rate:.1%}")
        
        if result.selected_sql:
            logger.info(f"Selected SQL: {result.selected_sql}")
        
        # Verify expectations
        assert result.selected_sql_index == 1, f"Expected SQL #2 (index 1) to be selected, got {result.selected_sql_index}"
        assert result.best_pass_rate == 1.0, f"Expected 100% pass rate, got {result.best_pass_rate}"
        assert result.status.value == "GOLD", f"Expected GOLD status, got {result.status.value}"
        
        logger.info("✓ All tests passed!")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(test_simplified_flow())