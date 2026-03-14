# Backend Architecture: LearningPath Recommendation Engine

This document outlines the technical architecture, data flow, and logic implementation for the **LearningPath Backend POC**.

---

## 1. System Overview

The backend is built using **FastAPI**, chosen for its high performance, asynchronous capabilities, and native support for Pydantic data validation. The system serves as a "Hybrid Recommendation Engine," balancing local rule-based logic with a skill assessment layer and external AI inference.

### Component Structure

```
Frontend (React UI)
        │
        ▼
FastAPI Backend (API Gateway)
        │
        ├─ Assessment Engine
        │       ├─ Diagnostic Test:    5 MCQ questions per skill → gap detection
        │       ├─ Gap Bridge:         Curated resources for weak skills
        │       └─ Delta Test:         5 harder questions → skill verification
        │
        ├─ Tier Detection Logic:       Classifies user as Beginner / Intermediate / Advanced
        ├─ Scoring Algorithm:          Ranks courses using 40/30/20/10 weightage
        ├─ Roadmap Generator:          Formats the final JSON sequence for the UI
        └─ Mock Course Data:           Local repository for zero-cost path generation
```

### Architectural Workflow

```
User claims skills (pills)
        │
        ▼
Diagnostic Test (5 MCQ per skill)
        │
        ├─ Score ≥ 60% → Verified ──────────────────────┐
        │                                               │
        └─ Score < 60% → Gap Detected                   │
                │                                       │
                ▼                                       │
        Study Bridge Resources                          │
                │                                       │
                ▼                                       │
        Delta Test (5 MCQ, harder)                      │
                │                                       │
                ├─ Pass → Verified ─────────────────────┤
                └─ Fail → Retry                         │
                                                        ▼
                                              Roadmap Generated
                                              (verified skills = skipped)
                                                        │
                                                        ▼
                                              User studies active courses
                                                        │
                                                        ▼
                                              Mark course done → history updated
                                                        │
                                                        ▼
                                              Next step unlocks
```

---

## 2. Core Components

### A. API Layer (FastAPI)
- **RESTful Endpoints:** Handles requests for skill assessment, roadmap generation, and history tracking.
- **Asynchronous Handling:** Uses Python's `async/await` to handle concurrent requests without blocking.
- **Auto-Documentation:** Integrated Swagger UI (`/docs`) for real-time testing and endpoint verification.

### B. Assessment Engine (New)

The assessment layer validates self-reported skills before the roadmap is generated. It prevents the system from skipping topics the user doesn't actually know.

**Diagnostic Test**
- 5 targeted MCQ questions per skill
- Pass threshold: 60%
- Pass → skill marked **verified**, skipped in roadmap
- Fail → skill marked as **gap**, bridge resources assigned

**Gap Bridge**
- Curated learning resources per gap skill
- User must mark all resources as done before delta test unlocks

**Delta Test**
- 5 harder questions per gap skill
- Same 60% pass threshold
- Pass → skill flips from unverified → verified
- Fail → user reviews resources and retries

### C. Hybrid Recommendation Engine

The roadmap logic is divided into two tiers:

1. **Rules-Based Tier (Beginner)**
   - Pure local logic — no API cost
   - Maps verified skills to predefined curriculum topics
   - Scoring algorithm ranks courses within each topic

2. **AI-Inference Tier (Advanced/Expert) — Stub**
   - Placeholder for LLM integration (GPT-4o mini / Gemini Flash)
   - Activates when user is auto-promoted to Intermediate or Advanced tier
   - Swap the stub with a real API call when ready

### D. Data Persistence
- **POC:** In-memory Python dictionaries — resets on server restart
- **Production:** PostgreSQL
  - User skill states, diagnostic scores, delta results
  - Learning history per user
  - Verified skill badges

---

## 3. The Scoring Algorithm

Courses are ranked within each roadmap step using a weighted formula:

| Metric | Weight | Description |
| :--- | :--- | :--- |
| **Skill Relevance** | 40% | Direct match between topic and course content |
| **Rating** | 30% | Course provider rating and user feedback |
| **Level Match** | 20% | How closely the course difficulty matches the user's tier |
| **Provider Authority** | 10% | Trusted providers score higher (FreeCodeCamp, Mosh, Tiangolo, AWS) |

```
final_score = (0.4 × skill_relevance) + (0.3 × rating) + (0.2 × level_match) + (0.1 × provider_authority)
```

Result is returned as a 0–100 score in the API response (`match_score` field).

---

## 4. Roadmap Step States

| State | Meaning | Frontend Behaviour |
| :--- | :--- | :--- |
| **completed** | Verified via history | Render as finished |
| **review** | Claimed via skill pill, not history-verified | Show "Review Resources" CTA |
| **active** | Current learning focus | Show ranked course cards |
| **locked** | Prerequisite not met | Render disabled |

---

## 5. Scalability Roadmap

### Caching Layer (Future)
- Hash `(user_goal + verified_skills)` as a Redis key
- Cache generated roadmaps — return in <50ms on hit
- Reduces LLM API calls by ~50% for repeated skill combinations

### Database (Production)
- Replace `user_histories` and `user_assessments` dicts with PostgreSQL tables
- Persist diagnostic scores, delta results, verified badges, and course history across sessions

### AI Engine (Next Phase)
- Replace the AI-Inference stub with a real LLM call
- Feed verified skill data (not self-reported pills) into the prompt
- Generate non-linear roadmaps for complex/niche skill combinations

---

## 6. Security & Validation
- **Pydantic Schemas:** All incoming JSON payloads are strictly validated against predefined schemas.
- **CORS Middleware:** Configured to allow communication between the frontend and backend.
- **Note:** Authentication and user identity are handled by a separate service. The backend accepts `user_id` as a plain string passed from the frontend.