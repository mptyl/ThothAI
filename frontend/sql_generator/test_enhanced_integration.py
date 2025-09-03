#!/usr/bin/env python

# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

"""
Test script to verify that the enhanced evaluation flow integration works correctly.
This test verifies:
1. Dynamic threshold support in enhanced evaluation flow
2. Template rendering with dynamic threshold
3. Integration with main generation phases
"""

import asyncio
import logging
from unittest.mock import Mock, MagicMock
from helpers.main_helpers.enhanced_evaluation_flow import EnhancedEvaluationFlow, run_enhanced_evaluation_flow

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_mock_state():
    """Create a mock state object with test data"""
    state = Mock()
    
    # Basic state properties
    state.question = "How many schools are exclusively virtual?"
    state.workspace = {'evaluation_threshold': 85}  # Test with 85% threshold
    state.session_id = 'test_session_123'
    
    # Generated SQLs for testing
    state.generated_sqls = [
        "SELECT COUNT(*) FROM schools WHERE type = 'virtual' AND physical_location IS NULL",
        "SELECT COUNT(id) FROM schools WHERE virtual_only = 1",
        "SELECT SUM(CASE WHEN type = 'virtual' THEN 1 ELSE 0 END) FROM schools"
    ]
    
    # Mock test data
    state.generated_tests = [(
        "Test generation thinking", 
        ["Test 1: Should count only virtual schools", "Test 2: Should exclude hybrid schools", "Test 3: Should handle NULL values"]
    )]
    
    # Database info
    state.full_mschema = "CREATE TABLE schools (id INT PRIMARY KEY, name VARCHAR(100), type VARCHAR(50), physical_location VARCHAR(200), virtual_only TINYINT)"
    state.used_mschema = state.full_mschema
    state.dbmanager = Mock()
    state.dbmanager.db_type = 'mysql'
    
    # Optional fields
    state.directives = "Focus on schools that are exclusively virtual"
    state.evidence_for_template = "Virtual schools have no physical location and virtual_only = 1"
    
    return state

def create_mock_agents_and_tools():
    """Create mock agents and tools"""
    agents_and_tools = Mock()
    
    # Mock evaluator agent
    evaluator_agent = Mock()
    evaluator_result = Mock()
    evaluator_result.output = Mock()
    evaluator_result.output.thinking = "Evaluation thinking for 85% threshold test"
    evaluator_result.output.answers = [
        "SQL #1: OK, OK, KO - missing join condition", 
        "SQL #2: OK, OK, OK",
        "SQL #3: OK, KO - wrong aggregation, OK"
    ]
    evaluator_agent.run = MagicMock(return_value=evaluator_result)
    agents_and_tools.evaluator_agent = evaluator_agent
    
    return agents_and_tools

async def test_enhanced_evaluation_flow():
    """Test the enhanced evaluation flow with dynamic threshold"""
    logger.info("Starting enhanced evaluation flow test...")
    
    try:
        # Create test data
        state = create_mock_state()
        agents_and_tools = create_mock_agents_and_tools()
        
        # Test the enhanced evaluation flow
        logger.info("Testing enhanced evaluation flow with 85% threshold...")
        
        enhanced_result, eval_logs = await run_enhanced_evaluation_flow(
            state, 
            agents_and_tools, 
            session_id='test_session_123',
            evaluation_threshold=85
        )
        
        logger.info(f"Enhanced evaluation result: {enhanced_result}")
        logger.info(f"Result status: {enhanced_result.status}")
        logger.info(f"Evaluation case: {enhanced_result.evaluation_case}")
        logger.info(f"Selected SQL index: {getattr(enhanced_result, 'selected_sql_index', 'None')}")
        logger.info(f"Processing time: {getattr(enhanced_result, 'processing_time_ms', 'None')} ms")
        
        # Test threshold integration
        flow = EnhancedEvaluationFlow(agents_and_tools, session_id='test', evaluation_threshold=85)
        logger.info(f"Flow threshold: {flow.evaluation_threshold}%")
        logger.info(f"Flow threshold ratio: {flow.threshold_ratio}")
        
        # Test pass rate classification
        test_pass_rates = {
            "SQL #1": 0.67,  # Below threshold (67% < 85%)
            "SQL #2": 1.0,   # Perfect (100%)
            "SQL #3": 0.87   # Borderline (87% >= 85% but < 100%)
        }
        
        case, perfect_sqls, borderline_sqls, failed_sqls = flow.classify_evaluation_case(test_pass_rates)
        logger.info(f"Classification test - Case: {case}")
        logger.info(f"Perfect SQLs: {perfect_sqls}")
        logger.info(f"Borderline SQLs (>={flow.evaluation_threshold}%): {borderline_sqls}")
        logger.info(f"Failed SQLs (<{flow.evaluation_threshold}%): {failed_sqls}")
        
        # Verify threshold integration works correctly
        assert flow.evaluation_threshold == 85, f"Expected threshold 85, got {flow.evaluation_threshold}"
        assert flow.threshold_ratio == 0.85, f"Expected ratio 0.85, got {flow.threshold_ratio}"
        assert "SQL #3" in borderline_sqls, f"SQL #3 (87%) should be borderline for 85% threshold"
        assert "SQL #1" in failed_sqls, f"SQL #1 (67%) should be failed for 85% threshold"
        
        logger.info("✅ Enhanced evaluation flow test PASSED!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Enhanced evaluation flow test FAILED: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

def test_template_threshold_support():
    """Test that templates support dynamic threshold"""
    logger.info("Testing template threshold support...")
    
    try:
        from helpers.template_preparation import TemplateLoader
        
        # Test evaluator supervisor template with dynamic threshold
        template_content = TemplateLoader.format(
            'user_evaluator_supervisor',
            safe=True,
            QUESTION="Test question",
            DATABASE_SCHEMA="Test schema", 
            BORDERLINE_SQLS="Test SQL",
            INITIAL_EVALUATION="Test evaluation",
            TEST_DETAILS="Test details",
            INITIAL_THINKING="Test thinking",
            GOLD_SQL_EXAMPLES="Test examples",
            EVALUATION_THRESHOLD=75
        )
        
        # Verify that the threshold is properly substituted
        assert "75-99%" in template_content, "Template should contain dynamic threshold range"
        assert "between 75-99%" in template_content, "Template should reference dynamic threshold in text"
        
        logger.info("✅ Template threshold support test PASSED!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Template threshold support test FAILED: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

async def main():
    """Run all tests"""
    logger.info("=" * 50)
    logger.info("Enhanced Evaluation Flow Integration Tests")
    logger.info("=" * 50)
    
    results = []
    
    # Test enhanced evaluation flow
    results.append(await test_enhanced_evaluation_flow())
    
    # Test template support
    results.append(test_template_threshold_support())
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    logger.info("=" * 50)
    logger.info(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All tests PASSED! Enhanced evaluation flow integration is working correctly.")
    else:
        logger.error(f"💥 {total - passed} test(s) FAILED!")
    
    return passed == total

if __name__ == "__main__":
    asyncio.run(main())