"""
Test to identify which tool is causing the comparison error.
"""
import sys
import asyncio

sys.path.insert(0, '/Users/abdulfaras/Google_X_Kaggle_Capstone')

async def main():
    try:
        print("Importing agents...")
        from agents.nutrition.agent import nutrition_agent
        from google.adk.runners import InMemoryRunner
        
        print(f"Nutrition agent created: {nutrition_agent.name}")
        print(f"Tools: {[str(tool) for tool in nutrition_agent.tools]}")
        
        # Try to run a simple message
        print("\nCreating runner...")
        runner = InMemoryRunner(
            agent=nutrition_agent,
            app_name="agents"
        )
        
        print("Running message...")
        events = await runner.run_debug(
            user_messages=["I ate 2 eggs for breakfast"],
            user_id="test_user",
            session_id="test_session",
            verbose=True
        )
        
        print(f"Got {len(events)} events")
        for i, event in enumerate(events):
            print(f"  Event {i}: {type(event).__name__}")
            if hasattr(event, 'content'):
                print(f"    Content: {event.content}")
        
    except TypeError as e:
        if "'<=' not supported" in str(e) or "not supported between instances of" in str(e):
            print(f"\n❌ FOUND THE ERROR: {e}")
            import traceback
            traceback.print_exc()
        else:
            raise
    except Exception as e:
        print(f"\n❌ ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
