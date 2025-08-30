# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Comprehensive System Test for Phase 5 - Complete Testing.
Tests the entire SQL generation pipeline with refactored architecture.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))


def test_system_state_creation():
    """Test that SystemState can be created and configured properly."""
    print("🔍 Testing SystemState creation and configuration...")
    
    try:
        from model.state_factory import StateFactory
        from model.system_state import SystemState
        from datetime import datetime
        from tzlocal import get_localzone
        
        # Test minimal creation
        state = StateFactory.create_minimal("How many active users are there?")
        
        # Verify core structure
        assert hasattr(state, 'request'), "Missing request context"
        assert hasattr(state, 'database'), "Missing database context"
        assert hasattr(state, 'semantic'), "Missing semantic context"
        assert hasattr(state, 'schemas'), "Missing schema derivations"
        assert hasattr(state, 'generation'), "Missing generation results"
        assert hasattr(state, 'execution'), "Missing execution state"
        assert hasattr(state, 'services'), "Missing external services"
        
        print(f"✅ SystemState created with {len(state.model_fields)} contexts")
        
        # Test request context
        assert state.request.question == "How many active users are there?"
        assert state.request.username == "test_user"
        assert state.request.functionality_level == "BASIC"
        print("✅ Request context properly initialized")
        
        # Test database context
        assert state.database.db_type == "postgresql"
        assert state.database.treat_empty_result_as_error == True
        print("✅ Database context properly initialized")
        
        # Test that contexts are separate objects
        assert id(state.request) != id(state.database), "Contexts should be separate objects"
        print("✅ Contexts are properly separated")
        
        return True
        
    except Exception as e:
        print(f"❌ SystemState creation test failed: {e}")
        return False


def test_state_factory_all_agent_types():
    """Test StateFactory creates all agent dependency types correctly."""
    print("\n🔍 Testing StateFactory with all agent types...")
    
    try:
        from model.state_factory import StateFactory
        
        # Create base state
        state = StateFactory.create_minimal("Test query for all agent types")
        
        # Test all supported agent types
        agent_types = [
            "keyword_extraction",
            "question_validation", 
            "test_generation",
            "question_translation",
            "sql_explanation",
            "ask_human",
            "sql_generation",
            "evaluator"
        ]
        
        created_deps = {}
        
        for agent_type in agent_types:
            try:
                deps = StateFactory.create_agent_deps(state, agent_type)
                created_deps[agent_type] = deps
                print(f"✅ {agent_type}: {type(deps).__name__}")
            except Exception as e:
                print(f"❌ {agent_type}: Failed - {e}")
                return False
        
        # Verify all were created
        assert len(created_deps) == len(agent_types), "Not all agent types created"
        
        # Test that dependencies are lightweight
        for agent_type, deps in created_deps.items():
            field_count = len(deps.model_fields)
            if field_count > 10:  # Reasonable limit
                print(f"❌ {agent_type}: Too many fields ({field_count})")
                return False
            print(f"✅ {agent_type}: Lightweight with {field_count} fields")
        
        return True
        
    except Exception as e:
        print(f"❌ StateFactory agent types test failed: {e}")
        return False


def test_legacy_compatibility():
    """Test that legacy SystemState properties still work."""
    print("\n🔍 Testing legacy SystemState compatibility...")
    
    try:
        from model.state_factory import StateFactory
        
        # Create state
        state = StateFactory.create_minimal("Legacy compatibility test")
        
        # Test legacy property access (should work via __getattr__)
        question = state.question
        assert question == "Legacy compatibility test", f"Expected test question, got {question}"
        print("✅ Legacy question property access works")
        
        username = state.username
        assert username == "test_user", f"Expected test_user, got {username}"
        print("✅ Legacy username property access works")
        
        functionality_level = state.functionality_level
        assert functionality_level == "BASIC", f"Expected BASIC, got {functionality_level}"
        print("✅ Legacy functionality_level property access works")
        
        # Test mutable properties
        state.keywords = ["test", "legacy", "keywords"]
        assert state.keywords == ["test", "legacy", "keywords"], "Keywords assignment failed"
        print("✅ Legacy keywords property assignment works")
        
        state.evidence = ["test evidence"]
        assert state.evidence == ["test evidence"], "Evidence assignment failed"
        print("✅ Legacy evidence property assignment works")
        
        # Test database properties
        db_type = state.database.db_type
        assert db_type == "postgresql", f"Expected postgresql, got {db_type}"
        print("✅ Database context access works")
        
        return True
        
    except Exception as e:
        print(f"❌ Legacy compatibility test failed: {e}")
        return False


def test_data_flow_integrity():
    """Test that data flows correctly through the system."""
    print("\n🔍 Testing data flow integrity...")
    
    try:
        from model.state_factory import StateFactory
        
        # Create state and simulate pipeline data flow
        state = StateFactory.create_minimal("Data flow test query")
        
        # Simulate Phase 1: Question validation (data input)
        original_question = state.request.question
        print(f"📊 Phase 1 - Question: {original_question}")
        
        # Simulate Phase 2: Keyword extraction (data modification)
        state.keywords = ["data", "flow", "test"]
        extracted_keywords = state.keywords
        assert extracted_keywords == ["data", "flow", "test"], "Keywords not preserved"
        print(f"📊 Phase 2 - Keywords: {extracted_keywords}")
        
        # Simulate Phase 3: Context retrieval (data enrichment)
        state.evidence = ["Test evidence for data flow"]
        evidence = state.evidence
        assert evidence == ["Test evidence for data flow"], "Evidence not preserved"
        print(f"📊 Phase 3 - Evidence: {len(evidence)} items")
        
        # Simulate Phase 4: SQL generation (result creation)
        state.generation.generated_sql = "SELECT COUNT(*) FROM users WHERE active = true;"
        generated_sql = state.generation.generated_sql
        assert "SELECT" in generated_sql, "Generated SQL not preserved"
        print(f"📊 Phase 4 - SQL: {generated_sql[:50]}...")
        
        # Test agent dependency creation preserves data
        kw_deps = StateFactory.create_agent_deps(state, "keyword_extraction")
        assert kw_deps.question == original_question, "Question not preserved in keyword deps"
        
        sql_deps = StateFactory.create_agent_deps(state, "sql_generation")
        assert sql_deps.db_type == "postgresql", "DB type not preserved in SQL deps"
        
        print("✅ Data integrity maintained throughout pipeline")
        return True
        
    except Exception as e:
        print(f"❌ Data flow integrity test failed: {e}")
        return False


def test_context_isolation():
    """Test that contexts are properly isolated and don't interfere."""
    print("\n🔍 Testing context isolation...")
    
    try:
        from model.state_factory import StateFactory
        
        # Create state
        state = StateFactory.create_minimal("Context isolation test")
        
        # Modify different contexts
        state.request.question  # Immutable - should not change
        original_question = state.request.question
        
        state.semantic.keywords = ["isolation", "test"]
        state.database.db_type = "mysql"  # Change database context
        state.generation.generated_sql = "SELECT 1;"
        
        # Verify contexts are isolated
        assert state.request.question == original_question, "Request context was modified"
        assert state.semantic.keywords == ["isolation", "test"], "Semantic context not updated"
        assert state.database.db_type == "mysql", "Database context not updated"
        assert state.generation.generated_sql == "SELECT 1;", "Generation context not updated"
        
        # Verify context independence
        request_id = id(state.request)
        semantic_id = id(state.semantic)
        database_id = id(state.database)
        generation_id = id(state.generation)
        
        assert request_id != semantic_id, "Request and semantic contexts not isolated"
        assert database_id != generation_id, "Database and generation contexts not isolated"
        assert semantic_id != database_id, "Semantic and database contexts not isolated"
        
        print("✅ Context isolation working correctly")
        return True
        
    except Exception as e:
        print(f"❌ Context isolation test failed: {e}")
        return False


def test_error_handling():
    """Test error handling in various scenarios."""
    print("\n🔍 Testing error handling scenarios...")
    
    try:
        from model.state_factory import StateFactory
        
        # Test invalid agent type
        state = StateFactory.create_minimal("Error handling test")
        
        try:
            StateFactory.create_agent_deps(state, "invalid_agent_type")
            print("❌ Should have failed with invalid agent type")
            return False
        except ValueError as e:
            assert "Unsupported agent type" in str(e), "Wrong error message"
            print("✅ Invalid agent type properly handled")
        
        # Test with None state
        try:
            StateFactory.create_agent_deps(None, "sql_generation")
            print("❌ Should have failed with None state")
            return False
        except AttributeError:
            print("✅ None state properly handled")
        
        # Test malformed dependency creation
        try:
            from model.agent_dependencies import KeywordExtractionDeps
            # Missing required fields
            KeywordExtractionDeps()
            print("❌ Should have failed with missing fields")
            return False
        except Exception:
            print("✅ Missing required fields properly handled")
        
        return True
        
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        return False


def main():
    """Main comprehensive system test function."""
    print("🚀 Starting Phase 5 Comprehensive System Tests...\n")
    
    test_results = []
    
    # Test 1: SystemState creation
    test_results.append(test_system_state_creation())
    
    # Test 2: StateFactory with all agent types
    test_results.append(test_state_factory_all_agent_types())
    
    # Test 3: Legacy compatibility
    test_results.append(test_legacy_compatibility())
    
    # Test 4: Data flow integrity
    test_results.append(test_data_flow_integrity())
    
    # Test 5: Context isolation
    test_results.append(test_context_isolation())
    
    # Test 6: Error handling
    test_results.append(test_error_handling())
    
    # Summary
    passed = sum(test_results)
    total = len(test_results)
    
    print(f"\n📊 Comprehensive System Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 COMPREHENSIVE SYSTEM TESTS PASSED!")
        print("✅ SystemState creation and configuration working")
        print("✅ StateFactory works with all agent types") 
        print("✅ Legacy compatibility maintained")
        print("✅ Data flow integrity preserved")
        print("✅ Context isolation working correctly")
        print("✅ Error handling robust and reliable")
        print("🚀 System ready for continued Phase 5 testing")
        return True
    else:
        print("❌ Some comprehensive system tests FAILED!")
        print("System has issues that need to be resolved")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)