# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

"""
Pipeline Integration Test for Phase 4 completion.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))


def test_pipeline_imports():
    """Test that all pipeline components can be imported correctly."""
    print("🔍 Testing pipeline component imports...")
    
    try:
        # Test main pipeline components
        from helpers.main_helpers.main_preprocessing_phases import (
            _validate_question_phase,
            _extract_keywords_phase, 
            _retrieve_context_phase
        )
        print("✅ Preprocessing phases imported successfully")
        
        from helpers.main_helpers.main_generation_phases import (
            _generate_sql_candidates_phase,
            _evaluate_and_select_phase
        )
        print("✅ Generation phases imported successfully")
        
        from helpers.main_helpers.main_sql_generation import generate_sql_units
        print("✅ SQL generation helper imported successfully")
        
        from model.state_factory import StateFactory
        print("✅ StateFactory imported successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Import test failed: {e}")
        return False


def test_state_factory_integration():
    """Test StateFactory integration with SQL generation dependencies."""
    print("\n🔍 Testing StateFactory integration...")
    
    try:
        from model.state_factory import StateFactory
        from model.system_state import SystemState
        from model.sql_generation_deps import SqlGenerationDeps
        
        # Create a test SystemState
        state = StateFactory.create_minimal("How many users are active?")
        print(f"✅ Created SystemState: {type(state).__name__}")
        
        # Test SQL generation dependency creation
        sql_deps = StateFactory.create_agent_deps(state, "sql_generation")
        print(f"✅ Created SQL dependencies: {type(sql_deps).__name__}")
        
        # Verify the dependency type
        if not isinstance(sql_deps, SqlGenerationDeps):
            print(f"❌ Expected SqlGenerationDeps, got {type(sql_deps)}")
            return False
            
        print("✅ SQL dependency type verification passed")
        
        # Test that required fields are present
        required_fields = ['db_type', 'db_schema_str', 'treat_empty_result_as_error']
        for field in required_fields:
            if not hasattr(sql_deps, field):
                print(f"❌ Missing required field: {field}")
                return False
            print(f"✅ Field '{field}' present: {getattr(sql_deps, field)}")
        
        return True
        
    except Exception as e:
        print(f"❌ StateFactory integration test failed: {e}")
        return False


def test_main_sql_generation_updates():
    """Test that main_sql_generation.py uses StateFactory correctly."""
    print("\n🔍 Testing main_sql_generation.py updates...")
    
    try:
        # Check that the file imports StateFactory
        with open("helpers/main_helpers/main_sql_generation.py", "r") as f:
            content = f.read()
        
        # Check for StateFactory import
        if "from model.state_factory import StateFactory" not in content:
            print("❌ StateFactory import missing from main_sql_generation.py")
            return False
        print("✅ StateFactory import found")
        
        # Check for StateFactory usage
        if "StateFactory.create_agent_deps(state, \"sql_generation\")" not in content:
            print("❌ StateFactory usage not found in main_sql_generation.py")
            return False
        print("✅ StateFactory usage found")
        
        # Check that manual SqlGenerationDeps creation was removed
        if "SqlGenerationDeps(" in content:
            print("❌ Manual SqlGenerationDeps creation still present")
            return False
        print("✅ Manual SqlGenerationDeps creation removed")
        
        return True
        
    except Exception as e:
        print(f"❌ main_sql_generation.py test failed: {e}")
        return False


def test_helper_functions_consistency():
    """Test that all helper functions use consistent lightweight dependencies."""
    print("\n🔍 Testing helper functions consistency...")
    
    helper_files = [
        "helpers/main_helpers/main_keyword_extraction.py",
        "helpers/main_helpers/main_translation_validation.py", 
        "helpers/translation_and_validation.py",
        "keyword_extraction.py",
        "helpers/main_helpers/main_sql_generation.py"
    ]
    
    failed_files = []
    
    for file_path in helper_files:
        try:
            with open(file_path, "r") as f:
                content = f.read()
            
            # Check for StateFactory import (if the file uses agents)
            has_agent_calls = "agent.run(" in content or "agents_and_tools" in content
            has_statefactory_import = "from model.state_factory import StateFactory" in content
            
            if has_agent_calls and not has_statefactory_import:
                print(f"❌ {file_path}: Has agent calls but missing StateFactory import")
                failed_files.append(file_path)
                continue
            
            # Check for StateFactory usage (if the file has the import)
            if has_statefactory_import:
                has_statefactory_usage = "StateFactory.create_agent_deps" in content
                if not has_statefactory_usage:
                    print(f"❌ {file_path}: Has StateFactory import but no usage")
                    failed_files.append(file_path)
                    continue
            
            print(f"✅ {file_path}: Consistent lightweight dependency usage")
            
        except Exception as e:
            print(f"❌ Error checking {file_path}: {e}")
            failed_files.append(file_path)
    
    return len(failed_files) == 0


def test_no_direct_systemstate_to_agents():
    """Test that no agents receive SystemState directly anymore."""
    print("\n🔍 Testing that no agents receive SystemState directly...")
    
    # Files that should not have direct SystemState to agent patterns
    pipeline_files = [
        "helpers/main_helpers/main_keyword_extraction.py",
        "helpers/main_helpers/main_translation_validation.py",
        "helpers/translation_and_validation.py", 
        "keyword_extraction.py",
        "helpers/main_helpers/main_sql_generation.py"
    ]
    
    failed_files = []
    
    for file_path in pipeline_files:
        try:
            with open(file_path, "r") as f:
                content = f.read()
            
            # Check for direct SystemState usage in agent calls
            lines = content.split('\n')
            for line_num, line in enumerate(lines, 1):
                stripped = line.strip()
                if "deps=state" in stripped and not stripped.startswith('#'):
                    # Check if it's actually passing SystemState directly
                    if ("deps=state," in stripped or "deps=state)" in stripped) and "deps=state_" not in stripped:
                        print(f"❌ {file_path}:{line_num}: Direct SystemState to agent: {stripped}")
                        failed_files.append(file_path)
                        break
            
            if file_path not in failed_files:
                print(f"✅ {file_path}: No direct SystemState to agents")
                
        except Exception as e:
            print(f"❌ Error checking {file_path}: {e}")
            failed_files.append(file_path)
    
    return len(failed_files) == 0


def main():
    """Main pipeline integration test function."""
    print("🚀 Starting Phase 4 Pipeline Integration Tests...\n")
    
    test_results = []
    
    # Test 1: Pipeline imports
    test_results.append(test_pipeline_imports())
    
    # Test 2: StateFactory integration
    test_results.append(test_state_factory_integration())
    
    # Test 3: main_sql_generation.py updates
    test_results.append(test_main_sql_generation_updates())
    
    # Test 4: Helper functions consistency
    test_results.append(test_helper_functions_consistency())
    
    # Test 5: No direct SystemState to agents
    test_results.append(test_no_direct_systemstate_to_agents())
    
    # Summary
    passed = sum(test_results)
    total = len(test_results)
    
    print(f"\n📊 Pipeline Integration Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 Phase 4 (Pipeline Integration) COMPLETED SUCCESSFULLY!")
        print("✅ All pipeline components use StateFactory for lightweight dependencies")
        print("✅ No agents receive full SystemState anymore")
        print("✅ Pipeline maintains full functionality with optimized data flow")
        print("🚀 Ready to proceed with Phase 5 (Complete Testing)")
        return True
    else:
        print("❌ Phase 4 pipeline integration tests FAILED!")
        print("Some pipeline components still have integration issues")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)