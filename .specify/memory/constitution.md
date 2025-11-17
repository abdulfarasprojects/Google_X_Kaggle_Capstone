<!--
Sync Impact Report:
- Version change: N/A → 1.0
- List of modified principles: All principles added (initial creation)
- Added sections: Technology Stack and Architecture Principles, Development Standards and Quality Assurance
- Removed sections: None
- Templates requiring updates: None (templates are generic)
- Follow-up TODOs: None
-->
# Weight Loss Chat Agent Constitution

## Core Principles

### I. User-Centric Design
All features prioritize user experience and mental health. Every design decision considers user well-being, accessibility, and positive reinforcement over punitive measures.

### II. Data Minimization
Only collect essential data required for weight loss tracking (calories, protein, water, sleep, steps, workouts). Store all data locally on device in MVP phase. No cloud synchronization or third-party data sharing.

### III. Transparency
Clear confidence levels for all AI-generated recommendations. No false claims about accuracy or effectiveness. Always disclose limitations and uncertainties to users.

### IV. Recommendation-Only
Agent never executes actions autonomously. All suggestions require user confirmation and action. Agent provides guidance and insights but does not control user behavior.

### V. Emotional Intelligence
Detect mental health risks through sentiment analysis. Escalate appropriately for crisis situations. Never shame users for setbacks or non-compliance. Focus on encouragement and support.

## Technology Stack and Architecture Principles

### Immutable Technology Stack

**Messaging Layer:**
- Platform: Telegram ONLY
- SDK: python-telegram-bot (async, MIT license)
- Python Version: 3.12+ (required, non-negotiable)
- License: All dependencies must be MIT, Apache 2.0, or GPL-compatible

**AI & Reasoning:**
- Foundation Model: Gemini 2.5 Flash (via google-generativeai SDK)
- Reasoning Framework: Google ADK (Agent Development Kit)
- Orchestration: LangGraph (for stateful workflows)
- Inference: No streaming (batch completion only), timeout 30 seconds max

**Database & State:**
- MVP Storage: SQLite (device-local only)
- Session Management: ADK LocalSessionService
- No ORM in MVP - Use raw SQL or lightweight query builders only

**Scheduling & Background Jobs:**
- Scheduler: APScheduler (asyncio-based)
- Timezone Support: User-aware timezones
- Persistence: In-memory with periodic database flush

**APIs (FREE TIER ONLY):**
- Food Database: USDA FoodData Central (free with API key)
- Backup Nutrition: Nutritionix API (free, no auth required)
- LLM API: Google Gemini (free tier or paid, but cost-tracked)

**Infrastructure:**
- Deployment: Google Cloud Run (serverless, auto-scaling)
- Containerization: Docker (Python 3.12 slim base image)
- CI/CD: GitHub Actions (free tier)
- Secrets Management: GitHub Repository Secrets

**Development Tools:**
- Package Manager: uv (ultra-fast)
- Testing Framework: pytest + pytest-asyncio
- Linting: ruff (Python linter, fast)
- Type Checking: pyright
- Documentation: Markdown + MkDocs

### Non-Negotiable Architecture Principles

**Agent Design:**
- Multi-Agent Pattern: Root agent (orchestrator) + 4 specialized sub-agents (Nutrition, Fitness, Wellness, Nudge)
- Each agent: Single responsibility, clear description for LLM delegation
- Delegation Method: LLM-driven (agent decides which sub-agent)
- Autonomy Level: RECOMMENDATION-ONLY
- Session State: Persistent per user, accessible to all agents

**Batch Processing:**
- NOT Real-time: Collect all items, ask confirmation, process together
- Batch Size Limit: 10 items per meal/workout/session max
- Timeout: 30 minutes of inactivity = auto-complete batch
- All-or-Nothing: If any item fails, entire batch fails (atomicity)
- User Confirmation: Always ask "Is that all?" before processing

**Tool Development:**
- Tool Definition: Every tool = Python async function with docstring + type hints
- Error Handling: All tools must catch exceptions, never crash agent
- Timeout: Every tool has max 5 sec timeout (except USDA API = 5 sec with Nutritionix fallback)
- Return Format: Consistent dict with "status", "data", "error" fields
- Idempotency: Tools must be safe to call multiple times with same input

**Memory & Context:**
- Long-Term Memory: Store ALL interactions for patterns (30-day rolling window)
- Emotional Context: Sentiment score + detected emotion + raw message
- Session Boundary: Resets at midnight (user's timezone)
- Privacy: Zero cloud storage in MVP (all local SQLite)

**Guardrails:**
1. Input Validation → Reject impossible values (negative calories, >500 reps)
2. Confidence Thresholding → Show ranges for <0.75 confidence
3. Hallucination Prevention → RAG with USDA DB (no unsourced claims)
4. Task Looping Prevention → Max 3 retries, exponential backoff
5. Emotional Safety → Multi-factor crisis detection, human escalation
6. Rate Limiting → Max 20 logs/day per user (eating disorder prevention)

## Development Standards and Quality Assurance

### Code Quality Standards

**Type Safety:**
- Requirement: 100% type hints on all function signatures
- Tool: pyright for static type checking
- CI/CD Check: Type checking fails build if issues found

**Code Style:**
- Format: Black formatter (88-character line length)
- Linter: Ruff (must pass with zero warnings in strict mode)
- Import Order: isort (standard)
- Docstrings: Google-style format, required on all modules/classes/functions

**Naming Conventions:**
- Files: snake_case.py for modules
- Agents: {domain}_agent.py
- Tools: {category}/{action}.py
- Classes: PascalCase
- Functions: snake_case
- Constants: UPPER_SNAKE_CASE

**Function Size & Complexity:**
- Max Function Length: 50 lines (excluding docstring)
- Max Cyclomatic Complexity: 5
- Max Nested Depth: 3 levels

### Testing & Evaluation Policies

**Unit Test Requirements:**
- Coverage Minimum: 80% for agents, 70% for tools
- Framework: pytest with pytest-asyncio
- Location: tests/unit/ mirroring source structure
- Execution: Run before every commit

**Integration Test Requirements:**
- Scope: Multi-agent interactions, end-to-end flows
- Location: tests/integration/
- Golden Test Sets: Documented in evals/
- Frequency: Run on every PR

**Evaluation Framework:**
- Tool: ADK built-in evaluation framework
- Metrics: Task Success Rate >90%, Hallucination Rate <5%, Emotional Accuracy >80%, Response Latency P95 <3 seconds

### Security & Privacy Best Practices

**GDPR Compliance:**
- Data Minimization: Only collect age, height, weight, activity level, meal entries, workouts, water, sleep, steps
- No Medical Data: Never ask for/store diagnoses, medications, health conditions
- Consent: Explicit opt-in for all data collection at onboarding
- Retention: Delete logs >90 days old automatically
- Right to Deletion: /delete_my_data command wipes all user data immediately

**Privacy-First Architecture:**
- Device-Local Storage: All data stored in SQLite on device (MVP)
- No Cloud Sync: Zero data transmitted to cloud in MVP
- No Third-Party Tracking: No Sentry, DataDog, mixpanel, etc.
- No Logs with Sensitive Data: Never log meal items, calorie counts, personal metrics

### Documentation Standards

**Required Documentation:**
1. README.md: Project overview, quick start, setup instructions
2. ARCHITECTURE.md: System design, component diagram, data flow
3. API_REFERENCE.md: All tools, agents, functions with examples
4. CONTRIBUTING.md: Development workflow, PR process, testing
5. CHANGELOG.md: Version history, breaking changes

**Code Documentation:**
- Module Docstring: One-line summary, then description
- Class Docstring: Purpose, attributes, methods (Google style)
- Function Docstring: Args, Returns, Raises, Example

### Workflow & Process Standards

**Speckit Workflow:**
1. Constitution First: Use /speckit.constitution to establish principles
2. Specification: Use /speckit.specify to define features with user stories
3. Planning: Use /speckit.plan to create technical design
4. Tasks: Use /speckit.tasks to generate actionable tasks
5. Implementation: Use /speckit.implement to generate code from tasks

**Git Workflow:**
- Branch Naming: feature/{issue-id}-{description} or bugfix/{issue-id}-{description}
- Commit Format: [TYPE] Description
- PR Process: Require 1 approval + tests passing before merge

**Code Review Standards:**
- Checklist for Every PR: Follows constitution principles, Unit tests pass, Integration tests pass, Type checking passes, Linting passes, Documentation updated

## Governance

This constitution establishes the non-negotiable principles for the Weight Loss Chat Agent project. All development must align with these principles. Amendments require justification, team consensus, and updated version numbering following semantic versioning.

Constitution supersedes all other practices. All PRs/reviews must verify compliance. Use speckit_constitution_best_practices.md for detailed guidance and examples.

**Version**: 1.0 | **Ratified**: 2025-11-17 | **Last Amended**: 2025-11-17
