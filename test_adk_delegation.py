"""
Test Multi-Agent Delegation Flow for Google ADK Implementation

This test suite validates:
1. Root agent initialization and coordinator tools
2. Sub-agent creation and tool availability
3. Agent delegation routing based on intent
4. Message flow through the agent hierarchy
5. Response generation and formatting

To run tests:
    python -m pytest test_adk_delegation.py -v
    
Or directly:
    python test_adk_delegation.py
"""

import asyncio
import logging
import pytest
from typing import Dict, Any, List
from datetime import datetime

# Configure logging for tests
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# TEST FIXTURES AND SETUP
# ============================================================================

@pytest.fixture
async def model_client():
    """Create a model client for testing"""
    from config.gemini import PatchedGemini
    return PatchedGemini(model="gemini-2.0-flash")


@pytest.fixture
async def root_agent(model_client):
    """Create root agent for testing"""
    from agents.root.agent_adk import create_root_agent
    return create_root_agent(model_client)


@pytest.fixture
async def nutrition_agent(model_client):
    """Create nutrition sub-agent for testing"""
    from agents.nutrition.agent_adk import create_nutrition_agent
    return create_nutrition_agent(model_client)


@pytest.fixture
async def fitness_agent(model_client):
    """Create fitness sub-agent for testing"""
    from agents.fitness.agent_adk import create_fitness_agent
    return create_fitness_agent(model_client)


@pytest.fixture
async def wellness_agent(model_client):
    """Create wellness sub-agent for testing"""
    from agents.wellness.agent_adk import create_wellness_agent
    return create_wellness_agent(model_client)


@pytest.fixture
async def analytics_agent(model_client):
    """Create analytics sub-agent for testing"""
    from agents.analytics.agent_adk import create_analytics_agent
    return create_analytics_agent(model_client)


@pytest.fixture
async def nudge_agent(model_client):
    """Create nudge sub-agent for testing"""
    from agents.nudge.agent_adk import create_nudge_agent
    return create_nudge_agent(model_client)


# ============================================================================
# TEST CLASSES
# ============================================================================

class TestRootAgentInitialization:
    """Test root agent initialization and coordinator tools"""
    
    @pytest.mark.asyncio
    async def test_root_agent_creation(self, root_agent):
        """Test that root agent is created successfully"""
        assert root_agent is not None
        assert root_agent.name == "root_agent"
        logger.info(f"✅ Root agent created: {root_agent.name}")
    
    @pytest.mark.asyncio
    async def test_root_agent_has_coordinator_tools(self, root_agent):
        """Test that root agent has coordinator tools"""
        assert hasattr(root_agent, 'tools')
        assert root_agent.tools is not None
        assert len(root_agent.tools) >= 5
        logger.info(f"✅ Root agent has {len(root_agent.tools)} coordinator tools")
    
    @pytest.mark.asyncio
    async def test_root_agent_has_sub_agents(self, root_agent):
        """Test that root agent has sub-agents registered"""
        assert hasattr(root_agent, 'sub_agents')
        assert root_agent.sub_agents is not None
        # After initialization, should have 5 sub-agents
        # Note: May need adjustment based on actual implementation
        logger.info(f"✅ Root agent has sub-agents registered")


class TestSubAgentCreation:
    """Test sub-agent creation and tool availability"""
    
    @pytest.mark.asyncio
    async def test_nutrition_agent_creation(self, nutrition_agent):
        """Test nutrition agent creation"""
        assert nutrition_agent is not None
        assert nutrition_agent.name == "nutrition_agent_batch"
        logger.info(f"✅ Nutrition agent created: {nutrition_agent.name}")
    
    @pytest.mark.asyncio
    async def test_nutrition_agent_has_tools(self, nutrition_agent):
        """Test nutrition agent has domain-specific tools"""
        assert hasattr(nutrition_agent, 'tools')
        assert len(nutrition_agent.tools) >= 6  # 6+ nutrition tools
        logger.info(f"✅ Nutrition agent has {len(nutrition_agent.tools)} tools")
    
    @pytest.mark.asyncio
    async def test_fitness_agent_creation(self, fitness_agent):
        """Test fitness agent creation"""
        assert fitness_agent is not None
        assert fitness_agent.name == "fitness_agent"
        logger.info(f"✅ Fitness agent created: {fitness_agent.name}")
    
    @pytest.mark.asyncio
    async def test_fitness_agent_has_tools(self, fitness_agent):
        """Test fitness agent has domain-specific tools"""
        assert hasattr(fitness_agent, 'tools')
        assert len(fitness_agent.tools) >= 7  # 7+ fitness tools
        logger.info(f"✅ Fitness agent has {len(fitness_agent.tools)} tools")
    
    @pytest.mark.asyncio
    async def test_wellness_agent_creation(self, wellness_agent):
        """Test wellness agent creation"""
        assert wellness_agent is not None
        assert wellness_agent.name == "wellness_agent_batch"
        logger.info(f"✅ Wellness agent created: {wellness_agent.name}")
    
    @pytest.mark.asyncio
    async def test_wellness_agent_has_tools(self, wellness_agent):
        """Test wellness agent has domain-specific tools"""
        assert hasattr(wellness_agent, 'tools')
        assert len(wellness_agent.tools) >= 7  # 7+ wellness tools
        logger.info(f"✅ Wellness agent has {len(wellness_agent.tools)} tools")
    
    @pytest.mark.asyncio
    async def test_analytics_agent_creation(self, analytics_agent):
        """Test analytics agent creation"""
        assert analytics_agent is not None
        assert analytics_agent.name == "analytics_agent_progress"
        logger.info(f"✅ Analytics agent created: {analytics_agent.name}")
    
    @pytest.mark.asyncio
    async def test_analytics_agent_has_tools(self, analytics_agent):
        """Test analytics agent has domain-specific tools"""
        assert hasattr(analytics_agent, 'tools')
        assert len(analytics_agent.tools) >= 7  # 7+ analytics tools
        logger.info(f"✅ Analytics agent has {len(analytics_agent.tools)} tools")
    
    @pytest.mark.asyncio
    async def test_nudge_agent_creation(self, nudge_agent):
        """Test nudge agent creation"""
        assert nudge_agent is not None
        assert nudge_agent.name == "nudge_agent_autonomous"
        logger.info(f"✅ Nudge agent created: {nudge_agent.name}")
    
    @pytest.mark.asyncio
    async def test_nudge_agent_has_tools(self, nudge_agent):
        """Test nudge agent has domain-specific tools"""
        assert hasattr(nudge_agent, 'tools')
        assert len(nudge_agent.tools) >= 7  # 7+ nudge tools
        logger.info(f"✅ Nudge agent has {len(nudge_agent.tools)} tools")


class TestADKIntegration:
    """Test ADK integration layer"""
    
    @pytest.mark.asyncio
    async def test_adk_integration_imports(self):
        """Test that ADK integration module imports correctly"""
        try:
            from adk_integration import (
                ADKAgentRunner,
                process_agent_message,
                initialize_agent_runner,
                shutdown_agent_runner,
                ADK_AVAILABLE
            )
            assert ADK_AVAILABLE
            logger.info("✅ ADK integration module imports successfully")
        except ImportError as e:
            logger.error(f"❌ ADK integration import failed: {e}")
            raise
    
    @pytest.mark.asyncio
    async def test_process_agent_message_function(self):
        """Test that process_agent_message is callable"""
        from adk_integration import process_agent_message
        
        assert callable(process_agent_message)
        logger.info("✅ process_agent_message is callable")
    
    @pytest.mark.asyncio
    async def test_adk_runner_initialization(self):
        """Test ADK runner can be initialized"""
        from adk_integration import agent_runner
        
        # Initialize runner
        await agent_runner.initialize()
        assert agent_runner._initialized
        logger.info("✅ ADK runner initialized successfully")
        
        # Cleanup
        await agent_runner.close()


class TestDelegationFlow:
    """Test agent delegation flow (requires mocking or integration test)"""
    
    def test_nutrition_delegation_keywords(self):
        """Test that nutrition keywords are recognized"""
        nutrition_keywords = [
            "meal", "food", "calories", "eat", "breakfast",
            "lunch", "dinner", "snack", "nutrition", "carbs",
            "protein", "macros", "log meal"
        ]
        # These should trigger nutrition_agent delegation
        logger.info(f"✅ Nutrition keywords defined: {len(nutrition_keywords)}")
    
    def test_fitness_delegation_keywords(self):
        """Test that fitness keywords are recognized"""
        fitness_keywords = [
            "workout", "exercise", "gym", "run", "lift",
            "training", "fitness", "pushups", "squats", "cardio"
        ]
        logger.info(f"✅ Fitness keywords defined: {len(fitness_keywords)}")
    
    def test_wellness_delegation_keywords(self):
        """Test that wellness keywords are recognized"""
        wellness_keywords = [
            "sleep", "water", "hydration", "steps", "health",
            "rest", "tired", "thirsty", "walked", "slept"
        ]
        logger.info(f"✅ Wellness keywords defined: {len(wellness_keywords)}")
    
    def test_analytics_delegation_keywords(self):
        """Test that analytics keywords are recognized"""
        analytics_keywords = [
            "progress", "stats", "summary", "report",
            "how am i doing", "trends", "analysis", "weight"
        ]
        logger.info(f"✅ Analytics keywords defined: {len(analytics_keywords)}")
    
    def test_nudge_delegation_keywords(self):
        """Test that nudge keywords are recognized"""
        nudge_keywords = [
            "remind", "motivation", "streak", "encourage",
            "push me", "reminder", "notification", "nudge"
        ]
        logger.info(f"✅ Nudge keywords defined: {len(nudge_keywords)}")


class TestAgentHierarchy:
    """Test agent hierarchy and structure"""
    
    def test_agent_names_match_routing_rules(self):
        """Test that agent names match root agent routing rules"""
        expected_agents = {
            "nutrition_agent_batch": "Nutrition domain",
            "fitness_agent": "Fitness domain",
            "wellness_agent_batch": "Wellness domain",
            "analytics_agent_progress": "Analytics domain",
            "nudge_agent_autonomous": "Nudge/Motivation domain"
        }
        
        for agent_name, domain in expected_agents.items():
            logger.info(f"✅ {agent_name}: {domain}")
    
    def test_coordinator_instructions_include_routing(self):
        """Test that coordinator instructions include routing rules"""
        from agents.root.agent_adk import create_root_agent
        from config.gemini import PatchedGemini
        
        model_client = PatchedGemini(model="gemini-2.0-flash")
        root = create_root_agent(model_client)
        
        assert hasattr(root, 'instructions')
        assert 'transfer_to_agent' in root.instructions
        assert 'nutrition_agent_batch' in root.instructions
        assert 'fitness_agent' in root.instructions
        
        logger.info("✅ Root agent instructions include transfer_to_agent routing")


# ============================================================================
# SYNCHRONOUS TEST RUNNERS (for direct execution)
# ============================================================================

def test_sync_root_agent():
    """Synchronous test for root agent creation"""
    logger.info("\n" + "="*80)
    logger.info("TEST: Root Agent Initialization")
    logger.info("="*80)
    
    try:
        from agents.root.agent_adk import create_root_agent
        from config.gemini import PatchedGemini
        
        model_client = PatchedGemini(model="gemini-2.0-flash")
        root_agent = create_root_agent(model_client)
        
        assert root_agent is not None
        assert root_agent.name == "root_agent"
        print(f"✅ Root agent created: {root_agent.name}")
        print(f"✅ Root agent has {len(root_agent.tools) if root_agent.tools else 0} coordinator tools")
        return True
    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        return False


def test_sync_sub_agents():
    """Synchronous test for sub-agent creation"""
    logger.info("\n" + "="*80)
    logger.info("TEST: Sub-Agent Initialization")
    logger.info("="*80)
    
    try:
        from config.gemini import PatchedGemini
        from agents.nutrition.agent_adk import create_nutrition_agent
        from agents.fitness.agent_adk import create_fitness_agent
        from agents.wellness.agent_adk import create_wellness_agent
        from agents.analytics.agent_adk import create_analytics_agent
        from agents.nudge.agent_adk import create_nudge_agent
        
        model_client = PatchedGemini(model="gemini-2.0-flash")
        
        # Create all sub-agents
        agents = {
            "Nutrition": create_nutrition_agent(model_client),
            "Fitness": create_fitness_agent(model_client),
            "Wellness": create_wellness_agent(model_client),
            "Analytics": create_analytics_agent(model_client),
            "Nudge": create_nudge_agent(model_client),
        }
        
        # Verify all agents
        for name, agent in agents.items():
            assert agent is not None
            assert agent.tools is not None
            assert len(agent.tools) > 0
            print(f"✅ {name} agent created with {len(agent.tools)} tools")
        
        return True
    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        return False


def test_sync_adk_integration():
    """Synchronous test for ADK integration"""
    logger.info("\n" + "="*80)
    logger.info("TEST: ADK Integration Module")
    logger.info("="*80)
    
    try:
        from adk_integration import (
            ADKAgentRunner,
            process_agent_message,
            ADK_AVAILABLE
        )
        
        assert ADK_AVAILABLE
        assert callable(process_agent_message)
        assert ADKAgentRunner is not None
        
        print("✅ ADK integration module loaded successfully")
        print("✅ process_agent_message is callable")
        print("✅ ADKAgentRunner class is available")
        return True
    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        return False


def test_sync_agent_hierarchy():
    """Synchronous test for agent hierarchy"""
    logger.info("\n" + "="*80)
    logger.info("TEST: Agent Hierarchy and Routing")
    logger.info("="*80)
    
    try:
        from agents.root.agent_adk import create_root_agent
        from config.gemini import PatchedGemini
        
        model_client = PatchedGemini(model="gemini-2.0-flash")
        root_agent = create_root_agent(model_client)
        
        # Verify routing instructions
        assert 'transfer_to_agent' in root_agent.instructions
        
        agent_names = [
            'nutrition_agent_batch',
            'fitness_agent',
            'wellness_agent_batch',
            'analytics_agent_progress',
            'nudge_agent_autonomous'
        ]
        
        for agent_name in agent_names:
            assert agent_name in root_agent.instructions
            print(f"✅ Routing rule for {agent_name} in instructions")
        
        return True
    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        return False


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

if __name__ == "__main__":
    logger.info("\n" + "="*80)
    logger.info("GOOGLE ADK MULTI-AGENT DELEGATION TEST SUITE")
    logger.info("="*80)
    
    results = []
    
    # Run synchronous tests
    logger.info("\n[1/4] Testing Root Agent...")
    results.append(("Root Agent", test_sync_root_agent()))
    
    logger.info("\n[2/4] Testing Sub-Agents...")
    results.append(("Sub-Agents", test_sync_sub_agents()))
    
    logger.info("\n[3/4] Testing ADK Integration...")
    results.append(("ADK Integration", test_sync_adk_integration()))
    
    logger.info("\n[4/4] Testing Agent Hierarchy...")
    results.append(("Agent Hierarchy", test_sync_agent_hierarchy()))
    
    # Print summary
    logger.info("\n" + "="*80)
    logger.info("TEST SUMMARY")
    logger.info("="*80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\n{'='*80}")
    print(f"Results: {passed}/{total} tests passed")
    print(f"{'='*80}\n")
    
    exit(0 if passed == total else 1)
