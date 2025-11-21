#!/usr/bin/env python3
"""
Test script to reproduce and trace the comparison error.
"""
import traceback
import sys

try:
    from google.genai import types as genai_types
    
    print("Testing Schema validation with string constraints...")
    
    # Try to create a schema with string constraints (this might trigger the error)
    schema = genai_types.Schema(
        type=genai_types.Type.NUMBER,
        minimum='7',  # This is a string, not a number
        maximum='90'  # This is a string, not a number
    )
    
    print(f"Schema created: minimum={schema.minimum}, maximum={schema.maximum}")
    
    # Try to validate a value - this is where the error likely occurs
    test_value = 10
    print(f"Testing if {test_value} < {schema.minimum}...")
    
    if test_value < schema.minimum:  # type: ignore
        print('Value is less than minimum')
    else:
        print('Value is greater than or equal to minimum')
    
except TypeError as e:
    print(f'TypeError: {e}')
    traceback.print_exc()
except Exception as e:
    print(f'Error type: {type(e).__name__}')
    print(f'Error message: {e}')
    traceback.print_exc()
