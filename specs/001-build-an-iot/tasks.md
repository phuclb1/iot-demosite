# Tasks: IoT Telemetry Dashboard

**Input**: Design documents from `/specs/001-build-an-iot/`
**Prerequisites**: plan.md (✓), research.md (✓), data-model.md (✓), contracts/ (✓)

## Execution Flow (main)
```
1. Load plan.md from feature directory
   → If not found: ERROR "No implementation plan found"
   → Extract: tech stack, libraries, structure
2. Load optional design documents:
   → data-model.md: Extract entities → model tasks
   → contracts/: Each file → contract test task
   → research.md: Extract decisions → setup tasks
3. Generate tasks by category:
   → Setup: project init, dependencies, linting
   → Tests: contract tests, integration tests
   → Core: models, services, CLI commands
   → Integration: DB, middleware, logging
   → Polish: unit tests, performance, docs
4. Apply task rules:
   → Different files = mark [P] for parallel
   → Same file = sequential (no [P])
   → Tests before implementation (TDD)
5. Number tasks sequentially (T001, T002...)
6. Generate dependency graph
7. Create parallel execution examples
8. Validate task completeness:
   → All contracts have tests?
   → All entities have models?
   → All endpoints implemented?
9. Return: SUCCESS (tasks ready for execution)
```

## Format: `[ID] [P?] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- Include exact file paths in descriptions

## Path Conventions
- **Web app**: `backend/src/`, `frontend/src/`
- Tech Stack: Backend: Python 3.12, FastAPI, asyncpg, asyncio-mqtt. Frontend: TypeScript, Next.js, VisActor, PostgreSQL, InfluxDB
- Testing: Backend: pytest, pytest-asyncio. Frontend: Vitest (unit), Playwright (E2E)

## Phase 3.1: Project Setup

- [x] T001 Create project structure with backend/ and frontend/ directories per plan.md
- [x] T002 Initialize Next.js frontend with TypeScript, Tailwind CSS, Shadcn UI components
- [x] T003 Initialize backend with Python 3.12, FastAPI, and async dependencies
- [ ] T004 [P] Configure pytest for unit testing in backend and Vitest for frontend
- [ ] T005 [P] Configure Playwright for E2E testing in frontend/
- [ ] T006 [P] Configure ruff/black for Python backend and ESLint/Prettier for TypeScript frontend
- [ ] T007 Install and configure PostgreSQL client library (asyncpg) in backend/
- [ ] T008 Install and configure InfluxDB 3.0 client library (influxdb3-python) in backend/
- [ ] T009 Install and configure asyncio-mqtt client library in backend/
- [ ] T010 Install and configure VisActor (@visactor/react-vchart) in frontend/
- [ ] T011 Install and configure Jotai state management in frontend/

## Phase 3.2: Tests First (TDD) ⚠️ MUST COMPLETE BEFORE 3.3
**CRITICAL: These tests MUST be written and MUST FAIL before ANY implementation**

### Contract Tests (API Schema Validation)
- [ ] T012 [P] Contract test GET /api/v1/organizations in backend/tests/contract/test_organizations_get.py
- [ ] T013 [P] Contract test GET /api/v1/organizations/{org_id}/sites in backend/tests/contract/test_sites_get.py
- [ ] T014 [P] Contract test GET /api/v1/organizations/{org_id}/sites/{site_id}/areas in backend/tests/contract/test_areas_get.py
- [ ] T015 [P] Contract test GET /api/v1/organizations/{org_id}/sites/{site_id}/areas/{area_id}/devices in backend/tests/contract/test_devices_get.py
- [ ] T016 [P] Contract test GET /api/v1/telemetry/current/{device_id} in backend/tests/contract/test_telemetry_current_get.py
- [ ] T017 [P] Contract test GET /api/v1/telemetry/historical/{device_id} in backend/tests/contract/test_telemetry_historical_get.py
- [ ] T018 [P] Contract test GET /api/v1/telemetry/stream (SSE) in backend/tests/contract/test_telemetry_stream_get.py
- [ ] T019 [P] Contract test POST /api/v1/auth/login in backend/tests/contract/test_auth_login_post.py

### Integration Tests (User Stories Validation)
- [ ] T020 [P] Integration test: Operations manager views real-time dashboard in backend/tests/integration/test_dashboard_realtime.py
- [ ] T021 [P] Integration test: Hierarchical filtering (org/site/area) in backend/tests/integration/test_hierarchy_filtering.py
- [ ] T022 [P] Integration test: Historical data time range selection in backend/tests/integration/test_historical_data.py
- [ ] T023 [P] Integration test: Device status monitoring and offline detection in backend/tests/integration/test_device_status.py
- [ ] T024 [P] Integration test: MQTT telemetry ingestion and processing in backend/tests/integration/test_mqtt_ingestion.py

### Database Schema Tests
- [ ] T025 [P] Database schema test: PostgreSQL tables creation in backend/tests/integration/test_postgres_schema.py
- [ ] T026 [P] Database schema test: InfluxDB measurements setup in backend/tests/integration/test_influxdb_schema.py

## Phase 3.3: Data Models (ONLY after tests are failing)

### PostgreSQL Models
- [ ] T027 [P] Organization model in backend/src/models/organization.py
- [ ] T028 [P] Site model in backend/src/models/site.py  
- [ ] T029 [P] Area model in backend/src/models/area.py
- [ ] T030 [P] Device model in backend/src/models/device.py
- [ ] T031 [P] User model in backend/src/models/user.py

### InfluxDB Models
- [ ] T032 [P] TelemetryReading model in backend/src/models/telemetry_reading.py
- [ ] T033 [P] DeviceStatusSnapshot model in backend/src/models/device_status_snapshot.py

### Database Migrations
- [ ] T034 PostgreSQL migration scripts in backend/src/migrations/
- [ ] T035 InfluxDB schema setup script in backend/src/scripts/setup_influxdb.py

## Phase 3.4: Core Services

### Database Services
- [ ] T036 [P] PostgreSQL connection service in backend/src/services/postgresql_service.py
- [ ] T037 [P] InfluxDB connection service in backend/src/services/influxdb_service.py
- [ ] T038 [P] Organization service (CRUD operations) in backend/src/services/organization_service.py
- [ ] T039 [P] Site service (CRUD operations) in backend/src/services/site_service.py
- [ ] T040 [P] Area service (CRUD operations) in backend/src/services/area_service.py
- [ ] T041 [P] Device service (CRUD operations) in backend/src/services/device_service.py
- [ ] T042 [P] User service (CRUD operations) in backend/src/services/user_service.py

### Telemetry Services  
- [ ] T043 [P] Telemetry service (InfluxDB queries) in backend/src/services/telemetry_service.py
- [ ] T044 [P] MQTT client service in backend/src/services/mqtt_service.py
- [ ] T045 Real-time streaming service (SSE) in backend/src/services/streaming_service.py

### Authentication & Authorization
- [ ] T046 [P] JWT authentication service in backend/src/services/auth_service.py
- [ ] T047 [P] Authorization middleware in backend/src/middleware/auth_middleware.py

## Phase 3.5: API Endpoints

### Hierarchy Endpoints
- [ ] T048 GET /api/v1/organizations endpoint in backend/src/api/v1/organizations.py
- [ ] T049 GET /api/v1/organizations/{org_id}/sites endpoint in backend/src/api/v1/sites.py
- [ ] T050 GET /api/v1/organizations/{org_id}/sites/{site_id}/areas endpoint in backend/src/api/v1/areas.py
- [ ] T051 GET /api/v1/organizations/{org_id}/sites/{site_id}/areas/{area_id}/devices endpoint in backend/src/api/v1/devices.py

### Telemetry Endpoints
- [ ] T052 GET /api/v1/telemetry/current/{device_id} endpoint in backend/src/api/v1/telemetry.py
- [ ] T053 GET /api/v1/telemetry/historical/{device_id} endpoint in backend/src/api/v1/telemetry.py
- [ ] T054 GET /api/v1/telemetry/stream endpoint (SSE) in backend/src/api/v1/telemetry.py

### Authentication Endpoints
- [ ] T055 POST /api/v1/auth/login endpoint in backend/src/api/v1/auth.py

## Phase 3.6: Frontend Components

### State Management (Jotai)
- [ ] T056 [P] Organization state atoms in frontend/src/state/organizationAtoms.ts
- [ ] T057 [P] Device hierarchy state atoms in frontend/src/state/hierarchyAtoms.ts
- [ ] T058 [P] Telemetry data state atoms in frontend/src/state/telemetryAtoms.ts
- [ ] T059 [P] Authentication state atoms in frontend/src/state/authAtoms.ts

### UI Components (React + Shadcn)
- [ ] T060 [P] Login form component in frontend/src/components/auth/LoginForm.tsx
- [ ] T061 [P] Organization selector component in frontend/src/components/hierarchy/OrganizationSelector.tsx
- [ ] T062 [P] Site selector component in frontend/src/components/hierarchy/SiteSelector.tsx
- [ ] T063 [P] Area selector component in frontend/src/components/hierarchy/AreaSelector.tsx
- [ ] T064 [P] Device list component in frontend/src/components/hierarchy/DeviceList.tsx

### Visualization Components (VisActor)
- [ ] T065 [P] Real-time vibration chart component in frontend/src/components/charts/VibrationChart.tsx
- [ ] T066 [P] Real-time temperature chart component in frontend/src/components/charts/TemperatureChart.tsx
- [ ] T067 [P] Real-time power chart component in frontend/src/components/charts/PowerChart.tsx
- [ ] T068 [P] Real-time electricity chart component in frontend/src/components/charts/ElectricityChart.tsx
- [ ] T069 [P] Time range picker component in frontend/src/components/charts/TimeRangePicker.tsx

### Dashboard Pages
- [ ] T070 Main dashboard page in frontend/src/pages/dashboard.tsx
- [ ] T071 Login page in frontend/src/pages/login.tsx
- [ ] T072 [P] Dashboard layout component in frontend/src/components/layout/DashboardLayout.tsx

## Phase 3.7: Real-time Integration

### MQTT Integration
- [ ] T073 MQTT message parser and validator in backend/src/services/mqtt_message_parser.py
- [ ] T074 MQTT to InfluxDB data pipeline in backend/src/services/telemetry_ingestion_service.py
- [ ] T075 Device status monitoring service in backend/src/services/device_monitoring_service.py

### Real-time Frontend
- [ ] T076 SSE client hook in frontend/src/hooks/useSSEConnection.ts
- [ ] T077 Real-time data synchronization service in frontend/src/services/RealtimeService.ts
- [ ] T078 Chart data update throttling (200ms) in frontend/src/hooks/useThrottledUpdate.ts

## Phase 3.8: CLI Tools & Libraries

### Backend CLI
- [ ] T079 [P] Organization management CLI in backend/src/cli/org_cli.py
- [ ] T080 [P] Device management CLI in backend/src/cli/device_cli.py
- [ ] T081 [P] Telemetry query CLI in backend/src/cli/telemetry_cli.py
- [ ] T082 [P] MQTT testing CLI in backend/src/cli/mqtt_cli.py

### Libraries (Constitutional Requirement)
- [ ] T083 [P] mqtt-ingestion library with CLI interface in backend/src/lib/mqtt_ingestion/
- [ ] T084 [P] telemetry-viz library with CLI interface in frontend/src/lib/telemetry-viz/
- [ ] T085 [P] device-hierarchy library with CLI interface in backend/src/lib/device_hierarchy/

## Phase 3.9: E2E Tests

### Playwright E2E Tests
- [ ] T086 [P] E2E test: Complete dashboard workflow in frontend/tests/e2e/dashboard-workflow.spec.ts
- [ ] T087 [P] E2E test: Real-time chart updates in frontend/tests/e2e/realtime-updates.spec.ts
- [ ] T088 [P] E2E test: Hierarchical filtering in frontend/tests/e2e/hierarchy-filtering.spec.ts
- [ ] T089 [P] E2E test: Time range selection in frontend/tests/e2e/time-range-selection.spec.ts
- [ ] T090 [P] E2E test: Authentication flow in frontend/tests/e2e/auth-flow.spec.ts

## Phase 3.10: Polish & Documentation

### Unit Tests
- [ ] T091 [P] Unit tests for organization service in backend/tests/unit/services/test_organization_service.py
- [ ] T092 [P] Unit tests for telemetry service in backend/tests/unit/services/test_telemetry_service.py
- [ ] T093 [P] Unit tests for MQTT service in backend/tests/unit/services/test_mqtt_service.py
- [ ] T094 [P] Unit tests for React components in frontend/tests/unit/components/
- [ ] T095 [P] Unit tests for state atoms in frontend/tests/unit/state/

### Performance & Optimization
- [ ] T096 Performance testing: <200ms chart update latency validation
- [ ] T097 Performance testing: 1000+ concurrent devices simulation
- [ ] T098 Performance testing: Database query optimization validation
- [ ] T099 [P] Code optimization: Remove duplication and improve performance

### Documentation & Validation
- [ ] T100 [P] Update libraries documentation in llms.txt format
- [ ] T101 Execute quickstart.md validation scenarios
- [ ] T102 Update CLAUDE.md with implementation details
- [ ] T103 [P] Create deployment documentation
- [ ] T104 [P] Create API documentation from OpenAPI schema

## Dependencies

### Critical Dependencies
- Tests (T012-T026) MUST be completed and FAILING before ANY implementation tasks
- Models (T027-T033) before Services (T036-T047)
- Services before API Endpoints (T048-T055)
- Backend APIs before Frontend components (T056-T072)
- Core functionality before CLI tools (T079-T085)
- Implementation before E2E tests (T086-T090)

### Specific Blockers
- T034, T035 (DB migrations) block all service tasks
- T036, T037 (DB connections) block all model and service tasks
- T044 (MQTT service) blocks T073, T074, T075
- T045 (Streaming service) blocks T054, T076, T077
- T048-T055 (API endpoints) block all frontend components
- All core tasks block polish tasks (T091-T104)

## Parallel Execution Examples

### Phase 3.2 - Contract Tests (All Parallel)
```bash
# Launch T012-T019 together:
Task: "Contract test GET /api/v1/organizations in backend/tests/contract/test_organizations_get.test.ts"
Task: "Contract test GET /api/v1/organizations/{orgId}/sites in backend/tests/contract/test_sites_get.test.ts"
Task: "Contract test GET /api/v1/organizations/{orgId}/sites/{siteId}/areas in backend/tests/contract/test_areas_get.test.ts"
Task: "Contract test GET /api/v1/organizations/{orgId}/sites/{siteId}/areas/{areaId}/devices in backend/tests/contract/test_devices_get.test.ts"
Task: "Contract test GET /api/v1/telemetry/current/{deviceId} in backend/tests/contract/test_telemetry_current_get.test.ts"
Task: "Contract test GET /api/v1/telemetry/historical/{deviceId} in backend/tests/contract/test_telemetry_historical_get.test.ts"
Task: "Contract test GET /api/v1/telemetry/stream (SSE) in backend/tests/contract/test_telemetry_stream_get.test.ts"
Task: "Contract test POST /api/v1/auth/login in backend/tests/contract/test_auth_login_post.test.ts"
```

### Phase 3.3 - Models (All Parallel)
```bash
# Launch T027-T033 together:
Task: "Organization model in backend/src/models/Organization.ts"
Task: "Site model in backend/src/models/Site.ts"
Task: "Area model in backend/src/models/Area.ts"
Task: "Device model in backend/src/models/Device.ts"
Task: "User model in backend/src/models/User.ts"
Task: "TelemetryReading model in backend/src/models/TelemetryReading.ts"
Task: "DeviceStatusSnapshot model in backend/src/models/DeviceStatusSnapshot.ts"
```

### Phase 3.6 - Frontend Components (Charts Parallel)
```bash
# Launch T065-T068 together:
Task: "Real-time vibration chart component in frontend/src/components/charts/VibrationChart.tsx"
Task: "Real-time temperature chart component in frontend/src/components/charts/TemperatureChart.tsx"
Task: "Real-time power chart component in frontend/src/components/charts/PowerChart.tsx"
Task: "Real-time electricity chart component in frontend/src/components/charts/ElectricityChart.tsx"
```

## Notes
- [P] tasks = different files, no dependencies
- Verify tests FAIL before implementing (TDD requirement)
- Commit after each task completion
- Use TypeScript strict mode throughout
- Follow constitutional requirements: libraries with CLI interfaces
- Performance target: <200ms chart updates, support 1000+ devices

## Task Generation Rules Applied

1. **From Contracts (8 endpoints)**: Generated 8 contract tests (T012-T019) + 8 implementation tasks (T048-T055)
2. **From Data Model (7 entities)**: Generated 7 model tasks (T027-T033)
3. **From User Stories (5 scenarios)**: Generated 5 integration tests (T020-T024)
4. **From Architecture**: Generated 3 library tasks per constitution (T083-T085)

## Validation Checklist
- [x] All contracts have corresponding tests (T012-T019 → T048-T055)
- [x] All entities have model tasks (7 entities → T027-T033)
- [x] All tests come before implementation (Phase 3.2 before 3.3+)
- [x] Parallel tasks truly independent (different files)
- [x] Each task specifies exact file path
- [x] No task modifies same file as another [P] task
- [x] TDD approach: RED phase enforced before GREEN phase
- [x] Constitutional compliance: 3 libraries with CLI interfaces

**Total Tasks**: 104 tasks across 10 phases
**Estimated Duration**: 3-4 weeks with parallel execution
**Critical Path**: Tests → Models → Services → APIs → Frontend → Integration