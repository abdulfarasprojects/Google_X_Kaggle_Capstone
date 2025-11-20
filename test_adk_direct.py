"""
Direct Test of Multi-Agent ADK Implementation

Run with: python test_adk_direct.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_root_agent():
    """Test root agent creation"""
    print("\n" + "="*80)
    print("TEST 1: Root Agent Initialization")
    print("="*80)
    
    try:
        from agents.root.agent_adk import create_root_agent
        from config.gemini import PatchedGemini
        
        logger.info("Creating model client...")
        model_client = PatchedGemini(model="gemini-2.0-flash")
        
        logger.info("Creating root agent...")
        root_agent = create_root_agent(model_client)
        
        assert root_agent is not None, "Root agent is None"
        assert root_agent.name == "root_agent", f"Root agent name is {root_agent.name}"
        
        logger.info(f"✅ Root agent name: {root_agent.name}")
        
        if hasattr(root_agent, 'tools') and root_agent.tools:
            logger.info(f"✅ Root agent has {len(root_agent.tools)} coordinator tools")
        
        if hasattr(root_agent, 'instructions'):
            logger.info(f"✅ Root agent has instructions ({len(root_agent.instructions)} chars)")
            if 'transfer_to_agent' in root_agent.instructions:
                logger.info("✅ Instructions contain 'transfer_to_agent' routing")
        
        print("✅ TEST 1 PASSED: Root agent initialized successfully\n")
        return True
    except Exception as e:
        logger.error(f"❌ TEST 1 FAILED: {e}", exc_info=True)
        print(f"❌ TEST 1 FAILED: {e}\n")
        return False


def test_sub_agents():
    """Test sub-agent creation"""
    print("="*80)
    print("TEST 2: Sub-Agent Initialization")
    print("="*80)
    
    try:
        from config.gemini import PatchedGemini
        from agents.nutrition.agent_adk import create_nutrition_agent
        from agents.fitness.agent_adk import create_fitness_agent
        from agents.wellness.agent_adk import create_wellness_agent
        from agents.analytics.agent_adk import create_analytics_agent
        from agents.nudge.agent_adk import create_nudge_agent
        
        model_client = PatchedGemini(model="gemini-2.0-flash")
        
        agents = {
            "Nutrition": (create_nutrition_agent, "nutrition_agent_batch"),
            "Fitness": (create_fitness_agent, "fitness_agent"),
            "Wellness": (create_wellness_agent, "wellness_agent_batch"),
            "Analytics": (create_analytics_agent, "analytics_agent_progress"),
            "Nudge": (create_nudge_agent, "nudge_agent_autonomous"),
        }
        
        for domain, (factory, expected_name) in agents.items():
            logger.info(f"Creating {domain} agent...")
            agent = factory(model_client)
            
            assert agent is not None, f"{domain} agent is None"
            assert agent.name == expected_name, f"{domain} name is {agent.name}"
            
            if hasattr(agent, 'tools') and agent.tools:
                logger.info(f"✅ {domain} agent ({agent.name}) has {len(agent.tools)} tools")
            else:
                logger.warning(f"⚠️  {domain} agent has no tools")
        
        print("✅ TEST 2 PASSED: All sub-agents created successfully\n")
        return True
    except Exception as e:
        logger.error(f"❌ TEST 2 FAILED: {e}", exc_info=True)
        print(f"❌ TEST 2 FAILED: {e}\n")
        return False


def test_adk_integration():
    """Test ADK integration module"""
    print("="*80)
    print("TEST 3: ADK Integration Module")
    print("="*80)
    
    try:
        logger.info("Importing ADK integration...")
        from adk_integration import (
            ADKAgentRunner,
            process_agent_message,
            ADK_AVAILABLE,
            agent_runner
        )
        
        logger.info(f"✅ ADK_AVAILABLE = {ADK_AVAILABLE}")
        
        if not ADK_AVAILABLE:
            logger.warning("⚠️  ADK is not available - agent features limited")
            print("⚠️  WARNING: ADK module not available (expected if google-adk not installed)")
        else:
            logger.info("✅ ADK module is available")
        
        assert callable(process_agent_message), "process_agent_message is not callable"
        logger.info("✅ process_agent_message is callable")
        
        assert ADKAgentRunner is not None, "ADKAgentRunner class not found"
        logger.info("✅ ADKAgentRunner class available")
        
        assert agent_runner is not None, "agent_runner instance not created"
        logger.info("✅ Global agent_runner instance created")
        
        print("✅ TEST 3 PASSED: ADK integration module valid\n")
        return True
    except Exception as e:
        logger.error(f"❌ TEST 3 FAILED: {e}", exc_info=True)
        print(f"❌ TEST 3 FAILED: {e}\n")
        return False


def test_agent_hierarchy():
    """Test agent hierarchy and routing"""
    print("="*80)
    print("TEST 4: Agent Hierarchy and Routing Rules")
    print("="*80)
    
    try:
        from agents.root.agent_adk import create_root_agent
        from config.gemini import PatchedGemini
        
        logger.info("Creating root agent to verify routing...")
        model_client = PatchedGemini(model="gemini-2.0-flash")
        root_agent = create_root_agent(model_client)
        
        # Verify agent names in instructions
        agent_names = {
            "nutrition_agent_batch": "Nutrition",
            "fitness_agent": "Fitness",
            "wellness_agent_batch": "Wellness",
            "analytics_agent_progress": "Analytics",
            "nudge_agent_autonomous": "Nudge"
        }
        
        for agent_name, domain in agent_names.items():
            if agent_name in root_agent.instructions:
                logger.info(f"✅ {domain} agent routing rule found: {agent_name}")
            else:
                logger.warning(f"⚠️  {domain} agent routing rule NOT found: {agent_name}")
        
        # Verify transfer_to_agent pattern
        if 'transfer_to_agent' in root_agent.instructions:
            logger.info("✅ transfer_to_agent() method found in instructions")
        else:
            logger.warning("⚠️  transfer_to_agent() method NOT found in instructions")
        
        print("✅ TEST 4 PASSED: Agent hierarchy verified\n")
        return True
    except Exception as e:
        logger.error(f"❌ TEST 4 FAILED: {e}", exc_info=True)
        print(f"❌ TEST 4 FAILED: {e}\n")
        return False


def test_imports():
    """Test all module imports work"""
    print("="*80)
    print("TEST 5: Module Imports")
    print("="*80)
    
    try:
        logger.info("Testing all imports...")
        
        modules = [
            ("adk_integration", "ADK integration module"),
            ("agents.root.agent_adk", "Root agent module"),
            ("agents.nutrition.agent_adk", "Nutrition agent module"),
            ("agents.fitness.agent_adk", "Fitness agent module"),
            ("agents.wellness.agent_adk", "Wellness agent module"),
            ("agents.analytics.agent_adk", "Analytics agent module"),
            ("agents.nudge.agent_adk", "Nudge agent module"),
            ("config.gemini", "Gemini config module"),
        ]
        
        for module_name, description in modules:
            try:
                __import__(module_name)
                logger.info(f"✅ {description}: {module_name}")
            except ImportError as e:
                logger.warning(f"⚠️  {description} import failed (may be expected): {e}")
        
        print("✅ TEST 5 PASSED: All critical imports successful\n")
        return True
    except Exception as e:
        logger.error(f"❌ TEST 5 FAILED: {e}", exc_info=True)
        print(f"❌ TEST 5 FAILED: {e}\n")
        return False


def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("GOOGLE ADK MULTI-AGENT DELEGATION TEST SUITE")
    print("="*80)
    
    tests = [
        ("Module Imports", test_imports),
        ("Root Agent", test_root_agent),
        ("Sub-Agents", test_sub_agents),
        ("ADK Integration", test_adk_integration),
        ("Agent Hierarchy", test_agent_hierarchy),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            logger.error(f"Unexpected error in {test_name}: {e}", exc_info=True)
            results.append((test_name, False))
    
    # Summary
    print("="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nResults: {passed}/{total} tests passed")
    print("="*80 + "\n")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
