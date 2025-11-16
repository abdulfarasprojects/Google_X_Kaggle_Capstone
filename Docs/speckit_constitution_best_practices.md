# Weight Loss Chat Agent: Speckit Constitution & Best Practices

**Document Version:** 1.0  
**Last Updated:** November 16, 2025  
**Framework:** GitHub Copilot Speckit  
**Purpose:** Foundational governance for spec-driven development

---

## Table of Contents

1. [Understanding Speckit Constitution](#understanding-speckit-constitution)
2. [Project Constitution Document](#project-constitution-document)
3. [Core Principles](#core-principles)
4. [Technology Stack Adherence](#technology-stack-adherence)
5. [Code Quality Standards](#code-quality-standards)
6. [Testing & Evaluation Policies](#testing--evaluation-policies)
7. [AI Agent Development Best Practices](#ai-agent-development-best-practices)
8. [Architecture Best Practices](#architecture-best-practices)
9. [Security & Privacy Best Practices](#security--privacy-best-practices)
10. [Documentation Standards](#documentation-standards)
11. [Workflow & Process Standards](#workflow--process-standards)

---

## Understanding Speckit Constitution

### What Is a Constitution in Speckit?

A **constitution.md** file in GitHub Speckit serves as the **governing document** for your entire project. It establishes:

1. **Non-negotiable principles** - Rules that NEVER change during development
2. **Opinionated stack guidance** - Technology choices that guide all decisions
3. **Quality standards** - Code quality, testing, documentation expectations
4. **Development conventions** - Coding style, naming, patterns, structure
5. **Process guardrails** - How code is written, reviewed, tested, deployed

### Why Constitution Matters

When you use `/speckit.specify`, `/speckit.plan`, `/speckit.tasks`, and `/speckit.implement`, the AI assistant will:
- **Reference the constitution** to ensure alignment
- **Reject specifications** that violate constitution principles
- **Generate consistent code** following constitution standards
- **Maintain architectural integrity** across all features
- **Prevent drift** in quality or approach

### Constitution vs. Copilot Instructions

| Aspect | Constitution.md | copilot-instructions.md |
|--------|-----------------|----------------------|
| **Scope** | Project-wide, immutable principles | File-specific, flexible guidance |
| **Used by** | All Speckit commands | Day-to-day Copilot interactions |
| **Frequency** | Updated once per major project phase | Updated frequently as needed |
| **Focus** | WHAT to build and WHY | HOW to implement details |
| **Authority** | Non-negotiable rules | Helpful suggestions |

---

## Project Constitution Document

### Template for `constitution.md`

Use this template with `/speckit.constitution` command:

```markdown
# Weight Loss Chat Agent - Project Constitution

**Project:** Weight Loss Chat Agent (Telegram)  
**Version:** 1.0  
**Created:** November 16, 2025  
**Last Updated:** [Current Date]  
**Status:** ACTIVE (Non-negotiable)

---

## I. CORE PROJECT MANDATE

### Project Vision
Build a lightweight, privacy-first weight loss coaching agent accessible via Telegram that helps users track 6 health metrics (calories, protein, water, sleep, steps, workouts) with personalized nudges and weekly synthesis.

### Foundational Pillars
1. **User-Centric Design** - All features prioritize user experience and mental health
2. **Data Minimization** - Only collect essential data, store locally (MVP), no cloud sync
3. **Transparency** - Clear confidence levels, no false claims, always disclose limitations
4. **Recommendation-Only** - Agent never executes actions autonomously, only suggests
5. **Emotional Intelligence** - Detect mental health risks, escalate appropriately, never shame
6. **Cost Effectiveness** - MVP uses free APIs only, no paid services

### Success Definition
- 70%+ daily active logging rate in first 30 days
- 50%+ 30-day retention
- <1% message delivery failures
- Zero false crisis escalations
- NPS >40 by end of Q1

---

## II. TECHNOLOGY STACK (IMMUTABLE)

### Messaging Layer
- **Platform:** Telegram ONLY (not WhatsApp, Discord, Slack)
- **SDK:** `python-telegram-bot` (async, MIT license)
- **Python Version:** 3.12+ (required, non-negotiable)
- **License:** All dependencies must be MIT, Apache 2.0, or GPL-compatible

### AI & Reasoning
- **Foundation Model (MVP):** Gemini 2.5 Flash (via google-generativeai SDK)
- **Reasoning Framework:** Google ADK (Agent Development Kit)
- **Orchestration:** LangGraph (for stateful workflows, not LangChain)
- **Inference:** No streaming (batch completion only), timeout 30 seconds max

### Database & State
- **MVP Storage:** SQLite (device-local only)
- **Session Management:** ADK LocalSessionService (not cloud-based)
- **No ORM in MVP** - Use raw SQL or lightweight query builders only
- **Vector DB:** Postponed to Q2 (not in MVP)

### Scheduling & Background Jobs
- **Scheduler:** APScheduler (asyncio-based, not Celery)
- **Timezone Support:** User-aware timezones (not UTC-only)
- **Persistence:** In-memory with periodic database flush (not external queue)

### APIs (FREE TIER ONLY)
- **Food Database:** USDA FoodData Central (free with API key)
- **Backup Nutrition:** Nutritionix API (free, no auth required)
- **LLM API:** Google Gemini (free tier or paid, but cost-tracked)
- **Monitoring:** Open-source only (no Sentry, DataDog, etc.)

### Infrastructure
- **Deployment:** Google Cloud Run (serverless, auto-scaling)
- **Containerization:** Docker (Python 3.12 slim base image)
- **CI/CD:** GitHub Actions (free tier)
- **Secrets Management:** GitHub Repository Secrets (not third-party)

### Development Tools
- **Package Manager:** `uv` (ultra-fast, not pip, not Poetry)
- **Testing Framework:** pytest + pytest-asyncio
- **Linting:** ruff (Python linter, fast)
- **Type Checking:** pyright (no mypy - too slow)
- **Documentation:** Markdown + MkDocs (not Sphinx)

---

## III. ARCHITECTURE PRINCIPLES (NON-NEGOTIABLE)

### Agent Design
- **Multi-Agent Pattern:** Root agent (orchestrator) + 4 specialized sub-agents (Nutrition, Fitness, Wellness, Nudge)
- **Each agent:** Single responsibility, clear description for LLM delegation
- **Delegation Method:** LLM-driven (agent decides which sub-agent, not if-then logic)
- **Autonomy Level:** RECOMMENDATION-ONLY (no action execution)
- **Session State:** Persistent per user, accessible to all agents

### Batch Processing
- **NOT Real-time:** Collect all items, ask confirmation, process together
- **Batch Size Limit:** 10 items per meal/workout/session max
- **Timeout:** 30 minutes of inactivity = auto-complete batch
- **All-or-Nothing:** If any item fails, entire batch fails (atomicity)
- **User Confirmation:** Always ask "Is that all?" before processing

### Tool Development
- **Tool Definition:** Every tool = Python async function with docstring + type hints
- **Error Handling:** All tools must catch exceptions, never crash agent
- **Timeout:** Every tool has max 5 sec timeout (except USDA API = 5 sec with Nutritionix fallback)
- **Return Format:** Consistent dict with "status", "data", "error" fields
- **Idempotency:** Tools must be safe to call multiple times with same input

### Memory & Context
- **Long-Term Memory:** Store ALL interactions for patterns (30-day rolling window)
- **Emotional Context:** Sentiment score + detected emotion + raw message
- **Session Boundary:** Resets at midnight (user's timezone)
- **Privacy:** Zero cloud storage in MVP (all local SQLite)

### Guardrails (Non-Negotiable Implementation)
1. **Input Validation** → Reject impossible values (negative calories, >500 reps)
2. **Confidence Thresholding** → Show ranges for <0.75 confidence
3. **Hallucination Prevention** → RAG with USDA DB (no unsourced claims)
4. **Task Looping Prevention** → Max 3 retries, exponential backoff
5. **Emotional Safety** → Multi-factor crisis detection, human escalation
6. **Rate Limiting** → Max 20 logs/day per user (eating disorder prevention)

---

## IV. CODE QUALITY STANDARDS

### Type Safety
- **Requirement:** 100% type hints on all function signatures
- **Tool:** pyright for static type checking
- **CI/CD Check:** Type checking fails build if issues found
- **Exception:** No `Any` type except in tool decorators (ADK-required)

### Code Style
- **Format:** Black formatter (88-character line length)
- **Linter:** Ruff (must pass with zero warnings in strict mode)
- **Import Order:** isort (standard, not custom)
- **Docstrings:** Google-style format, required on all modules/classes/functions

### Naming Conventions
- **Files:** `snake_case.py` for modules
- **Agents:** `{domain}_agent.py` (e.g., `nutrition_agent.py`)
- **Tools:** `{category}/{action}.py` (e.g., `tools/nutrition/food_parser.py`)
- **Classes:** `PascalCase`
- **Functions:** `snake_case`
- **Constants:** `UPPER_SNAKE_CASE`
- **Private:** Prefix with `_` (e.g., `_internal_helper()`)

### File Organization
```
weight_loss_agent/
├── agents/
│   ├── root/
│   ├── nutrition/
│   ├── fitness/
│   ├── wellness/
│   └── nudge/
├── tools/
│   ├── intent_classifier.py
│   ├── sentiment_detector.py
│   ├── batch_state_manager.py
│   ├── nutrition/
│   ├── fitness/
│   └── wellness/
├── scheduler/
├── telegram_bot/
├── guardrails/
├── evals/
├── tests/
├── config.py
└── main.py
```

### Function Size & Complexity
- **Max Function Length:** 50 lines (excluding docstring)
- **Max Cyclomatic Complexity:** 5 (measured by radon)
- **Max Nested Depth:** 3 levels
- **Long Functions:** Extract into smaller functions, not longer

### Error Handling
- **Never Ignore Exceptions:** Use `except Exception:` only as last resort
- **Specific Catch:** Catch specific exceptions (e.g., `asyncio.TimeoutError`)
- **Always Log:** Log before re-raising or returning error
- **User Message:** Always include non-technical error message for user

```python
try:
    result = await usda_api.query(food)
except asyncio.TimeoutError:
    logger.warning(f"USDA API timeout for {food}")
    return {"status": "error", "message": "Lookup timed out, using fallback"}
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    return {"status": "error", "message": "System error, please try again"}
```

---

## V. TESTING & EVALUATION POLICIES

### Unit Test Requirements
- **Coverage Minimum:** 80% for agents, 70% for tools
- **Framework:** pytest with pytest-asyncio
- **Location:** `tests/unit/` mirroring source structure
- **Naming:** `test_{module_name}.py`
- **Execution:** Run before every commit

### Integration Test Requirements
- **Scope:** Multi-agent interactions, end-to-end flows
- **Location:** `tests/integration/`
- **Golden Test Sets:** Documented in `evals/` (user stories)
- **Frequency:** Run on every PR

### Evaluation Framework (ADK)
- **Tool:** ADK built-in evaluation framework
- **Metrics:**
  - Task Success Rate (LSR): >90% for logging
  - Hallucination Rate: <5%
  - Emotional Accuracy: >80%
  - Response Latency P95: <3 seconds
  - Confidence Thresholding: Correctly qualified <75% confidence
  
### Acceptance Criteria Checklist
Every feature must pass:
- [ ] Unit tests pass (80%+ coverage)
- [ ] Integration tests pass
- [ ] Golden test set passes
- [ ] Guardrails not violated
- [ ] Type checking passes (pyright)
- [ ] Linting passes (ruff)
- [ ] Documentation updated
- [ ] No new TODO comments

---

## VI. AI AGENT DEVELOPMENT BEST PRACTICES

### Agent Definition Best Practices

```python
# ❌ BAD: Vague description, no guardrails
nutrition_agent = LlmAgent(
    name="nutrition",
    description="Handles nutrition",
)

# ✅ GOOD: Clear, specific, guardrailed
nutrition_agent = LlmAgent(
    name="nutrition_agent_batch",
    description="Processes complete meal batches. Receives list of all foods for one meal, queries USDA FoodData Central, returns total calories and protein with confidence scores.",
    instruction="""
You are a nutrition specialist receiving COMPLETE MEAL BATCHES.

YOUR TASK:
- Never process individual items - you receive complete meals only
- Query USDA FDB for each food
- Calculate totals
- Flag unusually high/low calorie meals

CONSTRAINTS:
- If USDA lookup fails: Use Nutritionix API backup
- Never diagnose nutritional deficiencies ("You have X deficiency")
- Always include confidence levels
""",
    tools=[batch_parser, usda_lookup, calorie_calc]
)
```

### Tool Definition Best Practices

```python
# ❌ BAD: Insufficient documentation
def parse_food(text):
    return parsed_food

# ✅ GOOD: Full documentation, type hints, error handling
async def parse_food_entry(
    food_description: str,
    user_id: str,
    tool_context: Optional[ToolContext] = None
) -> Dict[str, Any]:
    """
    Parse natural language food entry and estimate nutrition.
    
    Collects individual food items and estimates calories/protein from
    USDA FoodData Central database.
    
    Args:
        food_description (str): User's food description (e.g., "2 eggs scrambled")
        user_id (str): User ID for personalization
        tool_context (ToolContext, optional): ADK tool context
    
    Returns:
        dict: {
            "status": "success" | "error",
            "foods": [{"name": str, "quantity": str, "calories": int, "protein": float}],
            "confidence": float (0.0-1.0),
            "error_message": str (if status="error")
        }
    
    Raises:
        ValueError: If food_description is empty or <3 characters
    
    Example:
        >>> await parse_food_entry("2 eggs scrambled", "user_123")
        {"status": "success", "foods": [...], "confidence": 0.92}
    """
    
    # GUARDRAIL 1: Input validation
    if not food_description or len(food_description.strip()) < 3:
        raise ValueError("Food description too vague (<3 chars)")
    
    try:
        # Implementation with error handling
        result = await _parse_with_fallbacks(food_description)
        return result
    except Exception as e:
        logger.error(f"Parse error for '{food_description}': {e}")
        return {"status": "error", "error_message": str(e)}
```

### Delegation Pattern

```python
# ✅ CORRECT: Agent decides delegation
root_agent_instruction = """
You have access to:
- nutrition_agent: For food logging, calorie tracking
- fitness_agent: For workout logging, progression
- wellness_agent: For water, sleep, steps
- nudge_agent: For generating nudges (for ROOT to send)

WHEN TO DELEGATE:
1. User mentions food/meals → Delegate to nutrition_agent
2. User mentions workouts → Delegate to fitness_agent
3. User mentions water/sleep/steps → Delegate to wellness_agent
4. You're generating nudge → Delegate to nudge_agent

DO NOT:
- Use if-then logic to decide
- Call all agents on every message
- Delegate to wrong agent

DO:
- Let LLM reason about best agent
- Delegate to ONE agent per message (unless multi-intent)
- Synthesize responses from agents
"""
```

---

## VII. ARCHITECTURE BEST PRACTICES

### Layered Architecture

```
┌──────────────────────┐
│   Telegram Layer     │ - Bot commands, message handling
│   (telegram_bot/)    │ - Webhook validation, rate limiting
└──────────────────────┘
         ↓
┌──────────────────────┐
│  Root Agent Layer    │ - Orchestration, intent classification
│  (agents/root/)      │ - Response synthesis
└──────────────────────┘
         ↓
┌──────────────────────┐
│  Sub-Agent Layer     │ - Nutrition, Fitness, Wellness, Nudge
│  (agents/{domain}/)  │ - Domain-specific logic
└──────────────────────┘
         ↓
┌──────────────────────┐
│   Tool Layer         │ - Function tools, utilities
│   (tools/)           │ - External API calls, parsing
└──────────────────────┘
         ↓
┌──────────────────────┐
│   Guard Rail Layer   │ - Validation, safety checks
│   (guardrails/)      │ - Error handling
└──────────────────────┘
         ↓
┌──────────────────────┐
│  Persistence Layer   │ - SQLite, session management
│  (database/)         │ - State management
└──────────────────────┘
```

### Dependency Injection

```python
# ✅ GOOD: Inject dependencies, not hard-code
async def create_nutrition_agent(
    usda_api: USDAClient,
    session_service: SessionService,
    config: Config
) -> LlmAgent:
    """Create Nutrition Agent with injected dependencies."""
    parser_tool = FunctionTool(
        func=lambda items: parse_meal_batch(items, usda_api)
    )
    
    return LlmAgent(
        name="nutrition_agent",
        tools=[parser_tool],
        model=config.LLM_MODEL
    )

# ❌ BAD: Hard-coded dependencies
nutrition_agent = LlmAgent(
    name="nutrition",
    tools=[
        FunctionTool(func=parse_meal_batch)  # Where's the USDA client?
    ]
)
```

### Async/Await Requirements

- **All I/O Operations:** Must be async (API calls, database, file I/O)
- **Tool Functions:** Always async, even if no I/O (for consistency)
- **Never Block:** No `time.sleep()`, use `asyncio.sleep()`
- **Timeout Handling:** Always wrap I/O with `asyncio.wait_for(timeout=5)`

```python
# ✅ GOOD
async def query_usda_api(food: str) -> Dict:
    try:
        result = await asyncio.wait_for(
            _query_usda(food),
            timeout=5
        )
        return result
    except asyncio.TimeoutError:
        return await query_nutritionix_backup(food)

# ❌ BAD
def query_usda_api(food: str) -> Dict:
    time.sleep(10)  # Blocking, bad!
    return requests.get(...).json()  # Synchronous, bad!
```

---

## VIII. SECURITY & PRIVACY BEST PRACTICES

### GDPR Compliance (MVP)

- **Data Minimization:** Only collect age, height, weight, activity level, meal entries, workouts, water, sleep, steps
- **No Medical Data:** Never ask for/store diagnoses, medications, health conditions
- **Consent:** Explicit opt-in for all data collection at onboarding
- **Retention:** Delete logs >90 days old automatically
- **Right to Deletion:** /delete_my_data command wipes all user data immediately

### Privacy-First Architecture

- **Device-Local Storage:** All data stored in SQLite on device (MVP)
- **No Cloud Sync:** Zero data transmitted to cloud in MVP
- **No Third-Party Tracking:** No Sentry, DataDog, mixpanel, etc.
- **No Logs with Sensitive Data:** Never log meal items, calorie counts, personal metrics

```python
# ✅ GOOD: Safe logging
logger.info(f"User logged meal: success, confidence: {confidence}")

# ❌ BAD: Logs sensitive data
logger.info(f"User logged: {food_items}, calories: {total_cal}, protein: {protein}")
```

### Secret Management

- **Never Hardcode Secrets:** All API keys in .env or GitHub Secrets
- **Rotation:** Change API keys every 90 days
- **Scope:** Use minimal API scopes (Telegram bot token, not admin token)
- **Audit:** Log all API key usage (which key, when, what endpoint)

```python
# ✅ GOOD
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN not found in environment")

# ❌ BAD
TELEGRAM_BOT_TOKEN = "123456789:ABCdefGHIjklMNOpqrsTUVwxyzABCDEFGhi"  # Exposed!
```

---

## IX. DOCUMENTATION STANDARDS

### Required Documentation

1. **README.md:** Project overview, quick start, setup instructions
2. **ARCHITECTURE.md:** System design, component diagram, data flow
3. **API_REFERENCE.md:** All tools, agents, functions with examples
4. **CONTRIBUTING.md:** Development workflow, PR process, testing
5. **CHANGELOG.md:** Version history, breaking changes
6. **.md per major component:** (e.g., `docs/agents.md`, `docs/tools.md`)

### Code Documentation

- **Module Docstring:** One-line summary, then description
- **Class Docstring:** Purpose, attributes, methods (Google style)
- **Function Docstring:** Args, Returns, Raises, Example
- **Complex Logic:** Inline comments explaining "why", not "what"

```python
"""Weight loss agent root orchestrator."""

class RootAgent:
    """
    Orchestrates multi-agent system for weight loss tracking.
    
    Attributes:
        name (str): Agent name
        nutrition_agent (LlmAgent): Handles food logging
        model (str): LLM model name
    
    Example:
        >>> agent = RootAgent(config)
        >>> response = await agent.run(user_message)
    """
    
    async def run(self, user_message: str) -> str:
        """
        Process user message and generate response.
        
        Args:
            user_message (str): User's input
        
        Returns:
            str: Agent's response
        
        Raises:
            ValueError: If message is empty
        
        Example:
            >>> response = await agent.run("Had 2 eggs for breakfast")
            >>> print(response)
            "Logged! 140 cal, 12g protein ✅"
        """
```

---

## X. WORKFLOW & PROCESS STANDARDS

### Speckit Workflow (REQUIRED)

1. **Constitution First:** Use `/speckit.constitution` to establish principles (THIS DOCUMENT)
2. **Specification:** Use `/speckit.specify` to define features with user stories
3. **Planning:** Use `/speckit.plan` to create technical design
4. **Tasks:** Use `/speckit.tasks` to generate actionable tasks
5. **Implementation:** Use `/speckit.implement` to generate code from tasks

### Git Workflow

- **Branch Naming:** `feature/{issue-id}-{description}` or `bugfix/{issue-id}-{description}`
- **Commit Format:** `[TYPE] Description` (e.g., `[FEATURE] Add batch processing for meals`)
- **PR Process:** Require 1 approval + tests passing before merge
- **Merging:** Squash commits, delete branch after merge

### Code Review Standards

- **Checklist for Every PR:**
  - [ ] Follows constitution principles
  - [ ] 80%+ test coverage (agents/tools)
  - [ ] Type hints: pyright passes
  - [ ] Linting: ruff passes
  - [ ] Documentation updated
  - [ ] No new warnings/TODOs
  - [ ] Guardrails reviewed (if changes safety logic)
  - [ ] User stories updated (if spec changes)

### Testing Standards

- **Test Before Commit:** Run full test suite locally
- **Test on PR:** GitHub Actions must pass
- **Production Simulation:** Test with real Telegram in staging first
- **Rollback Plan:** Always have rollback procedure documented

### Documentation Synchronization

- **User Stories:** Keep `.specify/specs.md` in sync with actual features
- **Architecture:** Update `ARCHITECTURE.md` if component layout changes
- **API Changes:** Update `API_REFERENCE.md` when tools/agents change
- **Constitution:** Update only for major paradigm shifts (rare!)

---

## XI. CONSTITUTION MAINTENANCE

### When to Update Constitution

- ❌ DON'T update for: Daily features, bug fixes, UI tweaks
- ✅ DO update for: New technology stack, new principles, major architectural shift

### Update Process

1. **Proposal:** Create issue with justification
2. **Discussion:** Get team consensus before changing
3. **Amendment:** Update `constitution.md` with rationale
4. **Alignment:** Regenerate specs, plans with updated constitution
5. **Implementation:** Roll out aligned changes

### Version Control

```markdown
## Constitution History

### v1.0 (Nov 16, 2025) - Initial Release
- Telegram-only platform
- 4-agent system (Root + Nutrition + Fitness + Wellness + Nudge)
- Device-local storage (MVP)
- Python 3.12 + Google ADK + LangGraph

### v1.1 (TBD) - Potential Updates
- Cloud sync (Q2)
- Image recognition (Q2)
- Advanced NLP (Q2)
```

---

## XII. SPECKIT COMMAND REFERENCE

### For `/speckit.constitution` Prompt

```
/speckit.constitution Create principles focused on:
1. AI Agent Design: Multi-agent architecture with batch processing and recommendation-only autonomy
2. Code Quality: 100% type hints, Google-style docstrings, 80%+ test coverage
3. Testing Standards: Unit, integration, golden test sets with ADK evals
4. Privacy-First Design: Device-local storage, GDPR compliance, no cloud sync in MVP
5. Guardrails & Safety: Input validation, hallucination prevention, emotional safety, rate limiting
6. Batch Processing: All-or-nothing atomicity, 10-item limits, 30-min timeout
7. Error Recovery: Fallback chains, idempotent operations, graceful degradation
8. Scheduling: APScheduler for autonomous nudges, timezone-aware
9. Documentation: Architecture, API reference, code comments, git workflow
10. Development Workflow: Speckit-driven, git-based, PR review required
```

### For `/speckit.specify` Prompt

```
/speckit.specify Define requirements for:
User stories covering:
1. User onboarding and profile setup
2. Meal logging (simple and batch)
3. Workout logging
4. Water, sleep, steps tracking
5. Viewing progress and streaks
6. Receiving nudges (morning, midday, evening, weekly, streak-protection)

Edge cases including:
- API timeouts and fallbacks
- Batch collection timeout
- Negative/impossible values
- Emotional crises
- Multi-timezone users
- Session crashes
- Data duplication

Acceptance criteria: All user stories testable, edge cases recoverable
```

### For `/speckit.plan` Prompt

```
/speckit.plan Design the technical implementation:
1. Architecture: 4-agent system with root orchestrator
2. Technology: Python 3.12, Google ADK, LangGraph, Telegram Bot API, SQLite, APScheduler
3. Layers: Telegram → Root Agent → Sub-Agents → Tools → Guardrails → Storage
4. APIs: USDA FoodData Central (free), Nutritionix (free backup), Gemini 2.5 Flash
5. Batch Processing: Collection → Confirmation → All-or-Nothing Processing
6. Guardrails: Input validation, confidence thresholding, hallucination prevention
7. Testing: Unit (80%), integration (golden sets), ADK evals
8. Deployment: Docker → Cloud Run, GitHub Actions CI/CD
9. Data: SQLite device-local, 90-day retention, GDPR compliant
```

---

## XIII. QUICK START FOR DEVELOPERS

### Step 1: Understand Constitution

```bash
# Read this document thoroughly
# Understand the non-negotiable principles
# Review technology stack, guardrails, best practices
```

### Step 2: Set Up Speckit Project

```bash
# Initialize Speckit project
specify init weight_loss_agent --ai copilot

# Create constitution
/speckit.constitution [Use prompt from Section XII]

# Review generated constitution.md
cat .specify/memory/constitution.md
```

### Step 3: Create Feature Specs

```bash
# Define feature requirements
/speckit.specify [Use prompt from Section XII]

# Review generated spec
cat .specify/specs.md

# Approve or iterate
```

### Step 4: Generate Technical Plan

```bash
# Create implementation plan
/speckit.plan [Use prompt from Section XII]

# Review architecture, tech choices
cat .specify/plan.md
```

### Step 5: Break Down into Tasks

```bash
# Generate actionable tasks
/speckit.tasks

# Review task list
cat .specify/tasks.md

# Assign tasks to developers
```

### Step 6: Implement with Copilot

```bash
# Implement tasks with Copilot
/speckit.implement [Specific task description]

# Review generated code
# Ensure constitution alignment
# Run tests before committing
```

---

## Constitution Checklist for All Development

Before writing any code, verify:

- [ ] User story in `/specify/specs.md`
- [ ] Acceptance criteria clearly defined
- [ ] Edge cases identified in user story
- [ ] Technical plan in `/specify/plan.md`
- [ ] Tasks broken down in `/specify/tasks.md`
- [ ] Task aligns with constitution principles
- [ ] Type hints planned (100% coverage target)
- [ ] Tests planned (80%+ coverage target)
- [ ] Documentation planned
- [ ] Guardrails reviewed (if applicable)
- [ ] Approvals from 1 reviewer

---

## Summary: Constitution as Compass

Think of this constitution as a **compass**, not a **rulebook**:

- **Compass** guides all decisions consistently
- **Rulebook** would be too rigid for evolving project

When you use Speckit commands, the constitution ensures:
- ✅ Specifications align with principles
- ✅ Plans follow approved tech stack
- ✅ Tasks are granular and testable
- ✅ Implementation maintains consistency

**The constitution is the difference between "random development" and "principled development."**

---

**Document Status:** ✅ Complete, Ready for Speckit Usage  
**Version:** 1.0  
**Created:** November 16, 2025  
**Next Step:** Run `/speckit.constitution [prompt]` in GitHub Copilot