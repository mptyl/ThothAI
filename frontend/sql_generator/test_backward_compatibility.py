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
Backward Compatibility Test for Phase 5 - Complete Testing.
Tests that legacy code still works with the refactored SystemState.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))


def test_legacy_property_access():
    """Test that legacy SystemState property access patterns still work."""
    print("🔍 Testing legacy property access patterns...")
    
    try:
        from model.state_factory import StateFactory
        
        # Create state
        state = StateFactory.create_minimal("Legacy compatibility test")
        
        # Test all legacy properties that should be accessible
        legacy_properties = [
            ('question', str, "Legacy compatibility test"),
            ('username', str, "test_user"),
            ('workspace_name', str, "Test Workspace"),
            ('functionality_level', str, "BASIC"),
            ('language', str, "English"),
            ('scope', str, "Test database for minimal SystemState"),
            ('started_at', object, None)  # datetime object
        ]
        
        for prop_name, prop_type, expected_value in legacy_properties:
            try:
                value = getattr(state, prop_name)
                if expected_value is not None and value != expected_value:
                    print(f"❌ {prop_name}: Expected '{expected_value}', got '{value}'")
                    return False
                if not isinstance(value, prop_type):
                    print(f"❌ {prop_name}: Expected type {prop_type.__name__}, got {type(value).__name__}")
                    return False
                print(f"✅ {prop_name}: {value}")
            except AttributeError as e:
                print(f"❌ {prop_name}: Property not accessible - {e}")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Legacy property access test failed: {e}")
        return False


def test_legacy_property_modification():
    """Test that legacy SystemState property modification still works."""
    print("\n🔍 Testing legacy property modification...")
    
    try:
        from model.state_factory import StateFactory
        
        # Create state
        state = StateFactory.create_minimal("Property modification test")
        
        # Test mutable property modifications
        test_modifications = [
            ('keywords', ["legacy", "modification", "test"]),
            ('evidence', ["Legacy evidence item 1", "Legacy evidence item 2"]),
            ('filtered_schema', {"test_table": {"table_description": "Test table for legacy compatibility", "columns": {}}}),
            ('generated_sql', "SELECT * FROM legacy_test;"),
        ]
        
        for prop_name, test_value in test_modifications:
            try:
                # Set the property
                setattr(state, prop_name, test_value)
                
                # Get the property back
                retrieved_value = getattr(state, prop_name)
                
                # Verify it was set correctly
                if retrieved_value != test_value:
                    print(f"❌ {prop_name}: Set {test_value}, got {retrieved_value}")
                    return False
                
                print(f"✅ {prop_name}: Successfully set and retrieved")
                
            except Exception as e:
                print(f"❌ {prop_name}: Modification failed - {e}")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Legacy property modification test failed: {e}")
        return False


def test_legacy_immutable_properties():
    """Test that immutable properties correctly prevent modification."""
    print("\n🔍 Testing legacy immutable property protection...")
    
    try:
        from model.state_factory import StateFactory
        
        # Create state
        state = StateFactory.create_minimal("Immutable property test")
        
        # Test that immutable properties cannot be modified
        immutable_properties = ['question', 'username', 'workspace_name', 'functionality_level']
        
        for prop_name in immutable_properties:
            try:
                original_value = getattr(state, prop_name)
                
                # Attempt to modify (should fail)
                try:
                    setattr(state, prop_name, "modified_value")
                    
                    # If we get here, check if it actually changed
                    new_value = getattr(state, prop_name)
                    if new_value != original_value:
                        print(f"❌ {prop_name}: Immutable property was modified!")
                        return False
                    else:
                        print(f"✅ {prop_name}: Modification silently ignored (acceptable)")
                        
                except AttributeError as e:
                    # This is expected for truly immutable properties
                    if "immutable" in str(e) or "cannot" in str(e):
                        print(f"✅ {prop_name}: Properly protected as immutable")
                    else:
                        print(f"❌ {prop_name}: Unexpected error - {e}")
                        return False
                        
            except Exception as e:
                print(f"❌ {prop_name}: Immutable test failed - {e}")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Legacy immutable properties test failed: {e}")
        return False


def test_context_property_bridge():
    """Test that legacy properties correctly bridge to new context architecture."""
    print("\n🔍 Testing context property bridging...")
    
    try:
        from model.state_factory import StateFactory
        
        # Create state
        state = StateFactory.create_minimal("Context bridging test")
        
        # Test that legacy properties map to correct contexts
        context_mappings = [
            # Legacy property -> Context path
            ('question', 'request.question'),
            ('username', 'request.username'),
            ('functionality_level', 'request.functionality_level'),
            ('language', 'request.language'),
            ('scope', 'request.scope'),
        ]
        
        for legacy_prop, context_path in context_mappings:
            try:
                # Get via legacy property
                legacy_value = getattr(state, legacy_prop)
                
                # Get via context path
                context_obj = state
                for part in context_path.split('.'):
                    context_obj = getattr(context_obj, part)
                context_value = context_obj
                
                # They should be the same
                if legacy_value != context_value:
                    print(f"❌ {legacy_prop}: Legacy='{legacy_value}', Context='{context_value}'")
                    return False
                
                print(f"✅ {legacy_prop} ↔ {context_path}: {legacy_value}")
                
            except Exception as e:
                print(f"❌ {legacy_prop}: Context bridging failed - {e}")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Context property bridging test failed: {e}")
        return False



def test_legacy_code_patterns():
    """Test common legacy code usage patterns."""
    print("\n🔍 Testing legacy code patterns...")
    
    try:
        from model.state_factory import StateFactory
        
        # Create state
        state = StateFactory.create_minimal("Legacy patterns test")
        
        # Pattern 1: Direct property access and modification
        try:
            original_keywords = state.keywords or []
            state.keywords = original_keywords + ["pattern1"]
            assert "pattern1" in state.keywords, "Pattern 1: Keywords modification failed"
            print("✅ Pattern 1: Direct property access and modification")
        except Exception as e:
            print(f"❌ Pattern 1: Failed - {e}")
            return False
        
        # Pattern 2: Conditional property access
        try:
            if hasattr(state, 'generated_sql'):
                sql = state.generated_sql or "DEFAULT SQL"
                state.generated_sql = sql
            print("✅ Pattern 2: Conditional property access")
        except Exception as e:
            print(f"❌ Pattern 2: Failed - {e}")
            return False
        
        # Pattern 3: Property existence checking
        try:
            required_properties = ['question', 'username', 'functionality_level']
            for prop in required_properties:
                if not hasattr(state, prop):
                    print(f"❌ Pattern 3: Missing property {prop}")
                    return False
                if getattr(state, prop) is None:
                    print(f"❌ Pattern 3: Property {prop} is None")
                    return False
            print("✅ Pattern 3: Property existence checking")
        except Exception as e:
            print(f"❌ Pattern 3: Failed - {e}")
            return False
        
        # Pattern 4: State serialization compatibility
        try:
            # Should be able to access model_dump for serialization
            state_dict = state.model_dump()
            assert isinstance(state_dict, dict), "State serialization should return dict"
            assert 'request' in state_dict, "Serialized state should contain contexts"
            print("✅ Pattern 4: State serialization compatibility")
        except Exception as e:
            print(f"❌ Pattern 4: Failed - {e}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Legacy code patterns test failed: {e}")
        return False




def main():
    """Main backward compatibility test function."""
    print("🚀 Starting Phase 5 Backward Compatibility Tests...\n")
    
    test_results = []
    
    # Test 1: Legacy property access
    test_results.append(test_legacy_property_access())
    
    # Test 2: Legacy property modification
    test_results.append(test_legacy_property_modification())
    
    # Test 3: Immutable property protection
    test_results.append(test_legacy_immutable_properties())
    
    # Test 4: Context property bridging
    test_results.append(test_context_property_bridge())
    
    # Test 5: Legacy code patterns
    test_results.append(test_legacy_code_patterns())
    
    # Summary
    passed = sum(test_results)
    total = len(test_results)
    
    print(f"\n📊 Backward Compatibility Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 BACKWARD COMPATIBILITY TESTS PASSED!")
        print("✅ Legacy property access works correctly")
        print("✅ Legacy property modification preserved")
        print("✅ Immutable properties properly protected")
        print("✅ Context property bridging functional")
        print("✅ Common legacy code patterns supported")
        print("🚀 Legacy code fully compatible with new architecture")
        return True
    else:
        print("❌ Some backward compatibility tests FAILED!")
        print("Legacy compatibility has issues that need resolution")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)