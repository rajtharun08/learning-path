# Backend Architecture: LearningPath Recommendation Engine

This document outlines the technical architecture, data flow, and logic implementation for the **LearningPath Recommendation Engine** — integrated with the YouTube Learning Platform.

---

## 1. System Overview

The backend is built using **FastAPI**, chosen for its high performance, asynchronous capabilities, and native support for Pydantic data validation. The system serves as a **Hybrid Recommendation Engine**, combining rule-based logic for Beginner and Intermediate tiers with AI-driven personalization for the Advanced tier.

This system integrates with a companion **YouTube Learning Platform** built separately. The two systems connect at exactly two points — keeping both architectures clean and independent.

### Component Structure

```
Frontend (React UI)
        │
        ▼
FastAPI Backend — LearningPath Service (Port 8006)
        │
        ├─ Assessment Engine
        │       ├─ Diagnostic Test:       5 MCQ per skill (easy / medium / hard tagged)
        │       ├─ Proficiency Detection: Beginner / Intermediate / Advanced per skill
        │       ├─ Weak Topic Tracker:    Detects gaps even when user passes overall
        │       └─ Gap Bridge:            Curated resources for weak/Beginner skills
        │
        ├─ AI Question Generator:         OpenAI GPT-4o-mini for Intermediate + Advanced questions
        │                                 Beginner questions are hardcoded (zero AI cost)
        │
        ├─ AI Roadmap Generator:          OpenAI GPT-4o-mini for Advanced tier custom roadmap
        │
        ├─ Tier Detection Logic:          Weakest link rule — overall tier = lowest skill level
        ├─ Scoring Algorithm:             Ranks courses using 40/30/20/10 weightage
        │                                 (uses real popularity score from YouTube Platform if available)
        ├─ Roadmap Generator:             Formats the final JSON sequence for the UI
        │       ├─ Beginner:              Rules-based fixed curriculum
        │       ├─ Intermediate:          Rules-based fixed curriculum, per-skill level content
        │       └─ Advanced:              AI generates fully custom personalized roadmap
        ├─ Mock Course Data:              3 levels per skill (Beginner / Intermediate / Advanced)
        │
        └─ Integration Layer
                ├─ /api/v1/roadmap/next      ← Called by YouTube Platform recommend engine
                ├─ /api/v1/roadmap/complete  ← Called by YouTube Platform progress service
                └─ /api/v1/sync-playlists    ← Fetches real playlists + popularity scores
```

### Architectural Workflow

```
User selects goal + claims skills
        │
        ▼
Diagnostic Test (5 MCQ per skill — easy / medium / hard)
        │
        ├─ Proficiency Detection per skill:
        │       Failed easy              → Beginner
        │       Passed easy+medium       → Intermediate
        │       Passed all              → Advanced
        │
        ├─ Weak topic detection (even if overall pass)
        │
        ├─ Gap resources assigned for Beginner skills + weak topics
        │
        ▼
Overall tier determined (weakest link rule)
        │
        ├─ All Advanced      → AI generates custom Advanced roadmap
        ├─ Any Intermediate  → Rules-based Intermediate roadmap
        └─ Any Beginner      → Rules-based Beginner roadmap
        │
        ▼
Each skill gets content at its own proficiency level
        │
        ▼
YouTube Platform loads correct playlist per step
(via /api/v1/roadmap/next integration endpoint)
        │
        ▼
User studies courses — progress tracked by YouTube Platform
        │
        ▼
YouTube Platform detects 90% completion
→ calls /api/v1/roadmap/complete
        │
        ▼
Next step unlocks automatically
        │
        ▼
All steps done → roadmap complete signal sent
Certificate handled by separate service
```

---

## 2. Core Components

### A. API Layer (FastAPI)
- **RESTful Endpoints:** Handles requests for skill assessment, roadmap generation, history tracking and integration.
- **Asynchronous Handling:** Uses Python's `async/await` to handle concurrent requests without blocking.
- **Auto-Documentation:** Integrated Swagger UI (`/docs`) for real-time testing and endpoint verification.

### B. Assessment Engine

The assessment layer tests claimed skills using difficulty-tagged MCQ questions and detects proficiency level per skill before roadmap generation.

**Diagnostic Test**
- 5 MCQ questions per skill tagged by difficulty and topic
- Questions 1–2: easy (fundamentals)
- Questions 3–4: medium (applied concepts)
- Question 5: hard (advanced topics)
- Beginner questions are hardcoded — zero AI cost
- Intermediate and Advanced questions are AI-generated via GPT-4o-mini (cached per skill/level)

**Proficiency Detection**
- Failed easy questions → Beginner
- Passed easy and medium, failed hard → Intermediate
- Passed all including hard → Advanced
- Weak topics tracked per skill even when user passes overall

**Gap Bridge**
- Gap resources assigned for every skill where Beginner is detected
- Targeted resources also assigned for weak topics even when Intermediate or Advanced
- User marks resources as done before starting that roadmap step

### C. Hybrid Recommendation Engine

The roadmap logic runs in three modes based on the user's overall tier:

**Beginner — Rules-Based (Fixed Curriculum)**
- No AI cost
- Fixed topic order: Python → SQL → FastAPI → Docker → Git
- Each skill gets content at its detected proficiency level
- Beginner skill → Beginner course, Intermediate skill → Intermediate course, Advanced skill → Advanced course
- Gap resources shown alongside each step

**Intermediate — Rules-Based (Fixed Curriculum, One Level Up)**
- No AI cost
- Same fixed topic order
- Each skill gets content one level higher than its detected level
- Beginner skill → Intermediate course, Intermediate skill → Advanced course
- Weak topic resources shown alongside each step

**Advanced — AI-Driven (Fully Personalized)**
- OpenAI GPT-4o-mini generates a custom 5–6 topic roadmap
- Input: role, verified skills, proficiency levels, weak topics
- No fixed curriculum — every user gets a unique Advanced roadmap
- Fallback to fixed Advanced topics if AI call fails

### D. Integration Layer

Two endpoints connect this system to the YouTube Learning Platform:

**`GET /api/v1/roadmap/next`**
- Called by YouTube Platform recommend engine before resume/next/popular logic
- Returns next playlist matching the user's skill and proficiency level
- If all steps done returns `roadmap_complete`

**`POST /api/v1/roadmap/complete`**
- Called by YouTube Platform progress service when course hits 90% completion
- Marks step done and automatically unlocks the next step

**`GET /api/v1/sync-playlists`**
- Fetches real playlists from YouTube Platform `/playlist/all`
- Fetches popularity scores from YouTube Platform `/analytics/popular`
- Stores in `real_playlists` dict — used by scoring algorithm as real rating data

### E. Data Persistence
- **Phase 1:** In-memory Python dictionaries — resets on server restart
- **Production:** PostgreSQL
  - User skill assessments, proficiency levels, weak topics
  - Learning history per user
  - Real playlist cache

---

## 3. The Scoring Algorithm

Courses are ranked within each roadmap step using a weighted formula:

| Metric | Weight | Description |
| :--- | :--- | :--- |
| **Skill Relevance** | 40% | Direct match between topic and course content |
| **Rating** | 30% | Real popularity score from YouTube Platform analytics if available, falls back to hardcoded rating |
| **Level Match** | 20% | How closely the course difficulty matches the user's proficiency for that skill |
| **Provider Authority** | 10% | Trusted providers score higher (FreeCodeCamp, Mosh, Tiangolo, AWS Training) |

```
final_score = (0.4 × skill_relevance) + (0.3 × popularity_or_rating) + (0.2 × level_match) + (0.1 × provider_authority)
```

Result returned as 0–100 score in `match_score` field.

**Popularity score** is fetched from YouTube Platform analytics and normalized to 0–1 range:
```
normalized_popularity = play_count / max_play_count_on_platform
```

---

## 4. Roadmap Step States

| State | Meaning | Frontend Behaviour |
| :--- | :--- | :--- |
| **completed** | Course finished via YouTube Platform completion event | Render as finished |
| **active** | Current learning focus | Show ranked course cards and targeted resources |
| **locked** | Prerequisite step not yet completed | Render disabled |

---

## 5. Tier System

### Proficiency Level Detection (per skill)

| Performance | Level Assigned |
| :--- | :--- |
| Failed easy questions | Beginner |
| Passed easy + medium, failed hard | Intermediate |
| Passed all including hard | Advanced |

### Overall Tier (Weakest Link Rule)

The overall tier is determined by the lowest proficiency level across all assessed skills.

| Skill Levels | Overall Tier | Engine |
| :--- | :--- | :--- |
| All Advanced | Advanced | AI-Driven |
| All Intermediate or above | Intermediate | Rules-Based |
| Any Beginner | Beginner | Rules-Based |

### Tier Progression

- Beginner tier complete → Intermediate roadmap generated (each skill moves one level up)
- Intermediate tier complete → Advanced roadmap generated (AI driven)
- No new diagnostic test needed for tier progression — stored proficiency levels are used
- Certificate and final assessment handled by a separate service

---

## 6. Integration with YouTube Learning Platform

### How the Two Systems Connect

```
YouTube Platform (Port 8000)          LearningPath (Port 8006)
─────────────────────────────         ────────────────────────
recommend engine          ──────────→ GET /api/v1/roadmap/next
                          ←────────── returns next playlist_id + skill + level

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

## 7. Scalability Roadmap

### Caching Layer (Future)
- Hash `(user_goal + skill_profile)` as a Redis key
- Cache generated roadmaps — return in under 50ms on hit
- Reduces AI API calls significantly for repeated skill combinations

### Database (Production)
- Replace in-memory dicts with PostgreSQL tables
- Persist proficiency levels, weak topics, course history across sessions

### AI Engine Improvements (Next Phase)
- Adaptive question selection — start with medium, go up or down based on performance
- Confidence score based on attempts and consistency
- Graph-based skill progression — Python → FastAPI → System Design as dependency graph

### Sentiment Analysis (Planned)
- YouTube Platform will add comment sentiment analysis
- Negative sentiment scores fed into scoring algorithm as additional rating signal
- Improves course ranking with real user feedback data

---

## 8. Security & Validation
- **Pydantic Schemas:** All incoming JSON payloads strictly validated against predefined schemas.
- **CORS Middleware:** Configured to allow frontend-backend communication.
- **Integration Security:** All calls to/from YouTube Platform wrapped in try/except — failures are silent and never break either system.
- **OpenAI Fallback:** If AI question generation fails, system falls back to hardcoded Beginner questions automatically.
- **Note:** Authentication handled by a separate service. Backend accepts `user_id` as a plain string from the frontend.