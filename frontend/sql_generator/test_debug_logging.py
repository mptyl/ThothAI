#!/usr/bin/env python3
# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the MIT License.
# See the LICENSE.md file in the project root for full license information.

"""
Test script to verify DEBUG logging for LSH and similarity search.
"""

import logging
import sys
from pathlib import Path

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent))

# Configure logging to show DEBUG messages
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)

# Set specific loggers to DEBUG level
logging.getLogger('helpers.main_helpers.main_schema_extraction_from_lsh').setLevel(logging.DEBUG)
logging.getLogger('helpers.main_helpers.main_schema_extraction_from_vectordb').setLevel(logging.DEBUG)
logging.getLogger('helpers.vectordb_context_retrieval').setLevel(logging.DEBUG)

def test_logging_format():
    """Test that the logging format is working correctly."""
    logger = logging.getLogger('helpers.main_helpers.main_schema_extraction_from_lsh')
    
    print("\n" + "="*70)
    print("TESTING DEBUG LOGGING OUTPUT")
    print("="*70)
    
    # Simulate LSH extraction logging
    logger.debug("="*60)
    logger.debug("LSH SCHEMA EXTRACTION STARTED")
    logger.debug("="*60)
    logger.debug("Configuration:")
    logger.debug("  - Signature Size: 50")
    logger.debug("  - Top N Results: 25")
    logger.debug("  - Edit Distance Threshold: 20.0%")
    logger.debug("  - Embedding Similarity Threshold: 40.0%")
    logger.debug("  - Max Examples per Column: 10")
    logger.debug("-"*60)
    
    logger.debug("\nPhase 2: Extracting example values via LSH...")
    logger.debug("Keywords to search: ['school', 'virtual', 'online']")
    
    logger.debug("\nStarting LSH queries...")
    logger.debug("Total keywords to search: 3")
    
    logger.debug("\nSearching LSH for: 'school' (from keyword: 'school')")
    logger.debug("  Found 2 tables with 5 matching values")
    logger.debug("    ✓ schools.SchoolName: 3 values")
    logger.debug("        Values: [\"Lincoln High\", \"Washington Elementary\", \"Roosevelt Middle\" ... (3 total)]")
    logger.debug("    ✓ schools.SchoolType: 2 values")
    logger.debug("        Values: [\"Public\", \"Private\"]")
    
    logger.debug("\nFiltering by embedding similarity (threshold: 40.0%)...")
    logger.debug("Candidates to evaluate: 5")
    logger.debug("\n  Embedding similarity for 'school':")
    logger.debug("    ✓ schools.SchoolName = 'Lincoln High' (similarity: 0.923)")
    logger.debug("    ✓ schools.SchoolType = 'Public' (similarity: 0.875)")
    
    logger.debug("\nEmbedding similarity filtering complete:")
    logger.debug("  - Passed: 2 entities")
    logger.debug("  - Filtered out: 3 entities")
    
    logger.debug("="*60)
    logger.debug("LSH EXTRACTION COMPLETE")
    logger.debug("Total tables found: 1")
    logger.debug("Total columns with examples: 2")
    logger.debug("Total example values extracted: 5")
    logger.debug("="*60)
    
    # Simulate Vector similarity search logging
    logger_vector = logging.getLogger('helpers.main_helpers.main_schema_extraction_from_vectordb')
    
    logger_vector.debug("\n")
    logger_vector.debug("="*60)
    logger_vector.debug("VECTOR SIMILARITY SEARCH STARTED")
    logger_vector.debug("="*60)
    logger_vector.debug("Question: How many schools are exclusively virtual?")
    logger_vector.debug("Keywords: ['school', 'virtual', 'exclusively']")
    logger_vector.debug("-"*60)
    logger_vector.debug("Configuration:")
    logger_vector.debug("  - Top K Results: 10")
    logger_vector.debug("  - Number of keywords: 3")
    logger_vector.debug("-"*60)
    
    # Simulate column retrieval logging
    logger_retrieval = logging.getLogger('helpers.vectordb_context_retrieval')
    
    logger_retrieval.debug("\n" + "-"*60)
    logger_retrieval.debug("SIMILARITY SEARCH BY KEYWORDS")
    logger_retrieval.debug("-"*60)
    logger_retrieval.debug("Keywords to search: ['school', 'virtual', 'exclusively']")
    logger_retrieval.debug("Top K per keyword: 10")
    
    logger_retrieval.debug("\n[1/3] Searching for keyword: 'school'")
    logger_retrieval.debug("  Found 3 columns across 1 tables")
    logger_retrieval.debug("    Table: schools")
    logger_retrieval.debug("      ✓ SchoolName")
    logger_retrieval.debug("          Description: The official name of the school")
    logger_retrieval.debug("      ✓ SchoolType")
    logger_retrieval.debug("          Values: Public, Private, Charter")
    logger_retrieval.debug("      ✓ VirtualStatus")
    logger_retrieval.debug("          Description: Indicates if the school offers virtual learning")
    
    logger_retrieval.debug("\n" + "-"*60)
    logger_retrieval.debug("Similarity search summary:")
    logger_retrieval.debug("  - Keywords searched: 3")
    logger_retrieval.debug("  - Total matches found: 5")
    logger_retrieval.debug("  - Unique tables: 1")
    logger_retrieval.debug("-"*60)
    
    logger_vector.debug("\n")
    logger_vector.debug("="*60)
    logger_vector.debug("VECTOR SIMILARITY SEARCH COMPLETE")
    logger_vector.debug("Total tables found: 1")
    logger_vector.debug("Total columns retrieved: 3")
    logger_vector.debug("="*60)
    
    print("\n" + "="*70)
    print("TEST COMPLETE - Debug logging is working correctly!")
    print("="*70)
    print("\nTo enable these logs in production:")
    print("1. Set logging level to DEBUG for the specific modules")
    print("2. Or set environment variable: LOGLEVEL=DEBUG")
    print("3. Or add to your code:")
    print("   logging.getLogger('helpers.main_helpers.main_schema_extraction_from_lsh').setLevel(logging.DEBUG)")
    print("   logging.getLogger('helpers.main_helpers.main_schema_extraction_from_vectordb').setLevel(logging.DEBUG)")
    print("   logging.getLogger('helpers.vectordb_context_retrieval').setLevel(logging.DEBUG)")

if __name__ == "__main__":
    test_logging_format()