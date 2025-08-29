#!/usr/bin/env python3
"""Debug script to test the exact import path Django uses."""

import sys
import os

# Set up the same environment as Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Thoth.settings')

# Add the project root to Python path (same as Django)
sys.path.insert(0, '/Users/mp/DjangoExperimental/Thoth')

print("Python path:")
for i, path in enumerate(sys.path[:5]):
    print(f"  {i}: {path}")

print("\n" + "="*50)

try:
    # Import the same way the VectorStoreFactory does
    from thoth_qdrant import VectorStoreFactory
    
    print("✓ VectorStoreFactory imported successfully")
    
    # Create a Qdrant adapter (same as Django does)
    vector_store = VectorStoreFactory.create(
        backend="qdrant",
        collection="test_collection",
        host="localhost",
        port=6333
    )
    
    print(f"✓ Vector store created: {type(vector_store)}")
    print(f"  Class: {vector_store.__class__}")
    print(f"  Module: {vector_store.__class__.__module__}")
    
    # Check the method signature
    import inspect
    sig = inspect.signature(vector_store.bulk_add_documents)
    params = list(sig.parameters.keys())
    
    print(f"\nMethod signature: {sig}")
    print(f"Parameters: {params}")
    
    if 'policy' in params:
        print("[SUCCESS] policy parameter is available!")
    else:
        print("[FAILED] policy parameter is missing!")
        
    # Check the source file
    # Check the source file
    import thoth_qdrant.adapter.qdrant_native as module
    print(f"\nSource file: {module.__file__}")
    
    # Check if there are multiple versions
    import thoth_qdrant
    print(f"Package location: {thoth_qdrant.__file__}")
    
except Exception as e:
    print(f"[ERROR] {e}")
    import traceback
    traceback.print_exc()
