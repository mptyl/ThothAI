#!/usr/bin/env python3
# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

"""Standalone test for quoting styles in semantic alias generation."""

import re
from typing import Dict, List, Tuple

def _clean_field_name_for_alias(field_name: str) -> str:
    """Clean a field name to create a valid alias."""
    # Rimuovi tutti i tipi di quote supportati dai vari database
    # Double quotes (PostgreSQL, Oracle, SQLite)
    cleaned = field_name.strip().strip('"')
    # Single quotes (string literals - not typically for field names but handle anyway)
    cleaned = cleaned.strip("'")
    # Backticks (MySQL, MariaDB, SQLite)
    cleaned = cleaned.strip('`')
    # Square brackets (SQL Server)
    if cleaned.startswith('[') and cleaned.endswith(']'):
        cleaned = cleaned[1:-1]
    
    # Sostituisci parentesi e loro contenuto con underscore
    cleaned = re.sub(r'\([^)]*\)', lambda m: m.group().replace('(', '_').replace(')', '_').replace(' ', '_'), cleaned)
    
    # Sostituisci spazi, trattini e altri caratteri con underscore
    cleaned = re.sub(r'[\s\-\(\)\[\]\{\}\/\\,;:!@#$%^&*+=|<>?`~]', '_', cleaned)
    
    # Rimuovi underscore multipli
    cleaned = re.sub(r'_+', '_', cleaned)
    
    # Rimuovi underscore iniziali e finali
    cleaned = cleaned.strip('_')
    
    # Converti in lowercase
    cleaned = cleaned.lower()
    
    # Tronca se troppo lungo (max 30 caratteri)
    if len(cleaned) > 30:
        cleaned = cleaned[:30].rstrip('_')
    
    return cleaned if cleaned else 'field'

def _generate_semantic_alias(expression: str, alias_counter: Dict[str, int]) -> str:
    """Genera un alias semanticamente significativo per un'espressione."""
    # Rimuovi spazi extra
    expr = expression.strip()
    
    # Helper function to check for parentheses outside of quotes
    def has_unquoted_parens(s: str) -> bool:
        """Check if string has parentheses that aren't inside quoted field names.
        Handles all database quoting styles:
        - Double quotes: "field" (PostgreSQL, Oracle, SQLite, ANSI mode)
        - Single quotes: 'field' (for string literals, not field names)
        - Backticks: `field` (MySQL, MariaDB, SQLite)
        - Square brackets: [field] (SQL Server)
        """
        quote_char = None
        in_brackets = False
        
        for i, char in enumerate(s):
            # Handle square brackets (SQL Server style)
            if char == '[' and quote_char is None:
                in_brackets = True
            elif char == ']' and in_brackets:
                in_brackets = False
            # Handle quotes and backticks
            elif quote_char is None and char in ['"', "'", '`']:
                quote_char = char
            elif quote_char and char == quote_char:
                # Check if it's an escaped quote (doubled)
                if i + 1 < len(s) and s[i + 1] == quote_char:
                    continue  # Skip escaped quote
                quote_char = None
            elif quote_char or in_brackets:
                # Inside quotes or brackets, skip
                continue
            elif char in ['(', ')']:
                # Found parenthesis outside of quotes and brackets
                return True
        return False
    
    base_alias = None
    
    # Caso divisione
    if '/' in expr and not has_unquoted_parens(expr):
        parts = expr.split('/')
        if len(parts) == 2:
            left = _clean_field_name_for_alias(parts[0])
            right = _clean_field_name_for_alias(parts[1])
            
            # Casi speciali per ratio/rate
            # Check the original parts before cleaning for semantic meaning
            left_orig = parts[0].strip()
            right_orig = parts[1].strip()
            
            if 'count' in left.lower() and any(word in right.lower() for word in ['enrollment', 'total', 'population']):
                base_alias = f"{left}_rate"
            elif ('meal' in left_orig.lower() or 'meal' in left.lower()) and ('enrollment' in right_orig.lower() or 'enrollment' in right.lower()):
                base_alias = "free_meal_rate"
            else:
                base_alias = f"{left}_per_{right}"
    
    # Caso moltiplicazione
    elif '*' in expr and not has_unquoted_parens(expr):
        parts = expr.split('*')
        if len(parts) == 2:
            left = _clean_field_name_for_alias(parts[0])
            right = _clean_field_name_for_alias(parts[1])
            
            # Casi speciali
            if any(word in left.lower() + right.lower() for word in ['price', 'quantity', 'cost']):
                base_alias = "total_amount"
            else:
                base_alias = f"{left}_times_{right}"
    
    # Caso addizione
    elif '+' in expr and not has_unquoted_parens(expr):
        parts = expr.split('+')
        if len(parts) == 2:
            left = _clean_field_name_for_alias(parts[0])
            right = _clean_field_name_for_alias(parts[1])
            base_alias = f"{left}_plus_{right}"
    
    # Caso sottrazione
    elif '-' in expr and not has_unquoted_parens(expr):
        parts = expr.split('-')
        if len(parts) == 2:
            left = _clean_field_name_for_alias(parts[0])
            right = _clean_field_name_for_alias(parts[1])
            base_alias = f"{left}_minus_{right}"
    
    # Default fallback
    if not base_alias:
        # Fallback generico basato sull'operatore trovato
        if '/' in expr:
            base_alias = 'calculated_ratio'
        elif '*' in expr:
            base_alias = 'calculated_product'
        elif '+' in expr:
            base_alias = 'calculated_sum'
        elif '-' in expr:
            base_alias = 'calculated_difference'
        else:
            base_alias = 'calculated_field'
    
    # Gestisci duplicati aggiungendo un suffisso numerico se necessario
    final_alias = base_alias
    if base_alias in alias_counter:
        alias_counter[base_alias] += 1
        final_alias = f"{base_alias}_{alias_counter[base_alias]}"
    else:
        alias_counter[base_alias] = 0
    
    return final_alias

def test_quoting_styles():
    """Test different database quoting styles."""
    test_cases = [
        # PostgreSQL/Oracle/SQLite style (double quotes)
        {
            'expr': '"Free Meal Count (Ages 5-17)" / "Enrollment (Ages 5-17)"',
            'db': 'PostgreSQL',
            'expected': 'free_meal_rate'
        },
        # MySQL/MariaDB/SQLite style (backticks)
        {
            'expr': '`Free Meal Count (Ages 5-17)` / `Enrollment (Ages 5-17)`',
            'db': 'MySQL/MariaDB',
            'expected': 'free_meal_rate'
        },
        # SQL Server style (square brackets)
        {
            'expr': '[Free Meal Count (Ages 5-17)] / [Enrollment (Ages 5-17)]',
            'db': 'SQL Server',
            'expected': 'free_meal_rate'
        },
        # Mixed operations with different quoting
        {
            'expr': '"Price" * "Quantity"',
            'db': 'PostgreSQL (multiplication)',
            'expected': 'total_amount'
        },
        {
            'expr': '`Total` + `Tax`',
            'db': 'MySQL (addition)',
            'expected': 'total_plus_tax'
        },
        {
            'expr': '[Discount] - [Amount]',
            'db': 'SQL Server (subtraction)',
            'expected': 'discount_minus_amount'
        },
        # Complex field names with parentheses
        {
            'expr': '"Students (K-12)" + "Teachers (Full-Time)"',
            'db': 'PostgreSQL (complex names)',
            'expected': 'students_k_12_plus_teachers_full_time'
        },
        # Test that parentheses inside quotes don't break division detection
        {
            'expr': '`Count (Total)` / `Population (2020)`',
            'db': 'MySQL (parens in names)',
            'expected': 'count_total_rate'
        }
    ]
    
    print("Testing semantic alias generation with different database quoting styles:")
    print("=" * 80)
    
    alias_counter = {}
    
    for test in test_cases:
        print(f"\nDatabase: {test['db']}")
        print(f"Expression: {test['expr']}")
        
        result = _generate_semantic_alias(test['expr'], alias_counter)
        print(f"Generated alias: {result}")
        print(f"Expected alias: {test['expected']}")
        
        if result == test['expected']:
            print("✓ PASS")
        else:
            print("✗ FAIL")
        
        print("-" * 60)

if __name__ == "__main__":
    test_quoting_styles()