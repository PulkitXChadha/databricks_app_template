---
description: "Task list template for feature implementation"
---

# Tasks: [FEATURE NAME]

**Input**: Design documents from `/specs/[###-feature-name]/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**TDD REQUIREMENT (Principle XII)**: All production code MUST follow Test Driven Development.
Tests are MANDATORY and MUST be written BEFORE implementation following red-green-refactor cycles.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions
- **Single project**: `src/`, `tests/` at repository root
- **Web app**: `backend/src/`, `frontend/src/`
- **Mobile**: `api/src/`, `ios/src/` or `android/src/`
- Paths shown below assume single project - adjust based on plan.md structure

<!-- 
  ============================================================================
  IMPORTANT: The tasks below are SAMPLE TASKS for illustration purposes only.
  
  The /speckit.tasks command MUST replace these with actual tasks based on:
  - User stories from spec.md (with their priorities P1, P2, P3...)
  - Feature requirements from plan.md
  - Entities from data-model.md
  - Endpoints from contracts/
  
  Tasks MUST be organized by user story so each story can be:
  - Implemented independently
  - Tested independently
  - Delivered as an MVP increment
  
  DO NOT keep these sample tasks in the generated tasks.md file.
  ============================================================================
-->

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T001 Create project structure per implementation plan
- [ ] T002 Initialize [language] project with [framework] dependencies
- [ ] T003 [P] Configure linting and formatting tools

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

Examples of foundational tasks (adjust based on your project):

- [ ] T004 Setup database schema and migrations framework
- [ ] T005 [P] Implement authentication/authorization framework
- [ ] T006 [P] Setup API routing and middleware structure
- [ ] T007 Create base models/entities that all stories depend on
- [ ] T008 Configure error handling and logging infrastructure
- [ ] T009 Setup environment configuration management

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - [Title] (Priority: P1) 🎯 MVP

**Goal**: [Brief description of what this story delivers]

**Independent Test**: [How to verify this story works on its own]

### 🔴 RED Phase: Write Failing Tests for User Story 1 (TDD - MANDATORY)

**TDD Requirement**: Write these tests FIRST. All tests MUST FAIL initially before any implementation.

- [ ] T010 [P] [US1] Write contract test for [endpoint] in tests/contract/test_[name].py (MUST FAIL - RED)
- [ ] T011 [P] [US1] Write integration test for [user journey] in tests/integration/test_[name].py (MUST FAIL - RED)
- [ ] T012 [P] [US1] Write unit tests for [business logic] in tests/unit/test_[name].py (MUST FAIL - RED)

**Verification**: Run test suite - ALL tests for US1 should be RED (failing)

### 🟢 GREEN Phase: Implementation for User Story 1

**TDD Requirement**: Write minimal code to make tests pass. Focus on making tests GREEN, not on perfection.

- [ ] T013 [P] [US1] Create [Entity1] model in src/models/[entity1].py (makes unit tests pass)
- [ ] T014 [P] [US1] Create [Entity2] model in src/models/[entity2].py (makes unit tests pass)
- [ ] T015 [US1] Implement [Service] in src/services/[service].py (makes integration tests pass)
- [ ] T016 [US1] Implement [endpoint/feature] in src/[location]/[file].py (makes contract tests pass)
- [ ] T017 [US1] Add validation and error handling (all tests passing)
- [ ] T018 [US1] Add logging for user story 1 operations

**Verification**: Run test suite - ALL tests for US1 should be GREEN (passing)

### 🔄 REFACTOR Phase: Improve Code Quality for User Story 1

**TDD Requirement**: Refactor for quality while keeping ALL tests GREEN. Run tests after each refactoring step.

- [ ] T019 [US1] Refactor code for clarity and maintainability (tests stay GREEN)
- [ ] T020 [US1] Remove duplication and improve structure (tests stay GREEN)
- [ ] T021 [US1] Optimize performance if needed (tests stay GREEN)

**Checkpoint**: User Story 1 complete - fully functional, tested, and refactored. ALL tests GREEN.

---

## Phase 4: User Story 2 - [Title] (Priority: P2)

**Goal**: [Brief description of what this story delivers]

**Independent Test**: [How to verify this story works on its own]

### 🔴 RED Phase: Write Failing Tests for User Story 2 (TDD - MANDATORY)

- [ ] T022 [P] [US2] Write contract test for [endpoint] in tests/contract/test_[name].py (MUST FAIL - RED)
- [ ] T023 [P] [US2] Write integration test for [user journey] in tests/integration/test_[name].py (MUST FAIL - RED)
- [ ] T024 [P] [US2] Write unit tests for [business logic] in tests/unit/test_[name].py (MUST FAIL - RED)

**Verification**: Run test suite - ALL tests for US2 should be RED (failing)

### 🟢 GREEN Phase: Implementation for User Story 2

- [ ] T025 [P] [US2] Create [Entity] model in src/models/[entity].py (makes unit tests pass)
- [ ] T026 [US2] Implement [Service] in src/services/[service].py (makes integration tests pass)
- [ ] T027 [US2] Implement [endpoint/feature] in src/[location]/[file].py (makes contract tests pass)
- [ ] T028 [US2] Integrate with User Story 1 components if needed (tests stay GREEN)

**Verification**: Run test suite - ALL tests for US1 AND US2 should be GREEN (passing)

### 🔄 REFACTOR Phase: Improve Code Quality for User Story 2

- [ ] T029 [US2] Refactor code for clarity and maintainability (tests stay GREEN)
- [ ] T030 [US2] Remove duplication and improve structure (tests stay GREEN)

**Checkpoint**: User Stories 1 AND 2 complete - both independently functional and tested. ALL tests GREEN.

---

## Phase 5: User Story 3 - [Title] (Priority: P3)

**Goal**: [Brief description of what this story delivers]

**Independent Test**: [How to verify this story works on its own]

### 🔴 RED Phase: Write Failing Tests for User Story 3 (TDD - MANDATORY)

- [ ] T031 [P] [US3] Write contract test for [endpoint] in tests/contract/test_[name].py (MUST FAIL - RED)
- [ ] T032 [P] [US3] Write integration test for [user journey] in tests/integration/test_[name].py (MUST FAIL - RED)
- [ ] T033 [P] [US3] Write unit tests for [business logic] in tests/unit/test_[name].py (MUST FAIL - RED)

**Verification**: Run test suite - ALL tests for US3 should be RED (failing)

### 🟢 GREEN Phase: Implementation for User Story 3

- [ ] T034 [P] [US3] Create [Entity] model in src/models/[entity].py (makes unit tests pass)
- [ ] T035 [US3] Implement [Service] in src/services/[service].py (makes integration tests pass)
- [ ] T036 [US3] Implement [endpoint/feature] in src/[location]/[file].py (makes contract tests pass)

**Verification**: Run test suite - ALL tests for US1, US2, AND US3 should be GREEN (passing)

### 🔄 REFACTOR Phase: Improve Code Quality for User Story 3

- [ ] T037 [US3] Refactor code for clarity and maintainability (tests stay GREEN)
- [ ] T038 [US3] Remove duplication and improve structure (tests stay GREEN)

**Checkpoint**: All user stories complete - independently functional and tested. ALL tests GREEN.

---

[Add more user story phases as needed, following the same pattern]

---

## Phase N: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] TXXX [P] Documentation updates in docs/
- [ ] TXXX Code cleanup and refactoring
- [ ] TXXX Performance optimization across all stories
- [ ] TXXX [P] Additional unit tests (if requested) in tests/unit/
- [ ] TXXX Security hardening
- [ ] TXXX Run quickstart.md validation

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - May integrate with US1 but should be independently testable
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - May integrate with US1/US2 but should be independently testable

### Within Each User Story (TDD Phases)

**TDD Workflow (MANDATORY - Principle XII):**
1. **RED Phase**: Write all tests first - ALL MUST FAIL initially
2. **GREEN Phase**: Write minimal implementation to make tests pass
3. **REFACTOR Phase**: Improve code quality while keeping tests GREEN

**Implementation Order Within GREEN Phase:**
- Models before services (makes unit tests pass)
- Services before endpoints (makes integration tests pass)
- Endpoints complete contracts (makes contract tests pass)
- Core implementation before integration
- All tests GREEN before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- Once Foundational phase completes, all user stories can start in parallel (if team capacity allows)
- All tests for a user story marked [P] can run in parallel
- Models within a story marked [P] can run in parallel
- Different user stories can be worked on in parallel by different team members

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together (if tests requested):
Task: "Contract test for [endpoint] in tests/contract/test_[name].py"
Task: "Integration test for [user journey] in tests/integration/test_[name].py"

# Launch all models for User Story 1 together:
Task: "Create [Entity1] model in src/models/[entity1].py"
Task: "Create [Entity2] model in src/models/[entity2].py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test User Story 1 independently
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Test independently → Deploy/Demo
4. Add User Story 3 → Test independently → Deploy/Demo
5. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1
   - Developer B: User Story 2
   - Developer C: User Story 3
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- **TDD MANDATORY (Principle XII)**: Always follow RED-GREEN-REFACTOR cycle
  - RED: Write test first, verify it FAILS
  - GREEN: Write minimal code to pass test
  - REFACTOR: Improve code while keeping tests GREEN
- Commit after each TDD phase (RED, GREEN, REFACTOR) or logical group
- Stop at any checkpoint to validate story independently
- Run full test suite before moving to next user story
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence


