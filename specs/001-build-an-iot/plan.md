# Implementation Plan: IoT Telemetry Dashboard

**Branch**: `001-build-an-iot` | **Date**: 2025-09-12 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-build-an-iot/spec.md`

## Execution Flow (/plan command scope)
```
1. Load feature spec from Input path
   → If not found: ERROR "No feature spec at {path}"
2. Fill Technical Context (scan for NEEDS CLARIFICATION)
   → Detect Project Type from context (web=frontend+backend, mobile=app+api)
   → Set Structure Decision based on project type
3. Evaluate Constitution Check section below
   → If violations exist: Document in Complexity Tracking
   → If no justification possible: ERROR "Simplify approach first"
   → Update Progress Tracking: Initial Constitution Check
4. Execute Phase 0 → research.md
   → If NEEDS CLARIFICATION remain: ERROR "Resolve unknowns"
5. Execute Phase 1 → contracts, data-model.md, quickstart.md, agent-specific template file (e.g., `CLAUDE.md` for Claude Code, `.github/copilot-instructions.md` for GitHub Copilot, or `GEMINI.md` for Gemini CLI).
6. Re-evaluate Constitution Check section
   → If new violations: Refactor design, return to Phase 1
   → Update Progress Tracking: Post-Design Constitution Check
7. Plan Phase 2 → Describe task generation approach (DO NOT create tasks.md)
8. STOP - Ready for /tasks command
```

**IMPORTANT**: The /plan command STOPS at step 7. Phases 2-4 are executed by other commands:
- Phase 2: /tasks command creates tasks.md
- Phase 3-4: Implementation execution (manual or via tools)

## Summary
Real-time IoT telemetry dashboard that ingests MQTT data (vibration, temperature, power, electricity) from hierarchically organized devices and displays them as live charts with historical trending capabilities.

## Technical Context
**Language/Version**: TypeScript with Next.js (React framework)  
**Primary Dependencies**: Next.js, VisActor (visualization), Tailwind CSS, Shadcn UI components, Jotai (state management)  
**Storage**: PostgreSQL (device metadata/organization hierarchy), InfluxDB (telemetry time-series data)  
**Testing**: Vitest (unit tests), Playwright (E2E tests)  
**Target Platform**: Web application (browser-based dashboard)
**Project Type**: web - frontend + backend API  
**Performance Goals**: Real-time updates (1-second frequency), support thousands of concurrent devices  
**Constraints**: <200ms chart update latency, handle high-frequency data ingestion (1Hz per device)  
**Scale/Scope**: Multiple organizations, hundreds of sites, thousands of devices, continuous telemetry streams

## Constitution Check
*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Simplicity**:
- Projects: 2 (frontend, backend) - within limit of 3
- Using framework directly? Yes - Next.js, VisActor used directly without wrappers
- Single data model? Yes - shared TypeScript interfaces between frontend/backend
- Avoiding patterns? Yes - direct service calls, no Repository pattern unless proven needed

**Architecture**:
- EVERY feature as library? Yes - telemetry ingestion, visualization, auth as separate libraries
- Libraries listed: mqtt-ingestion (MQTT client), telemetry-viz (charts), device-hierarchy (org/site/area)
- CLI per library: Yes - each library will expose CLI for testing/management
- Library docs: llms.txt format planned? Yes

**Testing (NON-NEGOTIABLE)**:
- RED-GREEN-Refactor cycle enforced? Yes - tests written first, must fail before implementation
- Git commits show tests before implementation? Yes - commit strategy will show test commits before implementation
- Order: Contract→Integration→E2E→Unit strictly followed? Yes
- Real dependencies used? Yes - actual PostgreSQL/InfluxDB instances for integration tests
- Integration tests for: new libraries, contract changes, shared schemas? Yes
- FORBIDDEN: Implementation before test, skipping RED phase

**Observability**:
- Structured logging included? Yes - structured JSON logging for both frontend and backend
- Frontend logs → backend? Yes - unified logging stream via API
- Error context sufficient? Yes - full context including device IDs, timestamps, error chains

**Versioning**:
- Version number assigned? Yes - 0.1.0 (initial version)
- BUILD increments on every change? Yes
- Breaking changes handled? Yes - API versioning strategy, parallel tests during transitions

## Project Structure

### Documentation (this feature)
```
specs/[###-feature]/
├── plan.md              # This file (/plan command output)
├── research.md          # Phase 0 output (/plan command)
├── data-model.md        # Phase 1 output (/plan command)
├── quickstart.md        # Phase 1 output (/plan command)
├── contracts/           # Phase 1 output (/plan command)
└── tasks.md             # Phase 2 output (/tasks command - NOT created by /plan)
```

### Source Code (repository root)
```
# Option 1: Single project (DEFAULT)
src/
├── models/
├── services/
├── cli/
└── lib/

tests/
├── contract/
├── integration/
└── unit/

# Option 2: Web application (when "frontend" + "backend" detected)
backend/
├── src/
│   ├── models/
│   ├── services/
│   └── api/
└── tests/

frontend/
├── src/
│   ├── components/
│   ├── pages/
│   └── services/
└── tests/

# Option 3: Mobile + API (when "iOS/Android" detected)
api/
└── [same as backend above]

ios/ or android/
└── [platform-specific structure]
```

**Structure Decision**: Option 2 (Web application) - frontend + backend structure due to web project type with separate API backend

## Phase 0: Outline & Research
1. **Extract unknowns from Technical Context** above:
   - For each NEEDS CLARIFICATION → research task
   - For each dependency → best practices task
   - For each integration → patterns task

2. **Generate and dispatch research agents**:
   ```
   For each unknown in Technical Context:
     Task: "Research {unknown} for {feature context}"
   For each technology choice:
     Task: "Find best practices for {tech} in {domain}"
   ```

3. **Consolidate findings** in `research.md` using format:
   - Decision: [what was chosen]
   - Rationale: [why chosen]
   - Alternatives considered: [what else evaluated]

**Output**: research.md with all NEEDS CLARIFICATION resolved

## Phase 1: Design & Contracts
*Prerequisites: research.md complete*

1. **Extract entities from feature spec** → `data-model.md`:
   - Entity name, fields, relationships
   - Validation rules from requirements
   - State transitions if applicable

2. **Generate API contracts** from functional requirements:
   - For each user action → endpoint
   - Use standard REST/GraphQL patterns
   - Output OpenAPI/GraphQL schema to `/contracts/`

3. **Generate contract tests** from contracts:
   - One test file per endpoint
   - Assert request/response schemas
   - Tests must fail (no implementation yet)

4. **Extract test scenarios** from user stories:
   - Each story → integration test scenario
   - Quickstart test = story validation steps

5. **Update agent file incrementally** (O(1) operation):
   - Run `/scripts/update-agent-context.sh [claude|gemini|copilot]` for your AI assistant
   - If exists: Add only NEW tech from current plan
   - Preserve manual additions between markers
   - Update recent changes (keep last 3)
   - Keep under 150 lines for token efficiency
   - Output to repository root

**Output**: data-model.md, /contracts/*, failing tests, quickstart.md, agent-specific file

## Phase 2: Task Planning Approach
*This section describes what the /tasks command will do - DO NOT execute during /plan*

**Task Generation Strategy**:
- Load `/templates/tasks-template.md` as base
- Generate tasks from Phase 1 design docs (contracts, data model, quickstart)
- API contract endpoints → contract test tasks [P]
- Data model entities (6 total) → model creation tasks [P]
- Libraries (mqtt-ingestion, telemetry-viz, device-hierarchy) → library structure tasks [P]
- User stories (5 acceptance scenarios) → integration test tasks
- TDD implementation tasks to make all tests pass

**IoT-Specific Task Categories**:
1. **Database Setup**: PostgreSQL migrations, InfluxDB schema setup
2. **MQTT Integration**: Server-side MQTT client, message parsing, data validation
3. **Real-time Streaming**: SSE implementation, WebSocket fallback
4. **Visualization**: VisActor chart components, real-time data updates
5. **Authentication**: JWT-based auth, organization permissions
6. **Frontend Components**: Dashboard layout, filtering, time range selection

**Ordering Strategy**:
- TDD order: Contract tests → Integration tests → Unit tests → Implementation
- Dependency order: Data models → API services → MQTT ingestion → Frontend components
- Infrastructure first: Database setup → Auth → Core APIs → Real-time features → UI
- Mark [P] for parallel execution (independent files/libraries)

**Estimated Output**: 35-40 numbered, ordered tasks in tasks.md

**Key TDD Sequences**:
1. PostgreSQL model tests → Model implementations → Service tests → Service implementations
2. InfluxDB schema tests → Schema setup → Telemetry API tests → API implementations  
3. MQTT client tests → MQTT service → Integration tests → Real-time streaming
4. Component tests → React components → E2E tests → Dashboard integration

**IMPORTANT**: This phase is executed by the /tasks command, NOT by /plan

## Phase 3+: Future Implementation
*These phases are beyond the scope of the /plan command*

**Phase 3**: Task execution (/tasks command creates tasks.md)  
**Phase 4**: Implementation (execute tasks.md following constitutional principles)  
**Phase 5**: Validation (run tests, execute quickstart.md, performance validation)

## Complexity Tracking
*Fill ONLY if Constitution Check has violations that must be justified*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |


## Progress Tracking
*This checklist is updated during execution flow*

**Phase Status**:
- [x] Phase 0: Research complete (/plan command)
- [x] Phase 1: Design complete (/plan command)
- [x] Phase 2: Task planning complete (/plan command - describe approach only)
- [ ] Phase 3: Tasks generated (/tasks command)
- [ ] Phase 4: Implementation complete
- [ ] Phase 5: Validation passed

**Gate Status**:
- [x] Initial Constitution Check: PASS
- [x] Post-Design Constitution Check: PASS
- [x] All NEEDS CLARIFICATION resolved
- [x] Complexity deviations documented (none - all within limits)

---
*Based on Constitution v2.1.1 - See `/memory/constitution.md`*