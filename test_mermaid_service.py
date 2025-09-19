#!/usr/bin/env python3
"""
Test script to verify the Mermaid service integration with ThothAI ERD functionality.
"""

import os
import sys
import requests
import time

# Add the backend directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

# Import the mermaid_utils module
from thoth_ai_backend.mermaid_utils import (
    check_mermaid_service_status,
    generate_mermaid_image,
    get_erd_display_image,
    generate_erd_pdf,
)

def test_mermaid_service_status():
    """Test that the Mermaid service is running and accessible."""
    print("Testing Mermaid service status...")
    
    is_running = check_mermaid_service_status()
    
    if is_running:
        print("✓ Mermaid service is running and accessible")
        return True
    else:
        print("✗ Mermaid service is not running or not accessible")
        return False

def test_svg_generation():
    """Test SVG generation with a simple Mermaid diagram."""
    print("\nTesting SVG generation...")
    
    # Simple test diagram
    test_diagram = """
    graph TD
        A[Start] --> B[Process]
        B --> C[End]
    """
    
    success, output_path, error_msg = generate_mermaid_image(
        test_diagram, 
        output_format="svg"
    )
    
    if success and output_path:
        print(f"✓ SVG generated successfully: {output_path}")
        
        # Check if file exists and has content
        if os.path.exists(output_path):
            with open(output_path, 'r') as f:
                content = f.read()
                if '<svg' in content and '</svg>' in content:
                    print("✓ SVG file contains valid SVG content")
                    # Clean up
                    os.unlink(output_path)
                    return True
                else:
                    print("✗ SVG file does not contain valid SVG content")
                    return False
        else:
            print("✗ SVG file was not created")
            return False
    else:
        print(f"✗ Failed to generate SVG: {error_msg}")
        return False

def test_png_generation():
    """Test PNG generation with a simple Mermaid diagram."""
    print("\nTesting PNG generation...")
    
    # Simple test diagram
    test_diagram = """
    graph TD
        A[Start] --> B[Process]
        B --> C[End]
    """
    
    success, output_path, error_msg = generate_mermaid_image(
        test_diagram, 
        output_format="png"
    )
    
    if success and output_path:
        print(f"✓ PNG generated successfully: {output_path}")
        
        # Check if file exists and has content
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            if file_size > 0:
                print(f"✓ PNG file has content ({file_size} bytes)")
                # Clean up
                os.unlink(output_path)
                return True
            else:
                print("✗ PNG file is empty")
                return False
        else:
            print("✗ PNG file was not created")
            return False
    else:
        print(f"✗ Failed to generate PNG: {error_msg}")
        return False

def test_erd_display_image():
    """Test ERD display image generation."""
    print("\nTesting ERD display image generation...")
    
    # Simple ERD diagram
    erd_diagram = """
    erDiagram
        CUSTOMER ||--o{ ORDER : places
        ORDER ||--|{ ORDER-ITEM : contains
        ORDER-ITEM }|--|| PRODUCT : includes
    """
    
    success, output_path, error_msg = get_erd_display_image(erd_diagram)
    
    if success and output_path:
        print(f"✓ ERD display image generated successfully: {output_path}")
        
        # Check if file exists and has content
        if os.path.exists(output_path):
            with open(output_path, 'r') as f:
                content = f.read()
                if '<svg' in content and '</svg>' in content:
                    print("✓ ERD display image contains valid SVG content")
                    # Clean up
                    os.unlink(output_path)
                    return True
                else:
                    print("✗ ERD display image does not contain valid SVG content")
                    return False
        else:
            print("✗ ERD display image file was not created")
            return False
    else:
        print(f"✗ Failed to generate ERD display image: {error_msg}")
        return False

def test_erd_pdf_generation():
    """Test ERD PDF generation."""
    print("\nTesting ERD PDF generation...")
    
    # Simple ERD diagram
    erd_diagram = """
    erDiagram
        CUSTOMER ||--o{ ORDER : places
        ORDER ||--|{ ORDER-ITEM : contains
        ORDER-ITEM }|--|| PRODUCT : includes
    """
    
    success, pdf_response, error_msg = generate_erd_pdf(erd_diagram, "test_db")
    
    if success and pdf_response:
        print("✓ ERD PDF generated successfully")
        
        # Check if response has content
        content = pdf_response.content
        if len(content) > 0:
            print(f"✓ PDF has content ({len(content)} bytes)")
            return True
        else:
            print("✗ PDF is empty")
            return False
    else:
        print(f"✗ Failed to generate ERD PDF: {error_msg}")
        return False

def main():
    """Run all tests."""
    print("ThothAI Mermaid Service Integration Test")
    print("=========================================")
    
    tests = [
        test_mermaid_service_status,
        test_svg_generation,
        test_png_generation,
        test_erd_display_image,
        test_erd_pdf_generation,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"✗ Test failed with exception: {e}")
    
    print(f"\nTest Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✓ All tests passed! The Mermaid service integration is working correctly.")
        return 0
    else:
        print("✗ Some tests failed. Please check the Mermaid service configuration.")
        return 1

if __name__ == "__main__":
    sys.exit(main())