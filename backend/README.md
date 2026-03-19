# LearningPath — Recommendation Engine

A skill-aware learning path generator that tests what users actually know, detects gaps, and generates a personalized ranked roadmap. Integrated with a companion YouTube Learning Platform for real course delivery and progress tracking.

---

## What It Does

Most learning platforms just ask you what you know and trust your answer. This system does not.

When a user claims they know Python, the system tests them with 5 targeted questions. If they pass, Python is skipped in the roadmap. If they fail, a gap is detected, study resources are assigned, and a harder verification test must be passed before moving forward. The final roadmap is built only from what the user actually knows — not what they think they know.

---

## Tech Stack

- **FastAPI** — API framework
- **Pydantic** — data validation
- **Python 3.8+** — runtime
- **In-memory dicts** — POC data store (PostgreSQL in production)
- **httpx** — inter-service HTTP calls for YouTube Platform integration

---

## Getting Started

### Prerequisites
- Python 3.8+
- pip

### Installation

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate       # Windows
source .venv/bin/activate    # Mac/Linux
pip install fastapi uvicorn pydantic httpx
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
        ↓
Score >= 60% → Verified → Skip in roadmap
Score  < 60% → Gap detected → Study resources assigned
        ↓
Mark all resources done → Delta Test unlocks
        ↓
Delta Test — 5 harder MCQ
        ↓
Pass → Verified    Fail → Retry
        ↓
Roadmap generated from verified skills only
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
| `GET` | `/api/v1/assessment/questions?user_id=&skill=` | Get 5 diagnostic MCQ questions |
| `POST` | `/api/v1/assessment/submit` | Submit diagnostic answers |
| `POST` | `/api/v1/assessment/resource-done` | Mark a gap resource as completed |
| `GET` | `/api/v1/assessment/delta/questions?user_id=&skill=` | Get 5 harder delta test questions |
| `POST` | `/api/v1/assessment/delta/submit` | Submit delta test answers |
| `GET` | `/api/v1/assessment/status/{user_id}` | Get full skill assessment summary |

### Integration

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/roadmap/next?user_id=&playlist_id=` | Returns next course in roadmap |
| `POST` | `/api/v1/roadmap/complete` | Marks step done and unlocks next |
| `GET` | `/api/v1/sync-playlists` | Syncs real playlists and popularity scores from YouTube Platform |

---

## Assessment Flow

```
1. GET  /api/v1/assessment/questions      → show MCQ screen
2. POST /api/v1/assessment/submit         → get verified or gap badge
      → if gap:
3. POST /api/v1/assessment/resource-done  → mark each resource done
4. GET  /api/v1/assessment/delta/questions → show harder MCQ screen
5. POST /api/v1/assessment/delta/submit   → skill verified
      → repeat for each skill
6. POST /api/v1/generate-path            → roadmap built from verified skills
```

---

## Scoring Algorithm

Courses within each roadmap step are ranked using a weighted formula:

| Factor | Weight | Description |
|---|---|---|
| Skill Relevance | 40% | How closely the course matches the skill topic |
| Rating | 30% | Popularity score from YouTube Platform analytics (falls back to hardcoded rating) |
| Level Match | 20% | How closely the course difficulty matches the user's tier |
| Provider Authority | 10% | Trusted providers rank higher (FreeCodeCamp, Mosh, Tiangolo, AWS) |

```
score = (0.4 x relevance) + (0.3 x rating) + (0.2 x level) + (0.1 x provider)
```

---

## Roadmap Step States

| State | Meaning |
|---|---|
| `completed` | Done via history or YouTube Platform completion |
| `review` | Claimed via skill pill but not test-verified |
| `active` | Current learning focus |
| `locked` | Prerequisite not yet met |

---

## Supported Skills and Roles

| Role | Skills Tested |
|---|---|
| Backend Developer | Python, SQL, FastAPI, Docker |
| Frontend Developer | HTML/CSS, JavaScript, React |
| Fullstack Developer | Python, SQL, FastAPI, Docker |

---

## Integration with YouTube Platform

This system connects to a companion YouTube Learning Platform at two points:

- When the YouTube Platform needs to recommend a course, it asks this system what comes next in the user's roadmap
- When a user finishes 90% of a course, the YouTube Platform notifies this system to unlock the next roadmap step

The two systems run independently. If either is unreachable the other falls back to its own logic automatically.

---

## Production Database Plan

The current POC uses in-memory Python dictionaries. When moving to production with PostgreSQL, the system will use these 8 tables:

| Table | Purpose |
|---|---|
| USERS | User identity and goal tracking |
| USER_SKILL_ASSESSMENTS | Per-skill verified/gap/badge state |
| QUESTIONS | All MCQ questions with options as inline columns |
| SKILL_ATTEMPTS | Diagnostic and delta attempts combined |
| SKILL_ANSWERS | All answers for both test types |
| GAP_RESOURCES | Bridge study material per skill |
| USER_GAP_RESOURCES | Which resources each user completed |
| USER_COURSE_HISTORY | Course completion and roadmap progression |

---

## Important Notes

- **State is in-memory** — all data resets on server restart. Use a new `user_id` each test session.
- **user_id is a plain string** — no auth implemented. Frontend passes it directly.
- **Skill names are case-sensitive** — use `Python`, `SQL`, `FastAPI`, `Docker` exactly.
- **Pass threshold** — 60% for both diagnostic and delta test.
- **Fallback safe** — if YouTube Platform is unreachable, this system continues working independently.