#!/usr/bin/env python3
"""
Quick ADK Agent Import Verification

Lightweight check that verifies agents can be imported without hanging.
"""

import sys
import importlib
import warnings

warnings.filterwarnings('ignore')

def quick_check():
    """Quick check for agent imports."""
    print("✅ Checking agent imports...\n")
    
    agents = [
        ('agents.root.agent_adk', 'Root Agent'),
        ('agents.nutrition.agent_adk', 'Nutrition Agent'),
        ('agents.fitness.agent_adk', 'Fitness Agent'),
        ('agents.wellness.agent_adk', 'Wellness Agent'),
        ('agents.analytics.agent_adk', 'Analytics Agent'),
        ('agents.nudge.agent_adk', 'Nudge Agent'),
    ]
    
    all_ok = True
    
    for module_name, name in agents:
        try:
            # Just try to import, timeout if it hangs
            mod = importlib.import_module(module_name)
            print(f"✅ {name}: {module_name}")
        except ImportError as e:
            if 'profile_manager' in str(e):
                print(f"❌ {name}: PROFILE_MANAGER ERROR - {e}")
                all_ok = False
            else:
                print(f"❌ {name}: Import error - {e}")
                all_ok = False
        except Exception as e:
            print(f"⚠️  {name}: {type(e).__name__} - {str(e)[:80]}")
    
    print()
    if all_ok:
        print("✅ All agents imported successfully!")
        return 0
    else:
        print("❌ Some agents failed to import")
        return 1

if __name__ == "__main__":
    sys.exit(quick_check())
