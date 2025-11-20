#!/usr/bin/env python3
"""
Test script for meal logging conversation flow.
"""

import asyncio
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from adk_integration import process_agent_message

async def test_meal_flow():
    """Test the complete meal logging flow."""
    print("=== Testing Meal Logging Flow ===")

    # Step 1: User mentions food
    print("\n1. User says 'pizza'")
    result1 = await process_agent_message("test_user", "pizza", "test_session_meal")
    print(f"Agent: {result1['text']}")

    # Step 2: User confirms that's all
    print("\n2. User says 'yes that's all'")
    result2 = await process_agent_message("test_user", "yes that's all", "test_session_meal")
    print(f"Agent: {result2['text']}")

if __name__ == "__main__":
    asyncio.run(test_meal_flow())