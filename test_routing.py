#!/usr/bin/env python3
"""
Quick test script to verify meal routing works end-to-end.
"""

import asyncio
import logging
from adk_integration import process_agent_message, initialize_agent_runner, shutdown_agent_runner

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    print("\n" + "="*60)
    print("🧪 Testing ADK Agent Routing System")
    print("="*60)

    # Initialize the runner
    print("\n1️⃣ Initializing agent runner...")
    await initialize_agent_runner()
    print("✅ Agent runner initialized")

    # Test 1: Nutrition message
    print("\n2️⃣ Testing NUTRITION message routing...")
    result = await process_agent_message(
        user_id="test_user_001",
        message="I ate a burger for lunch"
    )
    print(f"📤 Response: {result.get('text', 'NO RESPONSE')[:200]}")

    # Test 2: Fitness message
    print("\n3️⃣ Testing FITNESS message routing...")
    result = await process_agent_message(
        user_id="test_user_001",
        message="I did 10 pushups and 20 squats today"
    )
    print(f"📤 Response: {result.get('text', 'NO RESPONSE')[:200]}")

    # Test 3: Wellness message
    print("\n4️⃣ Testing WELLNESS message routing...")
    result = await process_agent_message(
        user_id="test_user_001",
        message="I slept 8 hours last night"
    )
    print(f"📤 Response: {result.get('text', 'NO RESPONSE')[:200]}")

    # Test 4: General message
    print("\n5️⃣ Testing GENERAL (root) message routing...")
    result = await process_agent_message(
        user_id="test_user_001",
        message="How are you doing today?"
    )
    print(f"📤 Response: {result.get('text', 'NO RESPONSE')[:200]}")

    # Cleanup
    print("\n6️⃣ Shutting down...")
    await shutdown_agent_runner()
    print("✅ Shutdown complete")

    print("\n" + "="*60)
    print("✅ All tests completed!")
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
