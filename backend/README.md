# Technical Overview

The backend is built with FastAPI and implements four core logic layers:

**Skill Assessment Engine:** Validates self-reported skills through a diagnostic test before generating a learning path. Detects gaps, assigns bridge resources, and verifies skills via a delta test.

**Tier Detection:** Automatically classifies users into Beginner, Intermediate, or Advanced tracks based on verified skills.

**Adaptive Redundancy Filtering:** Dynamically handles mastered topics by distinguishing between "Completed" (verified via history) and "Review" (skipped via self-reported skills).

**Weighted Scoring:** Ranks course recommendations using a multi-factor algorithm (Skill Relevance: 40%, Rating: 30%, Level Match: 20%, Provider Authority: 10%).

**State Management:** Manages the progression of roadmap milestones through four distinct states: Completed, Review, Active, and Locked.

---

# Getting Started

## Prerequisites
- Python 3.8+
- pip

## Installation

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install fastapi uvicorn pydantic
```

## Running the Server

```bash
uvicorn main:app --reload
```

The server will be available at http://127.0.0.1:8000

---

# API Documentation and Integration

## Interactive Documentation

Once the server is running, access the full API contract and testing suite at:
http://127.0.0.1:8000/docs

---

# Core Endpoints

## — ROADMAP (Original) —

### 1. Generate Learning Path
**Endpoint:** POST /api/v1/generate-path

**Payload:** `{ user_id, role, current_skills }`

**Logic:** Returns a dynamic roadmap. Steps matched via current_skills are marked as review, history-verified steps as completed. Tier is auto-detected from skills.

### 2. Update User History
**Endpoint:** POST /api/v1/user/history

**Payload:** `{ user_id, course_id }`

**Logic:** Persists course completion. Next roadmap call automatically reflects the update and unlocks the next step.

### 3. Get User History
**Endpoint:** GET /api/v1/user/{user_id}/history

**Logic:** Returns all courses the user has completed. Use this to render the completed courses section.

---

## — ASSESSMENT (New) —

> Call these endpoints in order before generating the roadmap.

### 4. Get Diagnostic Questions
**Endpoint:** GET /api/v1/assessment/questions?user_id=&skill=

**Logic:** Returns 5 MCQ questions for the given skill. Supported skills: `Python`, `SQL`, `FastAPI`, `Docker`.

### 5. Submit Diagnostic Answers
**Endpoint:** POST /api/v1/assessment/submit

**Payload:** `{ user_id, skill, answers: [{ question_id, selected_option }] }`

**Logic:** Grades the answers. Score ≥ 60% → skill verified. Score < 60% → gap detected, returns bridge resources to study.

### 6. Mark Gap Resource as Done
**Endpoint:** POST /api/v1/assessment/resource-done

**Payload:** `{ user_id, skill, resource_id }`

**Logic:** Tracks which gap resources the user has completed. Once all resources for a skill are marked done, the delta test unlocks.

### 7. Get Delta Test Questions
**Endpoint:** GET /api/v1/assessment/delta/questions?user_id=&skill=

**Logic:** Returns 5 harder MCQ questions. Only available after all gap resources are completed.

### 8. Submit Delta Test
**Endpoint:** POST /api/v1/assessment/delta/submit

**Payload:** `{ user_id, skill, answers: [{ question_id, selected_option }] }`

**Logic:** Grades delta answers. Score ≥ 60% → skill flips from unverified to verified. Verified skills are treated as completed steps in the roadmap.

### 9. Get Assessment Status
**Endpoint:** GET /api/v1/assessment/status/{user_id}

**Logic:** Returns all skills with their current badge (verified / gap / not_assessed). Use this for the pre-roadmap summary screen.

---

# Assessment Flow (in order)

```
1. GET  /api/v1/assessment/questions        → render MCQ screen
2. POST /api/v1/assessment/submit           → get badge back (verified or gap)
     → if gap:
3. POST /api/v1/assessment/resource-done    → mark each resource done
4. GET  /api/v1/assessment/delta/questions  → render delta MCQ screen (same component)
5. POST /api/v1/assessment/delta/submit     → skill verified
     → repeat for each skill
6. POST /api/v1/generate-path              → roadmap now reflects verified skills
```

---

# UI State Mapping Reference

The frontend should use the `status` field in roadmap steps for conditional rendering:

**completed:** Topic mastered via history. Render with a finished state.

**review:** Topic skipped via skill pills. Render as completed but provide a "Review Resources" option. Use `is_reviewable: true` to trigger this UI state.

**active:** Current focus. Render course cards and details.

**locked:** Prerequisite not met. Render as disabled or hidden.

The `is_path_finished` boolean can be used to trigger the final completion state in the UI.

---

# Important Notes

- **State is in-memory** — all data resets when the server restarts. Use a new `user_id` each test session to get a clean state.
- **user_id is a plain string** — no auth is implemented. The frontend passes it directly (login is handled separately).
- **Skill names are case-sensitive** — use `Python`, `SQL`, `FastAPI`, `Docker` exactly.
- **Pass threshold** — 60% for both diagnostic and delta test.