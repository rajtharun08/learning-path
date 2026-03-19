import os
import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Learning Path AI - POC")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# His YouTube platform service URL
YT_SERVICE_URL = "http://youtube-platform:8000"

# DATA MODELS

class UserProfile(BaseModel):
    user_id: str
    role: str                  # Goal Dropdown (e.g., "Backend Developer")
    current_skills: List[str]  # Skill Pills

class HistoryUpdate(BaseModel):
    user_id: str
    course_id: int

# Assessment models
class DiagnosticAnswer(BaseModel):
    question_id: str
    selected_option: str       # "a", "b", "c", or "d"

class DiagnosticSubmission(BaseModel):
    user_id: str
    skill: str                 # e.g. "Python"
    answers: List[DiagnosticAnswer]

class DeltaTestSubmission(BaseModel):
    user_id: str
    skill: str
    answers: List[DiagnosticAnswer]

class ResourceCompletion(BaseModel):
    user_id: str
    resource_id: int
    skill: str

# Integration models
class RoadmapComplete(BaseModel):
    user_id:     str
    playlist_id: str

# MOCK DB

mock_courses = [
    # Beginner Topics
    {"id": 1,  "title": "Python Syntax & Logic",         "topic": "Python Basics",       "level": "Beginner",     "rating": 0.95, "provider": "FreeCodeCamp",      "skill_tags": ["python"],          "resource_url": "https://www.youtube.com/watch?v=rfscVS0vtbw"},
    {"id": 14, "title": "Git & GitHub Masterclass",      "topic": "Version Control",     "level": "Beginner",     "rating": 0.94, "provider": "Traversy",          "skill_tags": ["git"],             "resource_url": "https://www.youtube.com/watch?v=RGOj5yH7evk"},
    {"id": 6,  "title": "HTML/CSS Crash Course",         "topic": "HTML/CSS Essentials", "level": "Beginner",     "rating": 0.94, "provider": "Traversy",          "skill_tags": ["html", "css"],     "resource_url": "https://www.youtube.com/watch?v=gvOivz9skfA"},

    # Intermediate Topics
    {"id": 3,  "title": "SQL for Backend Devs",          "topic": "Database Integration","level": "Intermediate", "rating": 0.92, "provider": "Mosh",              "skill_tags": ["sql"],             "resource_url": "https://www.youtube.com/watch?v=HXV3zeQKqGY"},
    {"id": 15, "title": "Build a REST API with FastAPI", "topic": "API Development",     "level": "Intermediate", "rating": 0.89, "provider": "Tiangolo",          "skill_tags": ["fastapi", "api"],  "resource_url": "https://www.youtube.com/watch?v=0sOvCWFmrtA"},
    {"id": 8,  "title": "Docker for Developers",         "topic": "System Design",       "level": "Intermediate", "rating": 0.93, "provider": "TechWorld with Nana","skill_tags": ["docker"],          "resource_url": "https://www.youtube.com/watch?v=3c-iKn767wE"},
    {"id": 16, "title": "Celery & Redis for Tasks",      "topic": "Asynchronous Tasks",  "level": "Intermediate", "rating": 0.87, "provider": "CoreyMS",           "skill_tags": ["celery", "redis"], "resource_url": "https://www.youtube.com/watch?v=68QWw0Ot4Ng"},

    # Advanced Topics
    {"id": 5,  "title": "Microservices Architecture",    "topic": "System Design",       "level": "Advanced",     "rating": 0.96, "provider": "YouTube",           "skill_tags": ["microservices"],   "resource_url": "https://www.youtube.com/watch?v=123456"},
    {"id": 9,  "title": "AWS Cloud Architecture",        "topic": "Cloud Architecture",  "level": "Advanced",     "rating": 0.97, "provider": "AWS Training",      "skill_tags": ["aws", "cloud"],    "resource_url": "https://www.youtube.com/watch?v=ia7Mte8q08I"},
    {"id": 17, "title": "JWT Authentication Patterns",   "topic": "Security Patterns",   "level": "Advanced",     "rating": 0.93, "provider": "Auth0",             "skill_tags": ["security", "jwt"], "resource_url": "https://www.youtube.com/watch?v=7Q17ubqLfaM"},
    {"id": 10, "title": "Redis Caching & Performance",   "topic": "Performance Tuning",  "level": "Advanced",     "rating": 0.94, "provider": "Redis University",   "skill_tags": ["redis", "cache"],  "resource_url": "https://www.youtube.com/watch?v=OqZz90v-m5M"},
]

# In-memory stores
user_histories   = {}   # { user_id: [course_id, ...] }
user_assessments = {}   # { user_id: { skill: { verified, score, gap, resources_done, delta_passed } } }

# Stores real playlists fetched from YT system
# { playlist_id: { title, skill_tags, level, provider, popularity_score } }
real_playlists = {}

# Diagnostic question bank — 5 questions per skill
diagnostic_questions = {
    "Python": [
        {"id": "py_1", "question": "What keyword is used to define a generator in Python?",         "options": {"a": "return", "b": "yield", "c": "async", "d": "pass"},    "answer": "b"},
        {"id": "py_2", "question": "Which of these is a mutable data type?",                        "options": {"a": "tuple", "b": "str", "c": "list", "d": "int"},         "answer": "c"},
        {"id": "py_3", "question": "What does GIL stand for?",                                      "options": {"a": "Global Interpreter Lock", "b": "General Input Layer", "c": "Global Index List", "d": "None"}, "answer": "a"},
        {"id": "py_4", "question": "How do you handle exceptions in Python?",                       "options": {"a": "try/catch", "b": "try/except", "c": "catch/finally", "d": "error/handle"}, "answer": "b"},
        {"id": "py_5", "question": "What does a decorator do?",                                     "options": {"a": "Imports a module", "b": "Wraps a function to extend its behaviour", "c": "Defines a class", "d": "Creates a variable"}, "answer": "b"},
    ],
    "SQL": [
        {"id": "sql_1", "question": "Which clause filters rows AFTER grouping?",                    "options": {"a": "WHERE", "b": "FILTER", "c": "HAVING", "d": "ORDER BY"}, "answer": "c"},
        {"id": "sql_2", "question": "What does INNER JOIN return?",                                 "options": {"a": "All rows from both tables", "b": "Only matched rows", "c": "Only left table rows", "d": "Null rows"}, "answer": "b"},
        {"id": "sql_3", "question": "Which is a DDL command?",                                      "options": {"a": "SELECT", "b": "INSERT", "c": "CREATE", "d": "UPDATE"}, "answer": "c"},
        {"id": "sql_4", "question": "What does DISTINCT do?",                                       "options": {"a": "Sorts results", "b": "Removes duplicate rows", "c": "Groups rows", "d": "Counts rows"}, "answer": "b"},
        {"id": "sql_5", "question": "Which keyword is used for partial text search?",               "options": {"a": "MATCH", "b": "CONTAINS", "c": "LIKE", "d": "SIMILAR"}, "answer": "c"},
    ],
    "FastAPI": [
        {"id": "fa_1", "question": "Which library does FastAPI use for data validation?",           "options": {"a": "Marshmallow", "b": "Cerberus", "c": "Pydantic", "d": "Voluptuous"}, "answer": "c"},
        {"id": "fa_2", "question": "What does async/await enable in FastAPI?",                      "options": {"a": "Multi-threading", "b": "Concurrency without blocking", "c": "Parallel processing", "d": "Caching"}, "answer": "b"},
        {"id": "fa_3", "question": "What is Depends() used for?",                                   "options": {"a": "Database connection", "b": "Dependency injection", "c": "Middleware setup", "d": "Route grouping"}, "answer": "b"},
        {"id": "fa_4", "question": "Which decorator handles GET requests?",                         "options": {"a": "@app.get()", "b": "@app.fetch()", "c": "@app.read()", "d": "@app.request()"}, "answer": "a"},
        {"id": "fa_5", "question": "What does response_model do?",                                  "options": {"a": "Validates input", "b": "Filters and validates output", "c": "Caches responses", "d": "Logs the response"}, "answer": "b"},
    ],
    "Docker": [
        {"id": "dk_1", "question": "What is the purpose of a Dockerfile?",                         "options": {"a": "Configure a database", "b": "Define container build instructions", "c": "Set up networking", "d": "Install Python"}, "answer": "b"},
        {"id": "dk_2", "question": "Which command runs a Docker container?",                        "options": {"a": "docker start", "b": "docker launch", "c": "docker run", "d": "docker exec"}, "answer": "c"},
        {"id": "dk_3", "question": "What does docker-compose do?",                                  "options": {"a": "Builds images", "b": "Manages multi-container apps", "c": "Deploys to cloud", "d": "Tests containers"}, "answer": "b"},
        {"id": "dk_4", "question": "What is a Docker volume used for?",                             "options": {"a": "CPU allocation", "b": "Persistent data storage", "c": "Network routing", "d": "Image compression"}, "answer": "b"},
        {"id": "dk_5", "question": "How do you pass environment variables to a container?",         "options": {"a": "-v flag", "b": "-e flag", "c": "--network flag", "d": "ARGS in Dockerfile"}, "answer": "b"},
    ],
}

# Delta test question bank — 5 different questions per skill (harder)
delta_questions = {
    "Python": [
        {"id": "dpy_1", "question": "What does *args do in a function signature?",                 "options": {"a": "Keyword arguments", "b": "Variable positional arguments", "c": "Pointer args", "d": "Required args"}, "answer": "b"},
        {"id": "dpy_2", "question": "Which is the correct list comprehension syntax?",             "options": {"a": "[x for x in range(10)]", "b": "{x in range(10)}", "c": "(x for x, range(10))", "d": "list(x, range(10))"}, "answer": "a"},
        {"id": "dpy_3", "question": "What does __init__ do in a Python class?",                    "options": {"a": "Destroys the object", "b": "Initializes a new instance", "c": "Imports the module", "d": "Defines a static method"}, "answer": "b"},
        {"id": "dpy_4", "question": "What type does json.loads() return?",                         "options": {"a": "str", "b": "bytes", "c": "dict or list", "d": "JSON object"}, "answer": "c"},
        {"id": "dpy_5", "question": "Which is NOT a valid Python data type?",                      "options": {"a": "set", "b": "frozenset", "c": "hashmap", "d": "tuple"}, "answer": "c"},
    ],
    "SQL": [
        {"id": "dsql_1", "question": "Which JOIN returns all records from the left table?",        "options": {"a": "INNER JOIN", "b": "RIGHT JOIN", "c": "LEFT JOIN", "d": "FULL JOIN"}, "answer": "c"},
        {"id": "dsql_2", "question": "What does COUNT(*) do?",                                     "options": {"a": "Counts non-null values", "b": "Counts all rows including nulls", "c": "Sums values", "d": "Counts unique rows"}, "answer": "b"},
        {"id": "dsql_3", "question": "Which is used to prevent SQL injection?",                    "options": {"a": "String formatting", "b": "Parameterized queries", "c": "UPPER()", "d": "Escaping with quotes"}, "answer": "b"},
        {"id": "dsql_4", "question": "What is a PRIMARY KEY?",                                     "options": {"a": "A non-unique index", "b": "A unique identifier for a row", "c": "A foreign reference", "d": "An auto-increment column only"}, "answer": "b"},
        {"id": "dsql_5", "question": "What does the COALESCE function do?",                        "options": {"a": "Joins two strings", "b": "Returns the first non-null value", "c": "Counts rows", "d": "Converts data types"}, "answer": "b"},
    ],
    "FastAPI": [
        {"id": "dfa_1", "question": "How do you declare a path parameter in FastAPI?",             "options": {"a": "@app.get('/:id')", "b": "@app.get('/{id}')", "c": "@app.get('/<id>')", "d": "@app.get('/[id]')"}, "answer": "b"},
        {"id": "dfa_2", "question": "What HTTP status code means 'created'?",                      "options": {"a": "200", "b": "204", "c": "201", "d": "202"}, "answer": "c"},
        {"id": "dfa_3", "question": "What does HTTPException do?",                                  "options": {"a": "Logs errors", "b": "Raises HTTP errors with status codes", "c": "Sends email alerts", "d": "Retries requests"}, "answer": "b"},
        {"id": "dfa_4", "question": "Which header is used for Bearer token auth?",                 "options": {"a": "X-Auth-Token", "b": "Authorization", "c": "Token", "d": "API-Key"}, "answer": "b"},
        {"id": "dfa_5", "question": "What does @app.middleware('http') do?",                       "options": {"a": "Defines a route", "b": "Runs logic before/after every request", "c": "Sets CORS", "d": "Validates input"}, "answer": "b"},
    ],
    "Docker": [
        {"id": "ddk_1", "question": "What does EXPOSE in a Dockerfile do?",                        "options": {"a": "Opens firewall ports", "b": "Documents the port the container listens on", "c": "Maps host ports", "d": "Starts the server"}, "answer": "b"},
        {"id": "ddk_2", "question": "Which command lists running containers?",                      "options": {"a": "docker list", "b": "docker images", "c": "docker ps", "d": "docker show"}, "answer": "c"},
        {"id": "ddk_3", "question": "What is the difference between CMD and ENTRYPOINT?",          "options": {"a": "No difference", "b": "ENTRYPOINT is always executed; CMD provides defaults", "c": "CMD is always executed", "d": "ENTRYPOINT is for scripts only"}, "answer": "b"},
        {"id": "ddk_4", "question": "What does docker build -t myapp . do?",                       "options": {"a": "Runs the app", "b": "Pulls an image", "c": "Builds an image tagged myapp", "d": "Tags an existing image"}, "answer": "c"},
        {"id": "ddk_5", "question": "What is the purpose of .dockerignore?",                       "options": {"a": "Stops Docker from running", "b": "Excludes files from the build context", "c": "Hides environment variables", "d": "Ignores errors during build"}, "answer": "b"},
    ],
}

# Gap bridge resources (learning material for failed skills)
gap_resources = {
    "Python": [
        {"id": 501, "title": "Python Full Course",       "provider": "FreeCodeCamp",      "url": "https://www.youtube.com/watch?v=rfscVS0vtbw"},
        {"id": 502, "title": "Python OOP Tutorial",      "provider": "Corey Schafer",     "url": "https://www.youtube.com/watch?v=ZDa-Z5JzLYM"},
    ],
    "SQL": [
        {"id": 503, "title": "SQL for Beginners",        "provider": "Mosh",              "url": "https://www.youtube.com/watch?v=HXV3zeQKqGY"},
        {"id": 504, "title": "Advanced SQL Queries",     "provider": "Corey Schafer",     "url": "https://www.youtube.com/watch?v=9yeOJ0ZMUYw"},
    ],
    "FastAPI": [
        {"id": 505, "title": "FastAPI Crash Course",     "provider": "Traversy",          "url": "https://www.youtube.com/watch?v=0sOvCWFmrtA"},
        {"id": 506, "title": "FastAPI with PostgreSQL",  "provider": "Tiangolo",          "url": "https://www.youtube.com/watch?v=398Yjhpkn5g"},
    ],
    "Docker": [
        {"id": 507, "title": "Docker for Developers",   "provider": "TechWorld with Nana","url": "https://www.youtube.com/watch?v=3c-iKn767wE"},
        {"id": 508, "title": "Docker Compose Mastery",  "provider": "NetworkChuck",       "url": "https://www.youtube.com/watch?v=MVIcrmeV_6c"},
    ],
}

# Role → skills to assess in diagnostic
role_skills_map = {
    "backend developer":   ["Python", "SQL", "FastAPI", "Docker"],
    "frontend developer":  ["HTML/CSS", "JavaScript", "React"],
    "fullstack developer": ["Python", "SQL", "FastAPI", "Docker"],
}


# SCORING ALGORITHM
# Weights: Skill Relevance(40%), Rating(30%), Level Match(20%), Provider Authority(10%)


def calculate_score(course, target_level, popularity_score: float = None):
    # Use YT popularity score if available, else use hardcoded rating
    r = popularity_score if popularity_score is not None else course["rating"]
    l = 1.0 if course["level"].lower() == target_level.lower() else 0.5
    s = 1.0  # Topic Relevance
    p = 1.0 if course["provider"] in ["FreeCodeCamp", "Mosh", "Tiangolo", "AWS Training"] else 0.8

    final_score = (0.4 * s) + (0.3 * r) + (0.2 * l) + (0.1 * p)
    return round(final_score * 100, 1)

# Grading helper used by both diagnostic and delta endpoints
def grade_answers(submitted: List[DiagnosticAnswer], question_bank: List[dict]) -> dict:
    bank_map  = {q["id"]: q for q in question_bank}
    correct   = 0
    breakdown = []
    for ans in submitted:
        q = bank_map.get(ans.question_id)
        if not q:
            continue
        is_correct = ans.selected_option == q["answer"]
        if is_correct:
            correct += 1
        breakdown.append({
            "question_id":    ans.question_id,
            "your_answer":    ans.selected_option,
            "correct_answer": q["answer"],
            "is_correct":     is_correct,
        })
    score_pct = round((correct / len(question_bank)) * 100)
    return {"score_pct": score_pct, "correct": correct, "total": len(question_bank), "breakdown": breakdown}

# Helper to safely get or init a user's assessment state
def get_skill_state(user_id: str, skill: str) -> dict:
    if user_id not in user_assessments:
        user_assessments[user_id] = {}
    if skill not in user_assessments[user_id]:
        user_assessments[user_id][skill] = {
            "verified":        False,
            "score_pct":       None,
            "gap":             False,
            "resources_done":  [],
            "delta_passed":    False,
            "diagnostic_done": False,
        }
    return user_assessments[user_id][skill]

# EXISTING ENDPOINTS 

@app.post("/api/v1/generate-path")
async def generate_path(profile: UserProfile):
    history = user_histories.get(profile.user_id, [])

    # Curriculum
    beginner_be     = ["Python Basics", "Database Integration", "API Development", "Version Control"]
    intermediate_be = ["API Development", "System Design", "Docker & Containers", "Asynchronous Tasks"]
    advanced_be     = ["System Design", "Cloud Architecture", "Performance Tuning", "Security Patterns"]
    frontend_path   = ["HTML/CSS Essentials", "JavaScript Basics", "React Framework", "State Management"]

    # AutoPromotion Logic
    if "backend" in profile.role.lower():
        has_beg = all(any(pill.lower() in t.lower() for pill in profile.current_skills) for t in beginner_be)
        has_int = all(any(pill.lower() in t.lower() for pill in profile.current_skills) for t in intermediate_be)

        if has_beg and has_int:
            topics, target_level, engine = advanced_be,     "Advanced",     "AI-Driven - Expert Mode"
        elif has_beg:
            topics, target_level, engine = intermediate_be, "Intermediate", "AI-Driven - Auto-Promoted"
        else:
            topics, target_level, engine = beginner_be,     "Beginner",     "Rules-Based"
    else:
        topics, target_level, engine = frontend_path, "Beginner", "Rules-Based"

    roadmap      = []
    active_found = False

    for i, topic in enumerate(topics):
        relevant_ids    = [c["id"] for c in mock_courses if c["topic"] == topic]
        is_history_done = any(cid in history for cid in relevant_ids)
        is_pill_skipped = any(pill.lower() in topic.lower() for pill in profile.current_skills)
        is_reviewable   = False

        if is_history_done:
            status = "completed"
        elif is_pill_skipped:
            status        = "review"
            is_reviewable = True
        elif not active_found:
            status, active_found = "active", True
        else:
            status = "locked"

        courses = []
        if status in ["completed", "review", "active"]:
            available = [c for c in mock_courses if c["topic"] == topic]
            for c in available:
                # Use real popularity score from YT system if available
                pop_score = None
                if c["resource_url"] in real_playlists:
                    pop_score = real_playlists[c["resource_url"]].get("popularity_score")

                courses.append({
                    "course_id":    c["id"],
                    "title":        c["title"],
                    "provider":     c.get("provider", "Unknown"),
                    "resource_url": c["resource_url"],
                    "match_score":  calculate_score(c, target_level, pop_score),
                    "is_finished":  c["id"] in history or is_pill_skipped,
                })
            if status == "active":
                courses = sorted(courses, key=lambda x: x["match_score"], reverse=True)

        roadmap.append({
            "step":              i + 1,
            "topic":             topic,
            "status":            status,
            "is_reviewable":     is_reviewable,
            "suggested_courses": courses,
        })

    return {
        "user_id":          profile.user_id,
        "role":             profile.role,
        "inferred_level":   target_level,
        "engine":           engine,
        "roadmap":          roadmap,
        "is_path_finished": all(s["status"] in ["completed", "review"] for s in roadmap),
    }


@app.post("/api/v1/user/history")
async def update_history(update: HistoryUpdate):
    if update.user_id not in user_histories:
        user_histories[update.user_id] = []
    if update.course_id not in user_histories[update.user_id]:
        user_histories[update.user_id].append(update.course_id)
    return {"status": "success"}


@app.get("/api/v1/user/{user_id}/history")
async def get_history(user_id: str):
    history_ids = user_histories.get(user_id, [])
    completed   = [c for c in mock_courses if c["id"] in history_ids]
    return {"user_id": user_id, "total": len(completed), "courses": completed}


# ASSESSMENT ENDPOINTS 

# STEP 1 — Get diagnostic questions for a skill
# GET /api/v1/assessment/questions?user_id=u1&skill=Python

@app.get("/api/v1/assessment/questions")
async def get_diagnostic_questions(user_id: str, skill: str):
    questions = diagnostic_questions.get(skill)
    if not questions:
        raise HTTPException(status_code=404, detail=f"No diagnostic available for skill '{skill}'.")

    state = get_skill_state(user_id, skill)
    if state["diagnostic_done"]:
        raise HTTPException(status_code=400, detail=f"Diagnostic for '{skill}' already completed.")

    safe = [{"id": q["id"], "question": q["question"], "options": q["options"]} for q in questions]
    return {"user_id": user_id, "skill": skill, "questions": safe}


# STEP 2 — Submit diagnostic answers
# POST /api/v1/assessment/submit

@app.post("/api/v1/assessment/submit")
async def submit_diagnostic(submission: DiagnosticSubmission):
    questions = diagnostic_questions.get(submission.skill)
    if not questions:
        raise HTTPException(status_code=404, detail=f"No diagnostic available for '{submission.skill}'.")

    state = get_skill_state(submission.user_id, submission.skill)
    if state["diagnostic_done"]:
        raise HTTPException(status_code=400, detail=f"Diagnostic for '{submission.skill}' already completed.")

    grading  = grade_answers(submission.answers, questions)
    is_gap   = grading["score_pct"] < 60
    verified = not is_gap

    state["diagnostic_done"] = True
    state["score_pct"]       = grading["score_pct"]
    state["gap"]             = is_gap
    state["verified"]        = verified

    resources = []
    if is_gap:
        resources = gap_resources.get(submission.skill, [])

    return {
        "user_id":       submission.user_id,
        "skill":         submission.skill,
        "score_pct":     grading["score_pct"],
        "badge":         "verified" if verified else "unverified",
        "result":        "passed" if verified else "gap_detected",
        "message":       (
            f"'{submission.skill}' verified! You can skip this in your roadmap."
            if verified else
            f"Gap detected in '{submission.skill}'. Study the resources below, then take the delta test."
        ),
        "gap_resources": resources,
        "breakdown":     grading["breakdown"],
    }


# STEP 3 — Mark a gap resource as completed
# POST /api/v1/assessment/resource-done

@app.post("/api/v1/assessment/resource-done")
async def mark_resource_done(completion: ResourceCompletion):
    state = get_skill_state(completion.user_id, completion.skill)

    if not state["gap"]:
        raise HTTPException(status_code=400, detail=f"'{completion.skill}' is not a gap skill. No resources needed.")

    if completion.resource_id not in state["resources_done"]:
        state["resources_done"].append(completion.resource_id)

    all_resource_ids = [r["id"] for r in gap_resources.get(completion.skill, [])]
    all_done         = all(rid in state["resources_done"] for rid in all_resource_ids)

    return {
        "user_id":             completion.user_id,
        "skill":               completion.skill,
        "resource_id":         completion.resource_id,
        "resources_completed": state["resources_done"],
        "delta_test_unlocked": all_done,
        "message":             "Delta test unlocked! Test your knowledge now." if all_done else "Keep going — complete all resources to unlock the delta test.",
    }


# STEP 4 — Get delta test questions
# GET /api/v1/assessment/delta/questions?user_id=u1&skill=Python

@app.get("/api/v1/assessment/delta/questions")
async def get_delta_questions(user_id: str, skill: str):
    state = get_skill_state(user_id, skill)

    if not state["gap"]:
        raise HTTPException(status_code=400, detail=f"'{skill}' is not a gap skill. No delta test needed.")
    if state["delta_passed"]:
        raise HTTPException(status_code=400, detail=f"Delta test for '{skill}' already passed.")

    all_resource_ids = [r["id"] for r in gap_resources.get(skill, [])]
    if not all(rid in state["resources_done"] for rid in all_resource_ids):
        raise HTTPException(status_code=403, detail="Complete all gap resources before taking the delta test.")

    questions = delta_questions.get(skill)
    if not questions:
        raise HTTPException(status_code=404, detail=f"No delta test available for '{skill}'.")

    safe = [{"id": q["id"], "question": q["question"], "options": q["options"]} for q in questions]
    return {"user_id": user_id, "skill": skill, "type": "Delta Test", "questions": safe}


# STEP 5 — Submit delta test
# POST /api/v1/assessment/delta/submit

@app.post("/api/v1/assessment/delta/submit")
async def submit_delta(submission: DeltaTestSubmission):
    state = get_skill_state(submission.user_id, submission.skill)

    if not state["gap"]:
        raise HTTPException(status_code=400, detail=f"'{submission.skill}' is not a gap skill.")
    if state["delta_passed"]:
        raise HTTPException(status_code=400, detail="Delta test already passed.")

    questions = delta_questions.get(submission.skill, [])
    grading   = grade_answers(submission.answers, questions)
    passed    = grading["score_pct"] >= 60

    if passed:
        state["delta_passed"] = True
        state["verified"]     = True
        state["gap"]          = False

    return {
        "user_id":   submission.user_id,
        "skill":     submission.skill,
        "score_pct": grading["score_pct"],
        "passed":    passed,
        "badge":     "verified" if passed else "unverified",
        "message":   (
            f"'{submission.skill}' is now verified! Your roadmap has been updated."
            if passed else
            "Not quite — review the resources again and retry."
        ),
        "breakdown": grading["breakdown"],
    }


# BONUS — Full skill status for a user
# GET /api/v1/assessment/status/{user_id}

@app.get("/api/v1/assessment/status/{user_id}")
async def get_assessment_status(user_id: str):
    skills_state = user_assessments.get(user_id, {})

    summary = []
    for skill, state in skills_state.items():
        summary.append({
            "skill":           skill,
            "diagnostic_done": state["diagnostic_done"],
            "score_pct":       state["score_pct"],
            "badge":           "verified" if state["verified"] else ("gap" if state["gap"] else "not_assessed"),
            "delta_passed":    state["delta_passed"],
        })

    return {
        "user_id":         user_id,
        "skills_assessed": summary,
        "all_verified":    all(s["badge"] == "verified" for s in summary) if summary else False,
    }



# INTEGRATION ENDPOINTS 

@app.get("/api/v1/roadmap/next")
async def get_next_roadmap_step(user_id: str, playlist_id: str):
    history      = user_histories.get(user_id, [])
    skills_state = user_assessments.get(user_id, {})

    # Get all verified skills — these topics will be skipped
    verified_skills = [
        skill.lower() for skill, state in skills_state.items()
        if state.get("verified")
    ]

    # Find next course not in history and not already verified
    for course in mock_courses:
        course_id = course["id"]
        topic     = course["topic"].lower()

        # Skip if already completed
        if course_id in history:
            continue

        # Skip if skill is already verified
        if any(skill in topic for skill in verified_skills):
            continue

        return {
            "user_id":     user_id,
            "playlist_id": course.get("resource_url", ""),
            "topic":       course["topic"],
            "level":       course["level"],
            "skill_tags":  course.get("skill_tags", []),
            "reason":      "roadmap_next"
        }

    return {
        "user_id":     user_id,
        "playlist_id": None,
        "reason":      "roadmap_complete",
        "message":     "User has completed all roadmap steps"
    }


# POST /api/v1/roadmap/complete

@app.post("/api/v1/roadmap/complete")
async def mark_roadmap_step_complete(data: RoadmapComplete):
    if data.user_id not in user_histories:
        user_histories[data.user_id] = []

    # Match playlist back to a course and mark it done
    for course in mock_courses:
        if course.get("resource_url", "") == data.playlist_id:
            if course["id"] not in user_histories[data.user_id]:
                user_histories[data.user_id].append(course["id"])
            return {
                "status":      "success",
                "user_id":     data.user_id,
                "course_done": course["title"],
                "topic":       course["topic"],
                "message":     "Roadmap step complete. Next step unlocked."
            }

    return {
        "status":  "not_found",
        "message": "No matching course found for this playlist"
    }


# Fetch real playlists and popularity scores 
# Replaces mock rating with real popularity data from analytics
# GET /api/v1/sync-playlists

@app.get("/api/v1/sync-playlists")
async def sync_playlists_from_yt_system():
    try:
        # Get all  real playlists
        playlists_resp = httpx.get(
            f"{YT_SERVICE_URL}/playlist/all",
            timeout=5.0
        )

        # Get popularity scores from analytics service
        popular_resp = httpx.get(
            f"{YT_SERVICE_URL}/analytics/popular?limit=10",
            timeout=5.0
        )

        if playlists_resp.status_code == 200:
            playlists = playlists_resp.json()
            popular   = popular_resp.json() if popular_resp.status_code == 200 else []

            # Build popularity lookup
            # Normalize score to 0-1 range for scoring algorithm
            max_pop = max([p.get("play_count", 1) for p in popular], default=1)
            pop_map = {
                p["video_id"]: round(p.get("play_count", 0) / max_pop, 2)
                for p in popular
            }

            # Store real playlists with popularity scores
            for playlist in playlists.get("items", []):
                pid = playlist.get("youtube_playlist_id", "")
                real_playlists[pid] = {
                    "title":            playlist.get("title", ""),
                    "skill_tags":       playlist.get("skill_tags", []),
                    "level":            playlist.get("level", "Beginner"),
                    "provider":         playlist.get("provider", ""),
                    "popularity_score": pop_map.get(pid, 0.8),
                }

            return {
                "status":          "success",
                "playlists_synced": len(real_playlists),
                "message":         "Real playlists and popularity scores loaded successfully"
            }

    except Exception as e:
        return {
            "status":  "error",
            "message": str(e),
            "note":    "Falling back to mock course data"
        }

    return {"status": "failed", "message": "Could not reach his service"}
