# LearningPath — Recommendation Engine

A skill-aware learning path generator that tests what users actually know, detects proficiency levels, tracks weak topics, and generates a personalized ranked roadmap. Integrated with a companion YouTube Learning Platform for real course delivery and progress tracking.

---

## What It Does

Most learning platforms just ask you what you know and trust your answer. This system does not.

When a user claims they know Python, the system tests them with 5 difficulty-tagged questions. Based on performance across easy, medium and hard questions it determines whether they are Beginner, Intermediate or Advanced in that skill — and even identifies which specific topics they are weak in even if they pass overall. The roadmap is then built to match each skill's actual level, not a single overall score.

---

## Tech Stack

- **FastAPI** — API framework
- **Pydantic** — data validation
- **Python 3.8+** — runtime
- **OpenAI GPT-4o-mini** — AI question generation for Intermediate and Advanced, AI roadmap for Advanced tier
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
uvicorn main:app --reload
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
Roadmap generated — each skill gets content at its own level
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
| `GET` | `/api/v1/assessment/status/{user_id}` | Get full skill assessment summary and overall tier |

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
4. POST /api/v1/generate-path       → roadmap built from proficiency levels
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

Overall tier is determined by the weakest skill (weakest link rule):

| Skill Levels | Overall Tier | Roadmap Type |
|---|---|---|
| All Advanced | Advanced | AI generates custom roadmap |
| All Intermediate or above | Intermediate | Rules-based, one level up per skill |
| Any Beginner | Beginner | Rules-based, content at each skill's level |

Each skill gets content at its own detected proficiency level — not a single level for all skills.

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
score = (0.4 x relevance) + (0.3 x rating) + (0.2 x level) + (0.1 x provider)
```

---

## Roadmap Step States

| State | Meaning |
|---|---|
| `completed` | Done via YouTube Platform completion event |
| `active` | Current learning focus |
| `locked` | Prerequisite step not yet completed |

---

## Supported Skills and Roles

| Role | Skills Assessed |
|---|---|
| Backend Developer | Python, SQL, FastAPI, Docker, Git |
| Frontend Developer | HTML/CSS, JavaScript, React |
| Fullstack Developer | Python, SQL, FastAPI, Docker, Git |

Each skill has courses at Beginner, Intermediate and Advanced level. The roadmap picks the right level per skill based on diagnostic results.

---

## AI Usage

| Feature | Model | When |
|---|---|---|
| Intermediate diagnostic questions | GPT-4o-mini | When user requests Intermediate level questions |
| Advanced diagnostic questions | GPT-4o-mini | When user requests Advanced level questions |
| Advanced roadmap generation | GPT-4o-mini | When all skills are Advanced |
| Beginner questions | None — hardcoded | Always free, no AI cost |

AI generated questions are cached per skill/level so they are only generated once.

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

---

## Important Notes

- **State is in-memory** — all data resets on server restart. Use a new `user_id` each test session.
- **user_id is a plain string** — no auth implemented. Frontend passes it directly.
- **Skill names are case-sensitive** — use `Python`, `SQL`, `FastAPI`, `Docker`, `Git` exactly.
- **OpenAI key required** — set `OPENAI_API_KEY` in environment for Intermediate and Advanced questions.
- **Beginner questions are free** — no API key needed for Beginner level assessment.
- **Fallback safe** — if YouTube Platform or OpenAI is unreachable, system continues working with fallbacks.
- **Certificate and final assessment** — handled by a separate service. This system only signals roadmap complete.