#!/usr/bin/env python3
"""
Debug script to test ADK integration step by step.
"""

import sys
import asyncio
import logging

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

print("=" * 60)
print("🧪 ADK Integration Debug Test")
print("=" * 60)

# Test 1: Import adk_integration
print("\n1️⃣ Testing adk_integration import...")
try:
    import adk_integration
    print("✅ adk_integration imported successfully")
except Exception as e:
    print(f"❌ Failed to import adk_integration: {e}")
    sys.exit(1)

# Test 2: Check if _lazy_load_adk works
print("\n2️⃣ Testing lazy load...")
try:
    result = adk_integration._lazy_load_adk()
    if result:
        print("✅ Lazy load successful")
    else:
        print("❌ Lazy load returned False")
        sys.exit(1)
except Exception as e:
    print(f"❌ Lazy load failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 3: Try to process a message
print("\n3️⃣ Testing process_agent_message...")
async def test_message():
    try:
        response = await adk_integration.process_agent_message(
            user_id="test_123",
            message="I ate a burger"
        )
        print(f"✅ Message processed: {response}")
    except Exception as e:
        print(f"❌ Failed to process message: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

try:
    asyncio.run(test_message())
except Exception as e:
    print(f"❌ Async test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("✅ All tests passed!")
print("=" * 60)
