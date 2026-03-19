# Backend Architecture: LearningPath Recommendation Engine

This document outlines the technical architecture, data flow, and logic implementation for the **LearningPath Backend POC** — now integrated with the YouTube Learning Platform.

---

## 1. System Overview

The backend is built using **FastAPI**, chosen for its high performance, asynchronous capabilities, and native support for Pydantic data validation. The system serves as a "Hybrid Recommendation Engine," balancing local rule-based logic with a skill assessment layer and external AI inference.

This system is designed to integrate with a companion **YouTube Learning Platform** (built separately by a teammate). The two systems connect at exactly two points — keeping both architectures clean and independent.

### Component Structure

```
Frontend (React UI)
        │
        ▼
FastAPI Backend — LearningPath Service (Port 8006)
        │
        ├─ Assessment Engine
        │       ├─ Diagnostic Test:    5 MCQ questions per skill → gap detection
        │       ├─ Gap Bridge:         Curated resources for weak skills
        │       └─ Delta Test:         5 harder questions → skill verification
        │
        ├─ Tier Detection Logic:       Classifies user as Beginner / Intermediate / Advanced
        ├─ Scoring Algorithm:          Ranks courses using 40/30/20/10 weightage
        │                              (uses real popularity score from YouTube Platform if available)
        ├─ Roadmap Generator:          Formats the final JSON sequence for the UI
        ├─ Mock Course Data:           Local repository for zero-cost path generation
        │
        └─ Integration Layer (NEW)
                ├─ /api/v1/roadmap/next      ← Called by YouTube Platform recommend engine
                ├─ /api/v1/roadmap/complete  ← Called by YouTube Platform progress service
                └─ /api/v1/sync-playlists    ← Fetches real playlists + popularity scores
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
                                   YouTube Platform loads real playlist for active step
                                   (via /api/v1/roadmap/next integration endpoint)
                                                        │
                                                        ▼
                                              User studies active courses
                                                        │
                                                        ▼
                                   YouTube Platform detects 90% completion
                                   → calls /api/v1/roadmap/complete
                                                        │
                                                        ▼
                                              Next step unlocks automatically
```

---

## 2. Core Components

### A. API Layer (FastAPI)
- **RESTful Endpoints:** Handles requests for skill assessment, roadmap generation, history tracking, and integration.
- **Asynchronous Handling:** Uses Python's `async/await` to handle concurrent requests without blocking.
- **Auto-Documentation:** Integrated Swagger UI (`/docs`) for real-time testing and endpoint verification.

### B. Assessment Engine

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

### D. Integration Layer (NEW)

Two new endpoints connect this system to the YouTube Learning Platform:

**`GET /api/v1/roadmap/next`**
- Called by the YouTube Platform recommend engine before its own resume/next/popular logic
- Returns the next playlist the user should study based on their roadmap and verified skills
- If user has completed all steps returns `roadmap_complete`

**`POST /api/v1/roadmap/complete`**
- Called by the YouTube Platform progress service when a course hits 90% completion
- Marks the roadmap step as done and automatically unlocks the next step
- Updates `user_histories` in-memory store

**`GET /api/v1/sync-playlists`**
- Fetches real playlists from YouTube Platform's `/playlist/all` endpoint
- Fetches popularity scores from YouTube Platform's `/analytics/popular` endpoint
- Stores them in `real_playlists` dict for use in scoring algorithm
- Replaces hardcoded mock rating with real platform popularity data

### E. Data Persistence
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
| **Rating** | 30% | Uses real popularity score from YouTube Platform analytics if available, falls back to hardcoded rating |
| **Level Match** | 20% | How closely the course difficulty matches the user's tier |
| **Provider Authority** | 10% | Trusted providers score higher (FreeCodeCamp, Mosh, Tiangolo, AWS) |

```
final_score = (0.4 × skill_relevance) + (0.3 × popularity_or_rating) + (0.2 × level_match) + (0.1 × provider_authority)
```

Result is returned as a 0–100 score in the API response (`match_score` field).

**Popularity score** is fetched from the YouTube Platform's analytics service and normalized to 0–1 range:
```
normalized_popularity = play_count / max_play_count_on_platform
```

---

## 4. Roadmap Step States

| State | Meaning | Frontend Behaviour |
| :--- | :--- | :--- |
| **completed** | Verified via history or YouTube Platform completion event | Render as finished |
| **review** | Claimed via skill pill, not history-verified | Show "Review Resources" CTA |
| **active** | Current learning focus | Show ranked course cards |
| **locked** | Prerequisite not met | Render disabled |

---

## 5. Integration with YouTube Learning Platform

### How the Two Systems Connect

```
YouTube Platform (Port 8000)          LearningPath (Port 8006)
─────────────────────────────         ────────────────────────
recommend engine          ──────────→ GET /api/v1/roadmap/next
                          ←────────── returns next playlist_id

progress service          ──────────→ POST /api/v1/roadmap/complete
                                       marks step done, unlocks next

LearningPath              ──────────→ GET /playlist/all (YouTube Platform)
sync-playlists            ──────────→ GET /analytics/popular (YouTube Platform)
                          ←────────── real playlists + popularity scores
```

### What YouTube Platform Needs to Add

1. `skill_tags` field on playlist model — e.g. `["python", "fastapi"]`
2. `level` field on playlist model — `Beginner / Intermediate / Advanced`
3. `provider` field on playlist model — YouTube channel name
4. Call `/api/v1/roadmap/next` at top of `build_recommendation()` before existing logic
5. Call `/api/v1/roadmap/complete` in `progress_service.py` when course hits 90%

### Fallback Behaviour
If this service is unreachable, the YouTube Platform automatically falls back to its own resume → next → popular logic. Nothing breaks on either side.

---

## 6. Scalability Roadmap

### Caching Layer (Future)
- Hash `(user_goal + verified_skills)` as a Redis key
- Cache generated roadmaps — return in <50ms on hit
- Reduces LLM API calls by ~50% for repeated skill combinations

### Database (Production)
- Replace `user_histories`, `user_assessments`, and `real_playlists` dicts with PostgreSQL tables
- Persist diagnostic scores, delta results, verified badges, and course history across sessions

### AI Engine (Next Phase)
- Replace the AI-Inference stub with a real LLM call
- Feed verified skill data (not self-reported pills) into the prompt
- Generate non-linear roadmaps for complex/niche skill combinations

### Sentiment Analysis (Planned)
- YouTube Platform will add comment sentiment analysis
- Negative sentiment scores fed into this system's scoring algorithm as an additional rating signal
- Improves course ranking with real user feedback data

---

## 7. Security & Validation
- **Pydantic Schemas:** All incoming JSON payloads are strictly validated against predefined schemas.
- **CORS Middleware:** Configured to allow communication between the frontend and backend.
- **Integration Security:** All calls to/from YouTube Platform are wrapped in try/except — failures are silent and never break either system.
- **Note:** Authentication and user identity are handled by a separate service. The backend accepts `user_id` as a plain string passed from the frontend.