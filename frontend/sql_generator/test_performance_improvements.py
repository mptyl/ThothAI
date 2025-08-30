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
Performance improvement verification test for Phase 4 completion.
"""

import sys
import pickle
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))


def test_memory_usage_comparison():
    """Compare memory usage between SystemState and lightweight dependencies."""
    print("🔍 Testing memory usage improvements...")
    
    try:
        from model.state_factory import StateFactory
        from model.system_state import SystemState
        
        # Create a realistic SystemState with data
        state = StateFactory.create_minimal("How many active users are there?")
        
        # Add some realistic data to make the state larger
        state.keywords = ["users", "active", "count", "total", "database"]
        state.evidence = [
            "Users table contains user information",
            "Active flag indicates user status",
            "Created_at field shows user registration date"
        ]
        
        # Simulate some database schema
        state.database.full_schema = {
            "users": {
                "table_description": "User accounts table",
                "columns": {
                    "id": {"type": "integer", "description": "User ID"},
                    "email": {"type": "varchar", "description": "User email"},
                    "active": {"type": "boolean", "description": "User status"},
                    "created_at": {"type": "timestamp", "description": "Registration date"}
                }
            },
            "orders": {
                "table_description": "User orders table", 
                "columns": {
                    "id": {"type": "integer", "description": "Order ID"},
                    "user_id": {"type": "integer", "description": "User foreign key"},
                    "amount": {"type": "decimal", "description": "Order amount"},
                    "status": {"type": "varchar", "description": "Order status"}
                }
            }
        }
        
        # Measure SystemState size using model_dump instead of pickle
        import sys
        system_state_data = state.model_dump()
        system_state_size = sys.getsizeof(str(system_state_data))
        print(f"📊 Full SystemState size: {system_state_size:,} bytes")
        
        # Create lightweight dependencies
        kw_deps = StateFactory.create_agent_deps(state, "keyword_extraction")
        sql_deps = StateFactory.create_agent_deps(state, "sql_generation")
        validation_deps = StateFactory.create_agent_deps(state, "question_validation")
        
        # Measure lightweight dependency sizes
        kw_size = sys.getsizeof(str(kw_deps.model_dump()))
        sql_size = sys.getsizeof(str(sql_deps.model_dump()))
        validation_size = sys.getsizeof(str(validation_deps.model_dump()))
        
        print(f"📊 KeywordExtractionDeps size: {kw_size:,} bytes")
        print(f"📊 SqlGenerationDeps size: {sql_size:,} bytes")
        print(f"📊 ValidationDeps size: {validation_size:,} bytes")
        
        # Calculate improvements
        total_deps_size = kw_size + sql_size + validation_size
        memory_improvement = ((system_state_size - kw_size) / system_state_size) * 100
        sql_improvement = ((system_state_size - sql_size) / system_state_size) * 100
        
        print(f"\n📈 Memory Usage Improvements:")
        print(f"   • Keyword extraction: {memory_improvement:.1f}% reduction")
        print(f"   • SQL generation: {sql_improvement:.1f}% reduction")
        print(f"   • Combined 3 deps vs SystemState: {((system_state_size - total_deps_size) / system_state_size) * 100:.1f}% reduction")
        
        # Verify significant improvement (target: >50% reduction)
        if memory_improvement < 50:
            print(f"❌ Memory improvement {memory_improvement:.1f}% is less than target 50%")
            return False
        
        print("✅ Significant memory usage improvements achieved")
        return True
        
    except Exception as e:
        print(f"❌ Memory usage test failed: {e}")
        return False


def test_dependency_creation_performance():
    """Test performance of dependency creation via StateFactory."""
    print("\n🔍 Testing dependency creation performance...")
    
    try:
        import time
        from model.state_factory import StateFactory
        
        # Create a SystemState
        state = StateFactory.create_minimal("Test performance question")
        
        # Warm up
        for _ in range(10):
            StateFactory.create_agent_deps(state, "sql_generation")
        
        # Measure dependency creation time
        start_time = time.time()
        iterations = 1000
        
        for _ in range(iterations):
            sql_deps = StateFactory.create_agent_deps(state, "sql_generation")
            kw_deps = StateFactory.create_agent_deps(state, "keyword_extraction")
            val_deps = StateFactory.create_agent_deps(state, "question_validation")
        
        end_time = time.time()
        total_time = end_time - start_time
        avg_time_per_creation = (total_time / (iterations * 3)) * 1000  # milliseconds
        
        print(f"📊 Dependency creation performance:")
        print(f"   • {iterations * 3:,} dependency creations in {total_time:.3f} seconds")
        print(f"   • Average time per creation: {avg_time_per_creation:.3f}ms")
        
        # Target: <1ms per dependency creation
        if avg_time_per_creation > 1.0:
            print(f"❌ Dependency creation time {avg_time_per_creation:.3f}ms exceeds target 1.0ms")
            return False
        
        print("✅ Fast dependency creation performance achieved")
        return True
        
    except Exception as e:
        print(f"❌ Performance test failed: {e}")
        return False


def test_dependency_data_efficiency():
    """Test that dependencies contain only necessary data."""
    print("\n🔍 Testing dependency data efficiency...")
    
    try:
        from model.state_factory import StateFactory
        
        # Create a SystemState with lots of data
        state = StateFactory.create_minimal("Complex query with many tables")
        
        # Add substantial data
        state.keywords = ["users", "orders", "products", "sales", "analytics"]
        state.evidence = [f"Evidence item {i}" for i in range(20)]
        # Don't modify schema directly to avoid validation errors
        
        # Create different dependency types
        kw_deps = StateFactory.create_agent_deps(state, "keyword_extraction")
        sql_deps = StateFactory.create_agent_deps(state, "sql_generation")
        val_deps = StateFactory.create_agent_deps(state, "question_validation")
        
        # Test KeywordExtractionDeps efficiency
        required_kw_fields = {"question", "scope", "language"}
        actual_kw_fields = set(kw_deps.model_fields.keys())
        extra_kw_fields = actual_kw_fields - required_kw_fields
        
        if extra_kw_fields:
            print(f"❌ KeywordExtractionDeps has extra fields: {extra_kw_fields}")
            return False
        print("✅ KeywordExtractionDeps contains only necessary fields")
        
        # Test SqlGenerationDeps efficiency
        required_sql_fields = {"db_type", "db_schema_str", "treat_empty_result_as_error", 
                              "last_SQL", "last_execution_error", "last_generation_success"}
        actual_sql_fields = set(sql_deps.model_fields.keys())
        missing_sql_fields = required_sql_fields - actual_sql_fields
        
        if missing_sql_fields:
            print(f"❌ SqlGenerationDeps missing required fields: {missing_sql_fields}")
            return False
        print("✅ SqlGenerationDeps contains all necessary fields")
        
        # Test ValidationDeps efficiency  
        required_val_fields = {"question", "scope", "language", "workspace"}
        actual_val_fields = set(val_deps.model_fields.keys())
        extra_val_fields = actual_val_fields - required_val_fields
        
        if extra_val_fields:
            print(f"❌ ValidationDeps has extra fields: {extra_val_fields}")
            return False
        print("✅ ValidationDeps contains only necessary fields")
        
        return True
        
    except Exception as e:
        print(f"❌ Data efficiency test failed: {e}")
        return False


def test_type_safety_improvements():
    """Test that dependencies provide strong type safety."""
    print("\n🔍 Testing type safety improvements...")
    
    try:
        from model.state_factory import StateFactory
        from model.agent_dependencies import KeywordExtractionDeps, ValidationDeps
        from model.sql_generation_deps import SqlGenerationDeps
        
        # Create SystemState
        state = StateFactory.create_minimal("Type safety test")
        
        # Create dependencies
        kw_deps = StateFactory.create_agent_deps(state, "keyword_extraction")
        sql_deps = StateFactory.create_agent_deps(state, "sql_generation")
        val_deps = StateFactory.create_agent_deps(state, "question_validation")
        
        # Test type annotations
        type_checks = [
            (kw_deps, KeywordExtractionDeps, "KeywordExtractionDeps"),
            (sql_deps, SqlGenerationDeps, "SqlGenerationDeps"),
            (val_deps, ValidationDeps, "ValidationDeps")
        ]
        
        for deps, expected_type, name in type_checks:
            if not isinstance(deps, expected_type):
                print(f"❌ {name}: Expected {expected_type}, got {type(deps)}")
                return False
            print(f"✅ {name}: Correct type annotation")
        
        # Test field validation
        try:
            # This should work
            KeywordExtractionDeps(
                question="Valid question",
                scope="Valid scope", 
                language="English"
            )
            print("✅ Valid dependency creation works")
            
            # Test with missing required field (this should fail)
            try:
                KeywordExtractionDeps(
                    question="Valid question",
                    scope="Valid scope"
                    # Missing language field
                )
                print("❌ Invalid dependency creation should have failed")
                return False
            except Exception:
                print("✅ Invalid dependency creation properly rejected")
        
        except Exception as e:
            print(f"❌ Type validation test failed: {e}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Type safety test failed: {e}")
        return False


def main():
    """Main performance improvement test function."""
    print("🚀 Starting Phase 4 Performance Improvement Tests...\n")
    
    test_results = []
    
    # Test 1: Memory usage improvements
    test_results.append(test_memory_usage_comparison())
    
    # Test 2: Dependency creation performance
    test_results.append(test_dependency_creation_performance())
    
    # Test 3: Data efficiency
    test_results.append(test_dependency_data_efficiency())
    
    # Test 4: Type safety improvements
    test_results.append(test_type_safety_improvements())
    
    # Summary
    passed = sum(test_results)
    total = len(test_results)
    
    print(f"\n📊 Performance Improvement Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 PERFORMANCE IMPROVEMENTS VERIFIED!")
        print("✅ Significant memory usage reduction achieved")
        print("✅ Fast dependency creation performance")
        print("✅ Efficient data structures with only necessary fields")
        print("✅ Strong type safety with Pydantic validation")
        print("🚀 Phase 4 performance objectives met successfully")
        return True
    else:
        print("❌ Some performance improvement tests FAILED!")
        print("Performance objectives not fully met")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)