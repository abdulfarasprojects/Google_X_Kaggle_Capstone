#!/usr/bin/env python3
"""
Simple test script for the ADK agent.
"""

import asyncio
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from adk_integration import process_agent_message

async def test_agent(message: str):
    """Test the agent with a message."""
    print(f"Testing agent with message: {message}")
    result = await process_agent_message("test_user", message, "test_session")
    print(f"Response: {result['text']}")
    return result

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_agent.py <message>")
        sys.exit(1)

    message = " ".join(sys.argv[1:])
    asyncio.run(test_agent(message))