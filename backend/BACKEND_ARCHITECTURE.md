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
        ├─ AI Roadmap Generator:          OpenAI GPT-4o-mini for Advanced tier — generates
        │                                 personalized topic names when ALL skills are Advanced
        │
        ├─ Per-Skill Roadmap Logic:       Each skill gets content at its own detected level
        │                                 No global tier — no weakest link punishment
        ├─ Scoring Algorithm:             Ranks courses using 40/30/20/10 weightage
        │                                 Weak topic boost: courses matching weak areas score 20% higher
        │                                 Uses real popularity score from YouTube Platform if available
        ├─ Roadmap Generator:             Formats the final JSON sequence for the UI
        │       ├─ Rules-Based:           Fixed curriculum — each skill at its own level
        │       └─ AI-Driven:             All skills Advanced → AI generates personalized topic names
        │                                 Course lookup still rules-based (skill + level)
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
Per-skill roadmap generated — no global tier
        │
        ├─ Each skill independently gets content at its own detected level
        │       Python Advanced  → Python Advanced course
        │       SQL Beginner     → SQL Beginner course + gap resources
        │       FastAPI Intermed → FastAPI Intermediate course
        │
        ├─ All skills Advanced → AI generates personalized topic names as display labels
        │                        Course lookup still uses skill + level (rules-based)
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
All steps done → certificate_tier derived from skill levels
→ next_action: final_assessment signaled to frontend
→ Certificate and final assessment handled by separate service
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

The roadmap runs as a **single unified loop** — one pass through the curriculum, each skill independently selecting content at its own detected level.

**Rules-Based (all tiers except all-Advanced)**
- No AI cost for course lookup
- Fixed topic order: Python → SQL → FastAPI → Docker → Git
- Each skill gets content at its own detected proficiency level
  - Beginner skill → Beginner course + gap resources
  - Intermediate skill → Intermediate course
  - Advanced skill → Advanced course
- Weak topic resources shown alongside each step
- Handles any mix of levels in one pass — no weakest link punishment

**AI-Driven (only when ALL skills are Advanced)**
- OpenAI GPT-4o-mini generates personalized topic display names (e.g. "Advanced Async Python")
- Input: role, verified skills, proficiency levels, weak topics
- Topic names are display labels only — course lookup still uses skill + level
- Fallback to fixed Advanced topic names if AI call fails

### D. Certificate Tier Derivation

Certificate tier is computed at roadmap completion time from skill levels — not stored in the database:

```
All skills Advanced              → certificate_tier = "Advanced"
All skills Intermediate or above → certificate_tier = "Intermediate"
Any skill Beginner               → certificate_tier = "Beginner"
```

Signaled to frontend via `next_action: final_assessment` when `is_path_finished: true`.

### E. Integration Layer

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

### F. Data Persistence
- **Phase 1:** In-memory Python dictionaries — resets on server restart
- **Production:** PostgreSQL
  - User skill assessments, proficiency levels, weak topics
  - Learning history per user
  - Real playlist cache

---

## 3. The Scoring Algorithm

Courses are ranked within each roadmap step using a weighted formula with a weak topic boost:

| Metric | Weight | Description |
| :--- | :--- | :--- |
| **Skill Relevance** | 40% | Direct match between topic and course content |
| **Rating** | 30% | Real popularity score from YouTube Platform analytics if available, falls back to hardcoded rating |
| **Level Match** | 20% | How closely the course difficulty matches the user's proficiency for that skill |
| **Provider Authority** | 10% | Trusted providers score higher (FreeCodeCamp, Mosh, Tiangolo, AWS Training) |

```
final_score = ((0.4 × skill_relevance) + (0.3 × popularity_or_rating) + (0.2 × level_match) + (0.1 × provider_authority)) × weak_boost
```

**Weak Topic Boost:** If the course topic matches any of the user's weak topics, the final score is multiplied by 1.2 — ensuring courses that address weak areas rank higher.

**Popularity score** is fetched from YouTube Platform analytics and normalized to 0–1 range:
```
normalized_popularity = play_count / max_play_count_on_platform
```

Result returned as 0–100 score in `match_score` field.

---

## 4. Roadmap Step States

| State | Meaning | Frontend Behaviour |
| :--- | :--- | :--- |
| **completed** | Course finished via YouTube Platform completion event | Render as finished |
| **active** | Current learning focus | Show ranked course cards and targeted resources |
| **locked** | Prerequisite step not yet completed | Render disabled — no courses shown |

---

## 5. Tier System

### Proficiency Level Detection (per skill)

| Performance | Level Assigned |
| :--- | :--- |
| Failed easy questions | Beginner |
| Passed easy + medium, failed hard | Intermediate |
| Passed all including hard | Advanced |

### Per-Skill Roadmap Logic

There is no global tier. Each skill independently selects content at its own detected level.

| Skill Level | Content Served | Gap Resources |
| :--- | :--- | :--- |
| Beginner | Beginner course | Yes — assigned automatically |
| Intermediate | Intermediate course | Only if weak topics detected |
| Advanced | Advanced course | Only if weak topics detected |

### AI Roadmap Trigger

AI roadmap generation is triggered only when ALL skills are Advanced. In all other cases the roadmap is rules-based.

| Condition | Engine | Topic Labels |
| :--- | :--- | :--- |
| All skills Advanced | AI-Driven | AI generates personalized topic names |
| Any skill not Advanced | Rules-Based | Skill — Level format (e.g. "Python — Intermediate") |

### Certificate Tier

Derived at roadmap completion from skill levels in USER_SKILL_ASSESSMENTS:

| Skill Levels at Completion | Certificate Issued |
| :--- | :--- |
| All Advanced | Advanced Certificate |
| All Intermediate or above | Intermediate Certificate |
| Any Beginner | Beginner Certificate |

### Tier Progression

- Roadmap complete → `next_action: final_assessment` signaled to frontend
- Final assessment handled by separate service → promotes skill levels in USER_SKILL_ASSESSMENTS
- `generate-path` called again → new roadmap generated at promoted levels
- No new diagnostic test needed for tier progression — stored proficiency levels are used

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
- **OpenAI Fallback:** If AI question generation fails, system falls back to hardcoded Beginner questions automatically. Errors logged for visibility.
- **Note:** Authentication handled by a separate service. Backend accepts `user_id` as a plain string from the frontend.