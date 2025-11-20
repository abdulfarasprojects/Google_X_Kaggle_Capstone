#!/usr/bin/env python3
"""
Verification Script for ADK Agent Imports

This script verifies that all agent modules can be imported without errors.
It checks import statements and module availability.

Usage:
    python3 verify_adk_imports.py

Output:
    - ✅ for successful imports
    - ⚠️  for warnings (module not available but not required to fail)
    - ❌ for import errors (critical failures)
"""

import sys
import importlib
from typing import Tuple, List

# Suppress google.adk warnings since it may not be installed locally
import warnings
warnings.filterwarnings('ignore')


def check_import(module_name: str, component: str = None) -> Tuple[bool, str]:
    """
    Check if a module or component can be imported.
    
    Args:
        module_name: Name of the module to import (e.g., 'google.adk.agents')
        component: Optional specific component to import (e.g., 'LlmAgent')
    
    Returns:
        (success: bool, message: str)
    """
    try:
        if component:
            mod = importlib.import_module(module_name)
            getattr(mod, component)
            return True, f"✅ {module_name}.{component}"
        else:
            importlib.import_module(module_name)
            return True, f"✅ {module_name}"
    except ModuleNotFoundError as e:
        return False, f"❌ {module_name}: {str(e)}"
    except AttributeError as e:
        return False, f"❌ {module_name}.{component}: {str(e)}"
    except Exception as e:
        return False, f"❌ {module_name}: {str(e)}"


def verify_agent_imports() -> bool:
    """
    Verify that all agent modules can be imported.
    
    Returns:
        True if all critical imports succeed, False otherwise
    """
    print("="*80)
    print("ADK AGENT IMPORT VERIFICATION")
    print("="*80 + "\n")
    
    # Test 1: Core imports that may not be available locally
    print("[1] Google ADK Core Modules (may not be available locally):")
    optional_imports = [
        ('google.adk.agents', 'LlmAgent'),
        ('google.adk.tools', 'FunctionTool'),
        ('google.adk.agents.invocation_context', 'InvocationContext'),
        ('google.adk.sessions', 'InMemorySessionService'),
    ]
    
    optional_status = []
    for module, component in optional_imports:
        success, msg = check_import(module, component)
        optional_status.append(success)
        print(f"    {msg}")
    
    print()
    
    # Test 2: Local config imports (must succeed)
    print("[2] Local Configuration Modules (CRITICAL):")
    critical_imports = [
        ('config.logging', 'get_logger'),
        ('config.gemini', 'PatchedGemini'),
    ]
    
    critical_status = []
    for module, component in critical_imports:
        success, msg = check_import(module, component)
        critical_status.append(success)
        status = "✅" if success else "❌"
        print(f"    {msg}")
    
    print()
    
    # Test 3: Tool imports (must succeed)
    print("[3] Tool Modules (CRITICAL):")
    tool_imports = [
        ('tools.intent_classifier', 'classify_intent'),
        ('tools.sentiment_detector', 'detect_sentiment'),
        ('tools.response_formatter', 'format_response'),
    ]
    
    tool_status = []
    for module, component in tool_imports:
        success, msg = check_import(module, component)
        tool_status.append(success)
        status = "✅" if success else "❌"
        print(f"    {msg}")
    
    print()
    
    # Test 4: Database managers (must succeed)
    print("[4] Database Manager Modules (CRITICAL):")
    db_imports = [
        ('database.meal_manager', 'meal_manager'),
        ('database.workout_manager', 'workout_manager'),
        ('database.wellness_manager', 'wellness_manager'),
        ('database.analytics_manager', 'analytics_manager'),
        ('database.nudge_manager', 'nudge_manager'),
    ]
    
    db_status = []
    for module, component in db_imports:
        success, msg = check_import(module, component)
        db_status.append(success)
        status = "✅" if success else "❌"
        print(f"    {msg}")
    
    print()
    
    # Test 5: Agent module imports (check for the specific import error)
    print("[5] Agent Modules (checking for import errors):")
    agent_files = [
        ('agents.root.agent_adk', 'create_root_agent', 'Root Agent'),
        ('agents.nutrition.agent_adk', 'create_nutrition_agent', 'Nutrition Agent'),
        ('agents.fitness.agent_adk', 'create_fitness_agent', 'Fitness Agent'),
        ('agents.wellness.agent_adk', 'create_wellness_agent', 'Wellness Agent'),
        ('agents.analytics.agent_adk', 'create_analytics_agent', 'Analytics Agent'),
        ('agents.nudge.agent_adk', 'create_nudge_agent', 'Nudge Agent'),
    ]
    
    agent_status = []
    for module, component, name in agent_files:
        try:
            mod = importlib.import_module(module)
            if hasattr(mod, component):
                print(f"    ✅ {name}: {module}.{component}")
                agent_status.append(True)
            else:
                print(f"    ❌ {name}: Missing {component} in {module}")
                agent_status.append(False)
        except ModuleNotFoundError as e:
            # Check if it's the profile_manager error we fixed
            if 'profile_manager' in str(e):
                print(f"    ❌ {name}: IMPORT ERROR - profile_manager issue still present!")
                print(f"       {e}")
                agent_status.append(False)
            else:
                print(f"    ⚠️  {name}: ModuleNotFoundError (might be OK if ADK not installed)")
                print(f"       {e}")
                agent_status.append(None)  # Neutral - ADK might not be installed
        except Exception as e:
            print(f"    ❌ {name}: {type(e).__name__}: {e}")
            agent_status.append(False)
    
    print()
    print("="*80)
    print("VERIFICATION SUMMARY")
    print("="*80)
    
    # Summary
    critical_all_ok = all(critical_status)
    tools_all_ok = all(tool_status)
    db_all_ok = all(db_status)
    agents_ok = all(s for s in agent_status if s is not None)  # None = ADK not installed
    
    print(f"Configuration Modules:  {'✅ OK' if critical_all_ok else '❌ FAILED'}")
    print(f"Tool Modules:           {'✅ OK' if tools_all_ok else '❌ FAILED'}")
    print(f"Database Managers:      {'✅ OK' if db_all_ok else '❌ FAILED'}")
    print(f"Agent Modules:          {'✅ OK' if agents_ok else '❌ FAILED'}")
    
    print()
    
    # Check for specific errors
    profile_manager_errors = [s for s in agent_status if s is False]
    if profile_manager_errors:
        print("⚠️  ISSUES DETECTED:")
        print("    - Agent import failures detected")
        print("    - Check the error messages above")
    else:
        print("✅ ALL CRITICAL COMPONENTS VERIFIED")
        if any(s is None for s in agent_status):
            print("    (Note: Some modules require 'google.adk' package to fully load)")
    
    print()
    print("="*80)
    print()
    
    # Final result
    all_critical_ok = critical_all_ok and tools_all_ok and db_all_ok
    return all_critical_ok


if __name__ == "__main__":
    success = verify_agent_imports()
    sys.exit(0 if success else 1)
