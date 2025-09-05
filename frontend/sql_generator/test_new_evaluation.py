#!/usr/bin/env python3
# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache 2.0.
# See the LICENSE.md file in the project root for full license information.

"""
Test script for the new parallel SQL evaluation system.
"""

import asyncio
import logging
from typing import List, Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Mock classes for testing
class MockState:
    def __init__(self, generated_sqls: List[str], generated_tests: List[tuple]):
        self.generated_sqls = generated_sqls
        self.generated_tests = generated_tests
        self.question = "How many schools are exclusively virtual?"
        self.full_mschema = "CREATE TABLE schools (id INT, name TEXT, type TEXT);"
        self.directives = ""
        self.evidence_for_template = ""
        self.dbmanager = type('obj', (object,), {'db_type': 'sqlite'})()
        self.gold_sql_examples = []
        self.filtered_tests = []
        self.test_answers = []

class MockEvaluatorOutput:
    def __init__(self, thinking: str, answers: List[str]):
        self.thinking = thinking
        self.answers = answers

class MockEvaluatorResult:
    def __init__(self, output: MockEvaluatorOutput):
        self.output = output

class MockEvaluatorAgent:
    def __init__(self, responses: Dict[str, List[str]]):
        """
        responses: Dict mapping SQL text to list of test results
        """
        self.responses = responses
        self.call_count = 0
    
    async def run(self, template: str, model_settings=None, deps=None):
        self.call_count += 1
        
        # Extract SQL from template to determine response
        sql_start = template.find("*** SQL Query to Evaluate: ***")
        sql_end = template.find("*** Unit Tests to Apply: ***")
        
        if sql_start != -1 and sql_end != -1:
            sql_section = template[sql_start:sql_end]
            
            # Find which SQL this is
            for sql_text, test_results in self.responses.items():
                if sql_text in sql_section:
                    return MockEvaluatorResult(
                        MockEvaluatorOutput(
                            thinking=f"Evaluated SQL {self.call_count}",
                            answers=test_results
                        )
                    )
        
        # Default response
        return MockEvaluatorResult(
            MockEvaluatorOutput(
                thinking="Default evaluation",
                answers=["Test #1: OK", "Test #2: OK", "Test #3: OK"]
            )
        )

class MockAgentsAndTools:
    def __init__(self, evaluator_agent):
        self.evaluator_agent = evaluator_agent


async def test_single_sql_evaluation():
    """Test evaluation of a single SQL."""
    logger.info("Testing single SQL evaluation...")
    
    # Setup test data
    sql = "SELECT COUNT(*) FROM schools WHERE type = 'virtual'"
    tests = [
        ("Test thinking", [
            "Check if query counts virtual schools",
            "Verify WHERE clause filters correctly",
            "Ensure COUNT aggregation is used"
        ])
    ]
    
    # Create mock evaluator with expected responses
    evaluator = MockEvaluatorAgent({
        sql: [
            "Test #1: OK",
            "Test #2: OK", 
            "Test #3: OK"
        ]
    })
    
    # Create state and agents
    state = MockState([sql], tests)
    agents = MockAgentsAndTools(evaluator)
    
    # Import and run evaluation
    from helpers.main_helpers.main_evaluation import evaluate_sql_candidates
    
    results = await evaluate_sql_candidates(state, agents)
    
    # Verify results
    assert len(results) == 1, f"Expected 1 result, got {len(results)}"
    thinking, answers = results[0]
    assert len(answers) == 1, f"Expected 1 SQL verdict, got {len(answers)}"
    assert "SQL #1:" in answers[0], f"Expected SQL #1 verdict, got {answers[0]}"
    assert "OK, OK, OK" in answers[0], f"Expected all OK, got {answers[0]}"
    
    logger.info("✓ Single SQL evaluation test passed")


async def test_parallel_sql_evaluation():
    """Test parallel evaluation of multiple SQLs."""
    logger.info("Testing parallel SQL evaluation...")
    
    # Setup test data
    sqls = [
        "SELECT COUNT(*) FROM schools WHERE type = 'virtual'",
        "SELECT COUNT(*) FROM schools WHERE type='virtual' AND status='active'",
        "SELECT COUNT(DISTINCT id) FROM schools WHERE type = 'virtual'"
    ]
    tests = [
        ("Test thinking", [
            "Check if query counts virtual schools",
            "Verify WHERE clause filters correctly",
            "Ensure COUNT aggregation is used"
        ])
    ]
    
    # Create mock evaluator with different responses for each SQL
    evaluator = MockEvaluatorAgent({
        sqls[0]: [
            "Test #1: OK",
            "Test #2: OK",
            "Test #3: OK"
        ],
        sqls[1]: [
            "Test #1: OK",
            "Test #2: KO - includes active status filter not in question",
            "Test #3: OK"
        ],
        sqls[2]: [
            "Test #1: OK",
            "Test #2: OK",
            "Test #3: OK"
        ]
    })
    
    # Create state and agents
    state = MockState(sqls, tests)
    agents = MockAgentsAndTools(evaluator)
    
    # Import and run evaluation
    from helpers.main_helpers.main_evaluation import evaluate_sql_candidates
    
    results = await evaluate_sql_candidates(state, agents)
    
    # Verify results
    assert len(results) == 1, f"Expected 1 result, got {len(results)}"
    thinking, answers = results[0]
    assert len(answers) == 3, f"Expected 3 SQL verdicts, got {len(answers)}"
    
    # Check each SQL verdict
    assert "SQL #1:" in answers[0] and "OK, OK, OK" in answers[0]
    assert "SQL #2:" in answers[1] and "KO" in answers[1]
    assert "SQL #3:" in answers[2] and "OK, OK, OK" in answers[2]
    
    logger.info("✓ Parallel SQL evaluation test passed")


async def test_case_determination():
    """Test case determination logic (A/B/C/D)."""
    logger.info("Testing case determination...")
    
    from helpers.main_helpers.main_evaluation import determine_evaluation_case
    
    # Test Case A: Single perfect SQL
    answers_a = ["SQL #1: OK, OK, OK"]
    case, details = determine_evaluation_case(answers_a)
    assert case == "A", f"Expected case A, got {case}"
    assert len(details['perfect_sqls']) == 1
    logger.info("✓ Case A detection passed")
    
    # Test Case B: Multiple perfect SQLs
    answers_b = [
        "SQL #1: OK, OK, OK",
        "SQL #2: OK, OK, OK"
    ]
    case, details = determine_evaluation_case(answers_b)
    assert case == "B", f"Expected case B, got {case}"
    assert len(details['perfect_sqls']) == 2
    logger.info("✓ Case B detection passed")
    
    # Test Case C: Above threshold but not perfect
    answers_c = [
        "SQL #1: OK, OK, KO - minor issue",
        "SQL #2: OK, KO - issue, KO - issue"
    ]
    case, details = determine_evaluation_case(answers_c, threshold=0.6)
    assert case == "C", f"Expected case C, got {case}"
    assert len(details['above_threshold']) == 1  # Only SQL #1 is above 60%
    logger.info("✓ Case C detection passed")
    
    # Test Case D: All failed
    answers_d = [
        "SQL #1: KO - issue, KO - issue, KO - issue",
        "SQL #2: KO - issue, OK, KO - issue"
    ]
    case, details = determine_evaluation_case(answers_d, threshold=0.9)
    assert case == "D", f"Expected case D, got {case}"
    assert len(details['below_threshold']) == 2
    logger.info("✓ Case D detection passed")


async def main():
    """Run all tests."""
    logger.info("Starting evaluation system tests...")
    
    try:
        await test_single_sql_evaluation()
        await test_parallel_sql_evaluation()
        await test_case_determination()
        
        logger.info("\n✅ All tests passed successfully!")
        
    except AssertionError as e:
        logger.error(f"\n❌ Test failed: {e}")
        raise
    except Exception as e:
        logger.error(f"\n❌ Unexpected error: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())