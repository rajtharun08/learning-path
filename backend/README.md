# LearningPath — Recommendation Engine

A skill-aware learning path generator that tests what users actually know, detects proficiency levels, tracks weak topics, and generates a personalized ranked roadmap. Integrated with a companion YouTube Learning Platform for real course delivery and progress tracking.

---

## What It Does

Most learning platforms just ask you what you know and trust your answer. This system does not.

When a user claims they know Python, the system tests them with 5 difficulty-tagged questions. Based on performance across easy, medium and hard questions it determines whether they are Beginner, Intermediate or Advanced in that skill — and even identifies which specific topics they are weak in even if they pass overall. The roadmap is then built to match each skill's actual level independently — no single global tier, no weakest link punishment.

---

## Tech Stack

- **FastAPI** — API framework
- **Pydantic** — data validation
- **Python 3.8+** — runtime
- **OpenAI GPT-4o-mini** — AI question generation for Intermediate and Advanced, AI roadmap topic names for Advanced tier
- **In-memory dicts** — Phase 1 data store (PostgreSQL in production)
- **httpx** — inter-service HTTP calls for YouTube Platform integration

---

## Getting Started

### Prerequisites
- Python 3.8+
- pip
- OpenAI API key

### Installation

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate       # Windows
source .venv/bin/activate    # Mac/Linux
pip install fastapi uvicorn pydantic httpx openai
```

### Environment Variables

Create a `.env` file or set this directly:

```
OPENAI_API_KEY=your_openai_key_here
```

### Running the Server

```bash
uvicorn app.main:app --reload
```

Server runs at `http://127.0.0.1:8000`

Interactive API docs at `http://127.0.0.1:8000/docs`

---

## How the Assessment Works

```
User claims skills
        ↓
Diagnostic Test — 5 MCQ per skill
Questions tagged: easy / medium / hard
        ↓
Performance analyzed per difficulty bucket
        ↓
Failed easy          → Beginner
Passed easy+medium   → Intermediate
Passed all           → Advanced
        ↓
Weak topics tracked even if overall pass
        ↓
Gap resources assigned for Beginner skills + weak topics
        ↓
Roadmap generated — each skill independently gets content at its own level
```

---

## API Reference

### Roadmap

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/generate-path` | Generate personalized learning roadmap |
| `POST` | `/api/v1/user/history` | Mark a course as completed |
| `GET` | `/api/v1/user/{user_id}/history` | Get user's completed courses |

### Assessment

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/assessment/questions?user_id=&skill=&level=` | Get 5 diagnostic MCQ questions (Beginner=hardcoded, Intermediate/Advanced=AI generated) |
| `POST` | `/api/v1/assessment/submit` | Submit diagnostic answers — returns proficiency level and weak topics |
| `POST` | `/api/v1/assessment/resource-done` | Mark a gap resource as completed |
| `GET` | `/api/v1/assessment/status/{user_id}` | Get full skill assessment summary |

### Integration

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/roadmap/next?user_id=&playlist_id=` | Returns next course in roadmap matching user's skill level |
| `POST` | `/api/v1/roadmap/complete` | Marks step done and unlocks next |
| `GET` | `/api/v1/sync-playlists` | Syncs real playlists and popularity scores from YouTube Platform |

---

## Assessment Flow

```
1. GET  /api/v1/assessment/questions?skill=Python&level=Beginner
                                    → returns 5 hardcoded questions
2. POST /api/v1/assessment/submit   → returns proficiency level + weak topics
      → if Beginner detected:
3. POST /api/v1/assessment/resource-done  → mark each gap resource done
      → repeat steps 1-3 for each skill
4. POST /api/v1/generate-path       → roadmap built from per-skill proficiency levels
```

---

## Proficiency Detection

Questions are tagged by difficulty. After submission the system analyzes performance per bucket:

| Performance | Level |
|---|---|
| Failed easy questions | Beginner |
| Passed easy + medium, failed hard | Intermediate |
| Passed all including hard | Advanced |

Weak topics are tracked separately — even if a user passes overall, specific topics they got wrong are flagged and targeted resources are assigned alongside the relevant roadmap step.

---

## Tier System

Each skill gets content at its own independently detected proficiency level. There is no global tier and no weakest link rule.

| Skill Level | Content Served | Gap Resources |
|---|---|---|
| Beginner | Beginner course | Yes — assigned automatically |
| Intermediate | Intermediate course | Only if weak topics detected |
| Advanced | Advanced course | Only if weak topics detected |

When ALL skills are Advanced, AI generates personalized topic names as display labels. Course lookup remains rules-based in all cases.

---

## Certificate Tier

Derived at roadmap completion from skill levels — not stored in the database:

| Skill Levels at Completion | Certificate |
|---|---|
| All Advanced | Advanced Certificate |
| All Intermediate or above | Intermediate Certificate |
| Any Beginner | Beginner Certificate |

When all roadmap steps are completed, the system signals `next_action: final_assessment` to the frontend. The final assessment and certificate issuance are handled by a separate service.

---

## Scoring Algorithm

Courses within each roadmap step are ranked using a weighted formula:

| Factor | Weight | Description |
|---|---|---|
| Skill Relevance | 40% | How closely the course matches the skill topic |
| Rating | 30% | Popularity score from YouTube Platform analytics (falls back to hardcoded rating) |
| Level Match | 20% | How closely the course difficulty matches the user's proficiency for that skill |
| Provider Authority | 10% | Trusted providers rank higher (FreeCodeCamp, Mosh, Tiangolo, AWS) |

```
score = ((0.4 × relevance) + (0.3 × rating) + (0.2 × level) + (0.1 × provider)) × weak_boost
```

**Weak topic boost:** Courses matching a user's weak topics score 20% higher — ensuring targeted content ranks first.

---

## Roadmap Step States

| State | Meaning |
|---|---|
| `completed` | Done via YouTube Platform completion event |
| `active` | Current learning focus — courses shown and ranked |
| `locked` | Prerequisite step not yet completed — no courses shown |

---

## Supported Skills and Roles

| Role | Skills Assessed |
|---|---|
| Backend Developer | Python, SQL, FastAPI, Docker, Git |
| Frontend Developer | HTML/CSS, JavaScript, React |
| Fullstack Developer | Python, SQL, FastAPI, Docker, Git |

Each skill has courses at Beginner, Intermediate and Advanced level. The roadmap picks the right level per skill based on diagnostic results independently.

---

## AI Usage

| Feature | Model | When |
|---|---|---|
| Intermediate diagnostic questions | GPT-4o-mini | When user requests Intermediate level questions |
| Advanced diagnostic questions | GPT-4o-mini | When user requests Advanced level questions |
| Advanced roadmap topic names | GPT-4o-mini | When ALL skills are Advanced — generates personalized display labels |
| Beginner questions | None — hardcoded | Always free, no AI cost |

AI generated questions are cached per skill/level so they are only generated once. AI roadmap topic names are display labels only — course lookup is always rules-based.

---

## Integration with YouTube Platform

This system connects to a companion YouTube Learning Platform at two points:

- When the YouTube Platform needs to recommend a course, it asks this system what comes next in the user's roadmap — including which skill and which level
- When a user finishes 90% of a course, the YouTube Platform notifies this system to unlock the next roadmap step

The two systems run independently. If either is unreachable the other falls back to its own logic automatically.

---

## Production Database Plan

When moving to production with PostgreSQL, the system will use these 8 tables:

| Table | Purpose |
|---|---|
| USERS | User identity and goal tracking |
| USER_SKILL_ASSESSMENTS | Per-skill proficiency level, score, weak topics |
| QUESTIONS | All MCQ questions with options as inline columns |
| SKILL_ATTEMPTS | Diagnostic attempts — both Beginner and AI-generated |
| SKILL_ANSWERS | All answers with topic and difficulty tags |
| GAP_RESOURCES | Bridge study material per skill |
| USER_GAP_RESOURCES | Which resources each user completed |
| USER_COURSE_HISTORY | Course completion and roadmap progression |

Note: Overall tier and certificate tier are not stored — both are derived dynamically at roadmap generation and completion time respectively.

---

## Important Notes

- **State is in-memory** — all data resets on server restart. Use a new `user_id` each test session.
- **user_id is a plain string** — no auth implemented. Frontend passes it directly.
- **Skill names are case-sensitive** — use `Python`, `SQL`, `FastAPI`, `Docker`, `Git` exactly.
- **OpenAI key required** — set `OPENAI_API_KEY` in environment for Intermediate and Advanced questions.
- **Beginner questions are free** — no API key needed for Beginner level assessment.
- **Fallback safe** — if YouTube Platform or OpenAI is unreachable, system continues working with fallbacks.
- **Certificate and final assessment** — handled by a separate service. This system only signals `next_action: final_assessment` with `certificate_tier` when roadmap is complete.