# Frontend Integration Guide — LearningPath Recommendation Engine

This document contains everything you need to build the frontend for the LearningPath system. Read this fully before starting.

---

## Setup

**Backend Base URL:** `http://localhost:8000`

**Swagger Docs (test all endpoints here first):** `http://localhost:8000/docs`

**No API keys needed on your side.** All AI runs on the backend server.

**CORS is fully open** — you can call from any localhost port without issues.

---

## User ID

There is no login or authentication. 

Just keep it simple. Change it to a different string each time you restart testing since the backend resets on restart anyway.  just use any plain string like testuser1, testuser2
Example:
```js
const user_id = "anything_you_want"
```

---

## Skill Names — Case Sensitive

Always use exact casing:

| Role | Skills |
|---|---|
| Backend Developer | `Python`, `SQL`, `FastAPI`, `Docker`, `Git` |
| Frontend Developer | `HTML/CSS`, `JavaScript`, `React` |
| Fullstack Developer | `Python`, `SQL`, `FastAPI`, `Docker`, `Git` |

---

## Pages to Build

You need to build **3 pages**:

1. Onboarding Page
2. Diagnostic Assessment Page
3. Roadmap Page

Pages 4 and 5 (Final Assessment and Certificate) are handled by a separate service. Your job ends when the roadmap is complete — just show the certificate tier and a button.

---

## Page 1 — Onboarding

### What to show
- Dropdown to select role
- Skill pills to claim known skills
- Submit button

### Available roles
- `Backend Developer`
- `Frontend Developer`
- `Fullstack Developer`

### Available skills per role
Show only skills relevant to the selected role (see table above).

### On submit call

```
POST /api/v1/generate-path
```

Request body:
```json
{
  "user_id": "user_abc123",
  "role": "Backend Developer",
  "current_skills": ["Python", "SQL"]
}
```

Response:
```json
{
  "user_id": "user_abc123",
  "role": "Backend Developer",
  "overall_tier": "Mixed",
  "engine": "Rules-Based - Per Skill",
  "competency_profile": {},
  "roadmap": [
    {
      "step": 1,
      "topic": "Python — Beginner",
      "skill": "Python",
      "skill_level": "Beginner",
      "status": "active",
      "is_reviewable": false,
      "suggested_courses": [
        {
          "course_id": 1,
          "title": "Python Basics",
          "provider": "FreeCodeCamp",
          "resource_url": "https://www.youtube.com/watch?v=rfscVS0vtbw",
          "match_score": 95.0,
          "is_finished": false
        }
      ],
      "targeted_resources": [],
      "weak_topics": []
    },
    {
      "step": 2,
      "topic": "SQL — Beginner",
      "skill": "SQL",
      "skill_level": "Beginner",
      "status": "locked",
      "is_reviewable": false,
      "suggested_courses": [],
      "targeted_resources": [],
      "weak_topics": []
    }
  ],
  "is_path_finished": false
}
```

### After getting this response
Store the roadmap in state. Navigate to the Diagnostic Assessment page if `current_skills` is not empty. If user claimed no skills skip directly to the Roadmap page.

---

## Page 2 — Diagnostic Assessment

### What to show
Run through each claimed skill one at a time. For each skill show a test screen with 5 MCQ questions.

### Step 2A — Get Questions

```
GET /api/v1/assessment/questions?user_id=user_abc123&skill=Python&level=Beginner
```

> **For testing without OpenAI key always use `level=Beginner`.** Beginner questions are hardcoded and free.

Response:
```json
{
  "user_id": "user_abc123",
  "skill": "Python",
  "level": "Beginner",
  "questions": [
    {
      "id": "py_1",
      "difficulty": "easy",
      "topic": "data_types",
      "question": "Which of these is a mutable data type?",
      "options": {
        "a": "tuple",
        "b": "str",
        "c": "list",
        "d": "int"
      }
    },
    {
      "id": "py_2",
      "difficulty": "easy",
      "topic": "exceptions",
      "question": "How do you handle exceptions in Python?",
      "options": {
        "a": "try/catch",
        "b": "try/except",
        "c": "catch/finally",
        "d": "error/handle"
      }
    },
    {
      "id": "py_3",
      "difficulty": "medium",
      "topic": "generators",
      "question": "What keyword is used to define a generator in Python?",
      "options": {
        "a": "return",
        "b": "yield",
        "c": "async",
        "d": "pass"
      }
    },
    {
      "id": "py_4",
      "difficulty": "medium",
      "topic": "concurrency",
      "question": "What does GIL stand for?",
      "options": {
        "a": "Global Interpreter Lock",
        "b": "General Input Layer",
        "c": "Global Index List",
        "d": "None"
      }
    },
    {
      "id": "py_5",
      "difficulty": "hard",
      "topic": "decorators",
      "question": "What does a decorator do?",
      "options": {
        "a": "Imports a module",
        "b": "Wraps a function to extend its behaviour",
        "c": "Defines a class",
        "d": "Creates a variable"
      }
    }
  ]
}
```

Show all 5 questions as radio buttons. User selects one option per question.

### Step 2B — Submit Answers

```
POST /api/v1/assessment/submit
```

Request body:
```json
{
  "user_id": "user_abc123",
  "skill": "Python",
  "level": "Beginner",
  "answers": [
    {"question_id": "py_1", "selected_option": "c"},
    {"question_id": "py_2", "selected_option": "b"},
    {"question_id": "py_3", "selected_option": "b"},
    {"question_id": "py_4", "selected_option": "a"},
    {"question_id": "py_5", "selected_option": "b"}
  ]
}
```

Response:
```json
{
  "user_id": "user_abc123",
  "skill": "Python",
  "score_pct": 80,
  "proficiency_level": "Intermediate",
  "weak_topics": ["decorators"],
  "easy_pct": 100,
  "medium_pct": 50,
  "hard_pct": 0,
  "badge": "Intermediate",
  "gap_resources": [],
  "message": "'Python' assessed as Intermediate. Weak areas: decorators.",
  "breakdown": [
    {
      "question_id": "py_1",
      "your_answer": "c",
      "correct_answer": "c",
      "is_correct": true
    }
  ]
}
```

### What to display after submit
- Show proficiency badge — `proficiency_level` field
- Show score percentage — `score_pct`
- Show performance per bucket — `easy_pct`, `medium_pct`, `hard_pct`
- Show weak topics — `weak_topics`
- Show message — `message`
- If `gap_resources` is not empty show each resource with a **Mark as Done** button

### Step 2C — Mark Gap Resources Done (only if gap_resources returned)

For each resource the user has studied call:

```
POST /api/v1/assessment/resource-done
```

Request body:
```json
{
  "user_id": "user_abc123",
  "skill": "Python",
  "resource_id": 501
}
```

Response:
```json
{
  "user_id": "user_abc123",
  "skill": "Python",
  "resource_id": 501,
  "resources_completed": [501],
  "all_done": false,
  "message": "Keep going — complete all resources before starting the roadmap step."
}
```

When `all_done` is `true` show a success message and allow moving to next skill.

### Step 2D — Repeat for all claimed skills

Run Steps 2A, 2B, 2C for every skill in `current_skills`. Show a progress indicator like "Skill 1 of 3".

### Step 2E — Generate personalized roadmap

After ALL skills are assessed call generate-path again:

```
POST /api/v1/generate-path
```

Same request body as before. This time the response will have real proficiency levels per skill instead of all Beginner. Navigate to the Roadmap page with this response.

---

## Page 3 — Roadmap

### What to show

Display each step from the `roadmap` array. Each step has a `status` — use this to decide how to render it.

### Step status rules

| Status | What to show |
|---|---|
| `active` | Show step highlighted. Show course cards ranked by `match_score`. Show Watch button. Show targeted resources if any. |
| `completed` | Show step with a tick/checkmark. No course cards needed. |
| `locked` | Show step as greyed out / disabled. No course cards. |

### Step fields

```json
{
  "step": 1,
  "topic": "Python — Intermediate",
  "skill": "Python",
  "skill_level": "Intermediate",
  "status": "active",
  "suggested_courses": [...],
  "targeted_resources": [...],
  "weak_topics": ["decorators"]
}
```

- `topic` — display name for the step
- `skill_level` — show as a badge on the step (Beginner / Intermediate / Advanced)
- `weak_topics` — show as small warning badges if not empty
- `targeted_resources` — show alongside the step as extra study material

### Course card fields

```json
{
  "course_id": 2,
  "title": "Python Intermediate",
  "provider": "Corey Schafer",
  "resource_url": "https://www.youtube.com/watch?v=HGOBQPFzWKo",
  "match_score": 95.2,
  "is_finished": false
}
```

- Show `title` and `provider`
- Show `match_score` as a relevance indicator
- **Watch button** — opens `resource_url` in a new tab
- If `is_finished` is true show as completed

### Marking a course as done

When user clicks Mark as Done on a course call:

```
POST /api/v1/user/history
```

Request body:
```json
{
  "user_id": "user_abc123",
  "course_id": 2
}
```

Then immediately call generate-path again to refresh the roadmap. The completed step will now show `status: completed` and the next step will unlock.
"Note: To refresh the roadmap, you must send the exact same JSON request body (user_id, role, current_skills) that you sent on the Onboarding page. Keep these values saved in your frontend state."

### Targeted resources

If a step has `targeted_resources` show them as a separate section — these are extra study materials for the user's weak topics in that skill.

```json
{
  "id": 501,
  "title": "Python Full Course",
  "provider": "FreeCodeCamp",
  "url": "https://www.youtube.com/watch?v=rfscVS0vtbw"
}
```

Show a link or button that opens the `url`.

### Competency profile

Show a small profile card somewhere on the roadmap page using `competency_profile` from the generate-path response:

```json
{
  "Python": {
    "proficiency_level": "Intermediate",
    "score_pct": 80,
    "weak_topics": ["decorators"]
  },
  "SQL": {
    "proficiency_level": "Beginner",
    "score_pct": 40,
    "weak_topics": ["joins", "grouping"]
  }
}
```

---

## Page 3 — Roadmap Complete State

When `is_path_finished` is `true` in the generate-path response show a completion screen:

```json
{
  "is_path_finished": true,
  "next_action": "final_assessment",
  "certificate_tier": "Intermediate",
  "message": "All courses complete. Take final assessment to earn your Intermediate certificate."
}
```

Show:
- `message` — display this as the completion message
- `certificate_tier` — show what certificate the user will earn
- A **Take Final Assessment** button — this goes to the final assessment service (separate team, separate URL, ask the final assessment team for the URL)

---

## Useful Endpoint — Skill Status Page

At any point you can show the user their full assessment summary:

```
GET /api/v1/assessment/status/{user_id}
```

Example: `GET /api/v1/assessment/status/user_abc123`

Response:
```json
{
  "user_id": "user_abc123",
  "overall_tier": "Beginner",
  "skills_assessed": [
    {
      "skill": "Python",
      "diagnostic_done": true,
      "score_pct": 80,
      "proficiency_level": "Intermediate",
      "weak_topics": ["decorators"],
      "gap": false
    },
    {
      "skill": "SQL",
      "diagnostic_done": true,
      "score_pct": 40,
      "proficiency_level": "Beginner",
      "weak_topics": ["joins"],
      "gap": true
    }
  ],
  "all_assessed": true
}
```

Good for a profile or progress dashboard page.

---

## Complete API Summary

| Method | Endpoint | When to call |
|---|---|---|
| `POST` | `/api/v1/generate-path` | On onboarding submit and after every assessment |
| `GET` | `/api/v1/assessment/questions?user_id=&skill=&level=Beginner` | Before each diagnostic test |
| `POST` | `/api/v1/assessment/submit` | After user answers all 5 questions |
| `POST` | `/api/v1/assessment/resource-done` | When user marks a gap resource as done |
| `GET` | `/api/v1/assessment/status/{user_id}` | For profile or progress page |
| `POST` | `/api/v1/user/history` | When user marks a course as done |
| `GET` | `/api/v1/user/{user_id}/history` | To show completed courses list |

---

## Complete Page Flow

```
Page 1 — Onboarding
        ↓
User selects role + claims skills
        ↓
Call POST /api/v1/generate-path
        ↓
If skills claimed → go to Page 2
If no skills claimed → go to Page 3 directly
        ↓

Page 2 — Diagnostic Assessment
        ↓
For each claimed skill:
  GET /api/v1/assessment/questions (level=Beginner for testing)
  Show 5 MCQ questions
  POST /api/v1/assessment/submit
  Show result — proficiency + weak topics
  If gap_resources → show resources → POST /api/v1/assessment/resource-done per resource
        ↓
All skills done
        ↓
Call POST /api/v1/generate-path again
        ↓
Go to Page 3
        ↓

Page 3 — Roadmap
        ↓
Show roadmap steps
Active step → show courses → Watch button opens YouTube URL
User marks course done → POST /api/v1/user/history
        ↓
Call POST /api/v1/generate-path to refresh
        ↓
Repeat until is_path_finished = true
        ↓
Show certificate_tier + Take Final Assessment button
        ↓

Page 4 — Final Assessment (separate service — not your responsibility)
```

---

## Important Notes

- **State resets on server restart** — use a new `user_id` each time during development
- **Skill names are case sensitive** — `Python` not `python`
- **Always use `level=Beginner`** for testing without OpenAI key
- **Call generate-path twice** — once on onboarding, once after all assessments done
- **Call generate-path again** after every course marked as done to refresh step statuses
- **Watch button** just opens `resource_url` in a new tab — it is a YouTube link
- **Final Assessment** is a separate service — ask that team for their URL and how to integrate
- **No login needed** — just generate a random user_id and use it throughout
- **"UI Rule:** Once an assessment is submitted successfully, disable the submit 
button or remove the test from the screen so the user cannot submit the same skill twice (the backend will return a 400 error if they do)."
- try to test using Backend Developer as i gave mock course for that only