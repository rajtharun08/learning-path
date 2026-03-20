import os
import json
import httpx
from openai import OpenAI
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="LearningPath Recommendation Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Service URLs
YT_SERVICE_URL = "http://youtube-platform:8000"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# OpenAI client
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# DATA MODELS

class UserProfile(BaseModel):
    user_id: str
    role: str                  # Goal Dropdown (e.g., "Backend Developer")
    current_skills: List[str]  # Skill Pills

class HistoryUpdate(BaseModel):
    user_id: str
    course_id: int

class DiagnosticAnswer(BaseModel):
    question_id: str
    selected_option: str       # "a", "b", "c", or "d"

class DiagnosticSubmission(BaseModel):
    user_id: str
    skill:   str
    level:   str = "Beginner"   # Beginner / Intermediate / Advanced
    answers: List[DiagnosticAnswer]

class ResourceCompletion(BaseModel):
    user_id: str
    resource_id: int
    skill: str

class RoadmapComplete(BaseModel):
    user_id:     str
    playlist_id: str

# MOCK COURSE DATA
# Courses exist at Beginner / Intermediate / Advanced per skill
# Playlists will be replaced by real YT playlists once synced

mock_courses = [

    # ── PYTHON ──────────────────────────────────────────────
    {"id": 1,  "skill": "Python", "topic": "Python Basics",        "level": "Beginner",     "rating": 0.95, "provider": "FreeCodeCamp",       "skill_tags": ["python"],         "resource_url": "https://www.youtube.com/watch?v=rfscVS0vtbw"},
    {"id": 2,  "skill": "Python", "topic": "Python Intermediate",   "level": "Intermediate", "rating": 0.93, "provider": "Corey Schafer",       "skill_tags": ["python"],         "resource_url": "https://www.youtube.com/watch?v=HGOBQPFzWKo"},
    {"id": 3,  "skill": "Python", "topic": "Python Advanced",       "level": "Advanced",     "rating": 0.94, "provider": "ArjanCodes",          "skill_tags": ["python"],         "resource_url": "https://www.youtube.com/watch?v=MCs5OvhZvy8"},

    # ── SQL ──────────────────────────────────────────────────
    {"id": 4,  "skill": "SQL",    "topic": "SQL Basics",            "level": "Beginner",     "rating": 0.92, "provider": "Mosh",                "skill_tags": ["sql"],            "resource_url": "https://www.youtube.com/watch?v=HXV3zeQKqGY"},
    {"id": 5,  "skill": "SQL",    "topic": "SQL Intermediate",      "level": "Intermediate", "rating": 0.91, "provider": "Corey Schafer",       "skill_tags": ["sql"],            "resource_url": "https://www.youtube.com/watch?v=9yeOJ0ZMUYw"},
    {"id": 6,  "skill": "SQL",    "topic": "SQL Advanced",          "level": "Advanced",     "rating": 0.93, "provider": "Mosh",                "skill_tags": ["sql"],            "resource_url": "https://www.youtube.com/watch?v=7S_tz1z_5bA"},

    # ── FASTAPI ──────────────────────────────────────────────
    {"id": 7,  "skill": "FastAPI","topic": "FastAPI Basics",        "level": "Beginner",     "rating": 0.89, "provider": "Tiangolo",            "skill_tags": ["fastapi", "api"], "resource_url": "https://www.youtube.com/watch?v=0sOvCWFmrtA"},
    {"id": 8,  "skill": "FastAPI","topic": "FastAPI Intermediate",  "level": "Intermediate", "rating": 0.90, "provider": "Tiangolo",            "skill_tags": ["fastapi", "api"], "resource_url": "https://www.youtube.com/watch?v=398Yjhpkn5g"},
    {"id": 9,  "skill": "FastAPI","topic": "FastAPI Advanced",      "level": "Advanced",     "rating": 0.92, "provider": "ArjanCodes",          "skill_tags": ["fastapi", "api"], "resource_url": "https://www.youtube.com/watch?v=SORiTsvnU28"},

    # ── DOCKER ──────────────────────────────────────────────
    {"id": 10, "skill": "Docker", "topic": "Docker Basics",         "level": "Beginner",     "rating": 0.93, "provider": "TechWorld with Nana", "skill_tags": ["docker"],         "resource_url": "https://www.youtube.com/watch?v=3c-iKn767wE"},
    {"id": 11, "skill": "Docker", "topic": "Docker Intermediate",   "level": "Intermediate", "rating": 0.91, "provider": "TechWorld with Nana", "skill_tags": ["docker"],         "resource_url": "https://www.youtube.com/watch?v=MVIcrmeV_6c"},
    {"id": 12, "skill": "Docker", "topic": "Docker Advanced",       "level": "Advanced",     "rating": 0.92, "provider": "TechWorld with Nana", "skill_tags": ["docker"],         "resource_url": "https://www.youtube.com/watch?v=DM65_JyGxCo"},

    # ── VERSION CONTROL ──────────────────────────────────────
    {"id": 13, "skill": "Git",    "topic": "Version Control",       "level": "Beginner",     "rating": 0.94, "provider": "Traversy",            "skill_tags": ["git"],            "resource_url": "https://www.youtube.com/watch?v=RGOj5yH7evk"},
]

# In-memory stores
user_histories   = {}   # { user_id: [course_id, ...] }
user_assessments = {}   # { user_id: { skill: { proficiency_level, score_pct, weak_topics, gap, resources_done, diagnostic_done } } }

# Stores real playlists fetched from YT system
# { playlist_id: { title, skill_tags, level, provider, popularity_score } }
real_playlists = {}

# Cache for AI generated questions — avoids regenerating for same skill
# { skill: { "Beginner": [...], "Intermediate": [...], "Advanced": [...] } }
question_cache = {}

# Beginner diagnostic questions (rule-based — hardcoded, no AI cost)
# Tagged by difficulty: easy / medium / hard
# Tagged by topic for weak topic detection
beginner_questions = {
    "Python": [
        {"id": "py_1", "difficulty": "easy",   "topic": "data_types",      "question": "Which of these is a mutable data type?",                        "options": {"a": "tuple", "b": "str", "c": "list", "d": "int"},          "answer": "c"},
        {"id": "py_2", "difficulty": "easy",   "topic": "exceptions",      "question": "How do you handle exceptions in Python?",                       "options": {"a": "try/catch", "b": "try/except", "c": "catch/finally", "d": "error/handle"}, "answer": "b"},
        {"id": "py_3", "difficulty": "medium", "topic": "generators",      "question": "What keyword is used to define a generator in Python?",         "options": {"a": "return", "b": "yield", "c": "async", "d": "pass"},     "answer": "b"},
        {"id": "py_4", "difficulty": "medium", "topic": "concurrency",     "question": "What does GIL stand for?",                                      "options": {"a": "Global Interpreter Lock", "b": "General Input Layer", "c": "Global Index List", "d": "None"}, "answer": "a"},
        {"id": "py_5", "difficulty": "hard",   "topic": "decorators",      "question": "What does a decorator do?",                                     "options": {"a": "Imports a module", "b": "Wraps a function to extend its behaviour", "c": "Defines a class", "d": "Creates a variable"}, "answer": "b"},
    ],
    "SQL": [
        {"id": "sql_1", "difficulty": "easy",   "topic": "basics",         "question": "Which is a DDL command?",                                       "options": {"a": "SELECT", "b": "INSERT", "c": "CREATE", "d": "UPDATE"},  "answer": "c"},
        {"id": "sql_2", "difficulty": "easy",   "topic": "basics",         "question": "What does DISTINCT do?",                                        "options": {"a": "Sorts results", "b": "Removes duplicate rows", "c": "Groups rows", "d": "Counts rows"}, "answer": "b"},
        {"id": "sql_3", "difficulty": "medium", "topic": "joins",          "question": "What does INNER JOIN return?",                                  "options": {"a": "All rows from both tables", "b": "Only matched rows", "c": "Only left table rows", "d": "Null rows"}, "answer": "b"},
        {"id": "sql_4", "difficulty": "medium", "topic": "grouping",       "question": "Which clause filters rows AFTER grouping?",                    "options": {"a": "WHERE", "b": "FILTER", "c": "HAVING", "d": "ORDER BY"}, "answer": "c"},
        {"id": "sql_5", "difficulty": "hard",   "topic": "search",         "question": "Which keyword is used for partial text search?",               "options": {"a": "MATCH", "b": "CONTAINS", "c": "LIKE", "d": "SIMILAR"},  "answer": "c"},
    ],
    "FastAPI": [
        {"id": "fa_1", "difficulty": "easy",   "topic": "basics",          "question": "Which library does FastAPI use for data validation?",           "options": {"a": "Marshmallow", "b": "Cerberus", "c": "Pydantic", "d": "Voluptuous"}, "answer": "c"},
        {"id": "fa_2", "difficulty": "easy",   "topic": "routing",         "question": "Which decorator handles GET requests?",                         "options": {"a": "@app.get()", "b": "@app.fetch()", "c": "@app.read()", "d": "@app.request()"}, "answer": "a"},
        {"id": "fa_3", "difficulty": "medium", "topic": "async",           "question": "What does async/await enable in FastAPI?",                      "options": {"a": "Multi-threading", "b": "Concurrency without blocking", "c": "Parallel processing", "d": "Caching"}, "answer": "b"},
        {"id": "fa_4", "difficulty": "medium", "topic": "dependency",      "question": "What is Depends() used for?",                                   "options": {"a": "Database connection", "b": "Dependency injection", "c": "Middleware setup", "d": "Route grouping"}, "answer": "b"},
        {"id": "fa_5", "difficulty": "hard",   "topic": "response",        "question": "What does response_model do?",                                  "options": {"a": "Validates input", "b": "Filters and validates output", "c": "Caches responses", "d": "Logs the response"}, "answer": "b"},
    ],
    "Docker": [
        {"id": "dk_1", "difficulty": "easy",   "topic": "basics",          "question": "What is the purpose of a Dockerfile?",                         "options": {"a": "Configure a database", "b": "Define container build instructions", "c": "Set up networking", "d": "Install Python"}, "answer": "b"},
        {"id": "dk_2", "difficulty": "easy",   "topic": "commands",        "question": "Which command runs a Docker container?",                        "options": {"a": "docker start", "b": "docker launch", "c": "docker run", "d": "docker exec"}, "answer": "c"},
        {"id": "dk_3", "difficulty": "medium", "topic": "compose",         "question": "What does docker-compose do?",                                  "options": {"a": "Builds images", "b": "Manages multi-container apps", "c": "Deploys to cloud", "d": "Tests containers"}, "answer": "b"},
        {"id": "dk_4", "difficulty": "medium", "topic": "storage",         "question": "What is a Docker volume used for?",                             "options": {"a": "CPU allocation", "b": "Persistent data storage", "c": "Network routing", "d": "Image compression"}, "answer": "b"},
        {"id": "dk_5", "difficulty": "hard",   "topic": "environment",     "question": "How do you pass environment variables to a container?",         "options": {"a": "-v flag", "b": "-e flag", "c": "--network flag", "d": "ARGS in Dockerfile"}, "answer": "b"},
    ],
    "Git": [
        {"id": "git_1", "difficulty": "easy",   "topic": "basics",         "question": "What does git init do?",                                        "options": {"a": "Clones a repo", "b": "Initializes a new Git repository", "c": "Commits changes", "d": "Pushes to remote"}, "answer": "b"},
        {"id": "git_2", "difficulty": "easy",   "topic": "staging",        "question": "Which command stages all changes for commit?",                  "options": {"a": "git commit", "b": "git push", "c": "git add .", "d": "git status"}, "answer": "c"},
        {"id": "git_3", "difficulty": "medium", "topic": "branching",      "question": "What does git checkout -b do?",                                 "options": {"a": "Deletes a branch", "b": "Switches to existing branch", "c": "Creates and switches to a new branch", "d": "Merges branches"}, "answer": "c"},
        {"id": "git_4", "difficulty": "medium", "topic": "merging",        "question": "What is a merge conflict?",                                     "options": {"a": "A failed push", "b": "When two branches have conflicting changes", "c": "A deleted branch", "d": "An untracked file"}, "answer": "b"},
        {"id": "git_5", "difficulty": "hard",   "topic": "rebasing",       "question": "What does git rebase do?",                                      "options": {"a": "Deletes commits", "b": "Moves commits to a new base", "c": "Reverts changes", "d": "Stashes changes"}, "answer": "b"},
    ],
}

# Gap bridge resources — assigned when skill level is Beginner with weak topics
gap_resources = {
    "Python": [
        {"id": 501, "title": "Python Full Course",      "provider": "FreeCodeCamp",      "url": "https://www.youtube.com/watch?v=rfscVS0vtbw"},
        {"id": 502, "title": "Python OOP Tutorial",     "provider": "Corey Schafer",     "url": "https://www.youtube.com/watch?v=ZDa-Z5JzLYM"},
    ],
    "SQL": [
        {"id": 503, "title": "SQL for Beginners",       "provider": "Mosh",              "url": "https://www.youtube.com/watch?v=HXV3zeQKqGY"},
        {"id": 504, "title": "Advanced SQL Queries",    "provider": "Corey Schafer",     "url": "https://www.youtube.com/watch?v=9yeOJ0ZMUYw"},
    ],
    "FastAPI": [
        {"id": 505, "title": "FastAPI Crash Course",    "provider": "Traversy",          "url": "https://www.youtube.com/watch?v=0sOvCWFmrtA"},
        {"id": 506, "title": "FastAPI with PostgreSQL", "provider": "Tiangolo",          "url": "https://www.youtube.com/watch?v=398Yjhpkn5g"},
    ],
    "Docker": [
        {"id": 507, "title": "Docker for Developers",  "provider": "TechWorld with Nana","url": "https://www.youtube.com/watch?v=3c-iKn767wE"},
        {"id": 508, "title": "Docker Compose Mastery", "provider": "NetworkChuck",       "url": "https://www.youtube.com/watch?v=MVIcrmeV_6c"},
    ],
}

# Role → ordered curriculum topics for Beginner tier (rules-based)
role_curriculum = {
    "backend developer": ["Python", "SQL", "FastAPI", "Docker", "Git"],
    "frontend developer": ["HTML/CSS", "JavaScript", "React"],
    "fullstack developer": ["Python", "SQL", "FastAPI", "Docker", "Git"],
}

# Role → skills to assess in diagnostic
role_skills_map = {
    "backend developer":   ["Python", "SQL", "FastAPI", "Docker"],
    "frontend developer":  ["HTML/CSS", "JavaScript", "React"],
    "fullstack developer": ["Python", "SQL", "FastAPI", "Docker"],
}



# AI QUESTION GENERATOR
# Uses OpenAI to generate Intermediate and Advanced diagnostic questions
# Beginner questions are hardcoded (rule-based, no AI cost)


async def generate_ai_questions(skill: str, level: str) -> List[dict]:
    # Return from cache if already generated
    if skill in question_cache and level in question_cache[skill]:
        return question_cache[skill][level]

    prompt = f"""Generate exactly 5 multiple choice diagnostic questions for {skill} at {level} level.

Rules:
- Questions 1-2: medium difficulty (applied concepts)
- Questions 3-4: hard difficulty (advanced topics)  
- Question 5: hard difficulty (expert level)
- Each question must have exactly 4 options: a, b, c, d
- Include the topic tag for each question (e.g. async, decorators, joins)

Return ONLY valid JSON in this exact format, no extra text:
[
  {{
    "id": "{skill.lower()[:2]}_{level.lower()[:3]}_1",
    "difficulty": "medium",
    "topic": "topic_name",
    "question": "Question text here?",
    "options": {{"a": "option1", "b": "option2", "c": "option3", "d": "option4"}},
    "answer": "b"
  }}
]"""

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        raw = response.choices[0].message.content.strip()
        # Strip markdown code fences if present
        raw = raw.replace("```json", "").replace("```", "").strip()
        questions = json.loads(raw)

        # Store in cache
        if skill not in question_cache:
            question_cache[skill] = {}
        question_cache[skill][level] = questions
        return questions

    except Exception as e:
        # Fallback to beginner questions if AI fails
        return beginner_questions.get(skill, [])



# AI ADVANCED ROADMAP GENERATOR
# Used only for Advanced tier — generates custom topic list
# Beginner and Intermediate use fixed rule-based curricula


async def generate_ai_roadmap(role: str, skill_profiles: dict) -> List[str]:
    profile_summary = "\n".join([
        f"- {skill}: {data.get('proficiency_level', 'Beginner')} (weak topics: {', '.join(data.get('weak_topics', [])) or 'none'})"
        for skill, data in skill_profiles.items()
    ])

    prompt = f"""Generate a personalized Advanced learning roadmap for a {role}.

User skill profile:
{profile_summary}

Rules:
- Generate 5-6 advanced topics tailored to their weak areas
- Topics should be specific and actionable
- Focus on depth, real-world application, system design
- Return ONLY a JSON array of topic strings, no extra text

Example format:
["Advanced Async Python", "Database Query Optimization", "FastAPI Microservices", "Docker Orchestration", "System Design Patterns"]"""

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
        )
        raw = response.choices[0].message.content.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        topics = json.loads(raw)
        return topics

    except Exception:
        # Fallback to fixed advanced topics
        return ["System Design", "Cloud Architecture", "Performance Tuning", "Security Patterns"]



# PROFICIENCY DETECTION
# Derives Beginner / Intermediate / Advanced from diagnostic performance


def detect_proficiency_level(answers: List[DiagnosticAnswer], questions: List[dict]) -> dict:
    bank_map = {q["id"]: q for q in questions}

    easy_total   = sum(1 for q in questions if q.get("difficulty") == "easy")
    medium_total = sum(1 for q in questions if q.get("difficulty") == "medium")
    hard_total   = sum(1 for q in questions if q.get("difficulty") == "hard")

    easy_correct   = 0
    medium_correct = 0
    hard_correct   = 0
    weak_topics    = []

    for ans in answers:
        q = bank_map.get(ans.question_id)
        if not q:
            continue
        is_correct = ans.selected_option == q["answer"]
        difficulty = q.get("difficulty", "easy")
        topic      = q.get("topic", "")

        if difficulty == "easy"   and is_correct: easy_correct   += 1
        if difficulty == "medium" and is_correct: medium_correct += 1
        if difficulty == "hard"   and is_correct: hard_correct   += 1

        # Track weak topics — wrong answers even if overall pass
        if not is_correct and topic:
            weak_topics.append(topic)

    # Proficiency level detection
    easy_pct   = (easy_correct   / easy_total   * 100) if easy_total   > 0 else 0
    medium_pct = (medium_correct / medium_total * 100) if medium_total > 0 else 0
    hard_pct   = (hard_correct   / hard_total   * 100) if hard_total   > 0 else 0

    total_correct = easy_correct + medium_correct + hard_correct
    total_q       = len(questions)
    score_pct     = round((total_correct / total_q) * 100) if total_q > 0 else 0

    if easy_pct >= 60 and medium_pct >= 60 and hard_pct >= 60:
        proficiency = "Advanced"
    elif easy_pct >= 60 and medium_pct >= 60:
        proficiency = "Intermediate"
    else:
        proficiency = "Beginner"

    return {
        "proficiency_level": proficiency,
        "score_pct":         score_pct,
        "weak_topics":       list(set(weak_topics)),
        "easy_pct":          round(easy_pct),
        "medium_pct":        round(medium_pct),
        "hard_pct":          round(hard_pct),
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

# Grading helper
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
    score_pct = round((correct / len(question_bank)) * 100) if question_bank else 0
    return {"score_pct": score_pct, "correct": correct, "total": len(question_bank), "breakdown": breakdown}

# Helper to safely get or init a user's assessment state
def get_skill_state(user_id: str, skill: str) -> dict:
    if user_id not in user_assessments:
        user_assessments[user_id] = {}
    if skill not in user_assessments[user_id]:
        user_assessments[user_id][skill] = {
            "proficiency_level": None,       # Beginner / Intermediate / Advanced
            "score_pct":         None,
            "weak_topics":       [],          # Topics user got wrong even if overall pass
            "gap":               False,       # True if Beginner level detected
            "resources_done":    [],
            "diagnostic_done":   False,
        }
    return user_assessments[user_id][skill]



# ROADMAP ENDPOINTS


@app.post("/api/v1/generate-path")
async def generate_path(profile: UserProfile):
    history  = user_histories.get(profile.user_id, [])
    assessed = user_assessments.get(profile.user_id, {})

    # Get per-skill proficiency levels from assessment results
    # Skills claimed but not yet assessed default to Beginner
    curriculum  = role_curriculum.get(profile.role.lower(), [])
    skill_levels = {}
    for skill in curriculum:
        if skill in assessed and assessed[skill].get("diagnostic_done"):
            skill_levels[skill] = assessed[skill].get("proficiency_level", "Beginner")
        elif skill.lower() in [s.lower() for s in profile.current_skills]:
            # Claimed but not assessed yet — treat as Beginner until tested
            skill_levels[skill] = "Beginner"
        else:
            skill_levels[skill] = "Beginner"

    # Determine overall tier from skill levels
    # Weakest link rule — overall tier = lowest skill level
    all_levels  = list(skill_levels.values())
    has_advanced     = all(l == "Advanced"     for l in all_levels) if all_levels else False
    has_intermediate = all(l in ["Intermediate", "Advanced"] for l in all_levels) if all_levels else False

    if has_advanced:
        # AI generates custom Advanced roadmap
        ai_topics    = await generate_ai_roadmap(profile.role, assessed)
        target_level = "Advanced"
        engine       = "AI-Driven"
        topics       = ai_topics

        roadmap      = []
        active_found = False
        for i, topic in enumerate(topics):
            status = "active" if not active_found else "locked"
            if status == "active":
                active_found = True

            # Find Advanced courses matching topic keywords
            available = [c for c in mock_courses if c["level"] == "Advanced" and
                        any(kw.lower() in c["topic"].lower() for kw in topic.split())]
            courses = []
            if status == "active" and available:
                for c in available:
                    pop_score = None
                    if c["resource_url"] in real_playlists:
                        pop_score = real_playlists[c["resource_url"]].get("popularity_score")
                    courses.append({
                        "course_id":    c["id"],
                        "title":        c["title"],
                        "provider":     c.get("provider", "Unknown"),
                        "resource_url": c["resource_url"],
                        "match_score":  calculate_score(c, "Advanced", pop_score),
                        "is_finished":  c["id"] in history,
                    })
                courses = sorted(courses, key=lambda x: x["match_score"], reverse=True)

            roadmap.append({
                "step":              i + 1,
                "topic":             topic,
                "status":            status,
                "is_reviewable":     False,
                "suggested_courses": courses,
                "targeted_resources": [],
                "weak_topics":       [],
            })

    elif has_intermediate:
        # Intermediate — rules-based fixed curriculum, per-skill level content
        target_level = "Intermediate"
        engine       = "Rules-Based - Intermediate"
        curriculum   = role_curriculum.get(profile.role.lower(), [])
        roadmap      = []
        active_found = False

        for i, skill in enumerate(curriculum):
            # Find course matching skill at correct level
            skill_level  = skill_levels.get(skill, "Beginner")
            # Move one level up for tier progression
            next_level   = "Advanced" if skill_level == "Intermediate" else "Intermediate"
            available    = [c for c in mock_courses if c["skill"] == skill and c["level"] == next_level]

            relevant_ids    = [c["id"] for c in available]
            is_history_done = any(cid in history for cid in relevant_ids)

            if is_history_done:
                status = "completed"
            elif not active_found:
                status, active_found = "active", True
            else:
                status = "locked"

            courses = []
            if status in ["completed", "active"]:
                for c in available:
                    pop_score = None
                    if c["resource_url"] in real_playlists:
                        pop_score = real_playlists[c["resource_url"]].get("popularity_score")
                    courses.append({
                        "course_id":    c["id"],
                        "title":        c["title"],
                        "provider":     c.get("provider", "Unknown"),
                        "resource_url": c["resource_url"],
                        "match_score":  calculate_score(c, next_level, pop_score),
                        "is_finished":  c["id"] in history,
                    })
                if status == "active":
                    courses = sorted(courses, key=lambda x: x["match_score"], reverse=True)

            # Attach weak topic gap resources for this skill
            weak_topics   = assessed.get(skill, {}).get("weak_topics", [])
            targeted_resources = gap_resources.get(skill, []) if weak_topics else []

            roadmap.append({
                "step":              i + 1,
                "topic":             f"{skill} — {next_level}",
                "skill":             skill,
                "status":            status,
                "is_reviewable":     False,
                "suggested_courses": courses,
                "targeted_resources": targeted_resources,
                "weak_topics":       weak_topics,
            })

    else:
        # Beginner — rules-based fixed curriculum
        target_level = "Beginner"
        engine       = "Rules-Based - Beginner"
        curriculum   = role_curriculum.get(profile.role.lower(), [])
        roadmap      = []
        active_found = False

        for i, skill in enumerate(curriculum):
            skill_level  = skill_levels.get(skill, "Beginner")
            # Use detected proficiency level for content selection
            content_level = skill_level if skill_level else "Beginner"
            available     = [c for c in mock_courses if c["skill"] == skill and c["level"] == content_level]

            relevant_ids    = [c["id"] for c in available]
            is_history_done = any(cid in history for cid in relevant_ids)

            if is_history_done:
                status = "completed"
            elif not active_found:
                status, active_found = "active", True
            else:
                status = "locked"

            courses = []
            if status in ["completed", "active"]:
                for c in available:
                    pop_score = None
                    if c["resource_url"] in real_playlists:
                        pop_score = real_playlists[c["resource_url"]].get("popularity_score")
                    courses.append({
                        "course_id":    c["id"],
                        "title":        c["title"],
                        "provider":     c.get("provider", "Unknown"),
                        "resource_url": c["resource_url"],
                        "match_score":  calculate_score(c, content_level, pop_score),
                        "is_finished":  c["id"] in history,
                    })
                if status == "active":
                    courses = sorted(courses, key=lambda x: x["match_score"], reverse=True)

            # Attach gap resources for Beginner skills with weak topics
            weak_topics        = assessed.get(skill, {}).get("weak_topics", [])
            skill_gap          = assessed.get(skill, {}).get("gap", False)
            targeted_resources = gap_resources.get(skill, []) if (skill_gap or weak_topics) else []

            roadmap.append({
                "step":              i + 1,
                "topic":             f"{skill} — {content_level}",
                "skill":             skill,
                "status":            status,
                "is_reviewable":     False,
                "suggested_courses": courses,
                "targeted_resources": targeted_resources,
                "weak_topics":       weak_topics,
            })

    # Build competency profile summary
    competency_profile = {
        skill: {
            "proficiency_level": state.get("proficiency_level"),
            "score_pct":         state.get("score_pct"),
            "weak_topics":       state.get("weak_topics", []),
        }
        for skill, state in assessed.items()
        if state.get("diagnostic_done")
    }

    return {
        "user_id":            profile.user_id,
        "role":               profile.role,
        "overall_tier":       target_level,
        "engine":             engine,
        "competency_profile": competency_profile,
        "roadmap":            roadmap,
        "is_path_finished":   all(s["status"] in ["completed"] for s in roadmap),
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
# Beginner → hardcoded rule-based questions
# Intermediate / Advanced → AI generated questions
# GET /api/v1/assessment/questions?user_id=u1&skill=Python&level=Beginner

@app.get("/api/v1/assessment/questions")
async def get_diagnostic_questions(user_id: str, skill: str, level: str = "Beginner"):
    state = get_skill_state(user_id, skill)
    if state["diagnostic_done"]:
        raise HTTPException(status_code=400, detail=f"Diagnostic for '{skill}' already completed.")

    if level == "Beginner":
        # Rule-based — use hardcoded questions
        questions = beginner_questions.get(skill)
        if not questions:
            raise HTTPException(status_code=404, detail=f"No diagnostic available for skill '{skill}'.")
    else:
        # AI generated for Intermediate and Advanced
        questions = await generate_ai_questions(skill, level)
        if not questions:
            raise HTTPException(status_code=404, detail=f"Could not generate questions for '{skill}' at {level} level.")

    # Return questions without answers
    safe = [{"id": q["id"], "difficulty": q.get("difficulty"), "topic": q.get("topic"), "question": q["question"], "options": q["options"]} for q in questions]
    return {"user_id": user_id, "skill": skill, "level": level, "questions": safe}


# STEP 2 — Submit diagnostic answers
# Detects proficiency level and weak topics from performance
# POST /api/v1/assessment/submit

@app.post("/api/v1/assessment/submit")
async def submit_diagnostic(submission: DiagnosticSubmission):
    state = get_skill_state(submission.user_id, submission.skill)
    if state["diagnostic_done"]:
        raise HTTPException(status_code=400, detail=f"Diagnostic for '{submission.skill}' already completed.")

    # Get the right question bank based on level from request body
    if submission.level == "Beginner":
        questions = beginner_questions.get(submission.skill, [])
    else:
        questions = await generate_ai_questions(submission.skill, submission.level)

    if not questions:
        raise HTTPException(status_code=404, detail=f"No questions found for '{submission.skill}'.")

    # Detect proficiency level and weak topics
    result = detect_proficiency_level(submission.answers, questions)

    # Update skill state
    state["diagnostic_done"]   = True
    state["proficiency_level"] = result["proficiency_level"]
    state["score_pct"]         = result["score_pct"]
    state["weak_topics"]       = result["weak_topics"]
    state["gap"]               = result["proficiency_level"] == "Beginner"

    # Assign gap resources if Beginner level detected
    resources = []
    if state["gap"]:
        resources = gap_resources.get(submission.skill, [])

    return {
        "user_id":           submission.user_id,
        "skill":             submission.skill,
        "score_pct":         result["score_pct"],
        "proficiency_level": result["proficiency_level"],
        "weak_topics":       result["weak_topics"],
        "easy_pct":          result["easy_pct"],
        "medium_pct":        result["medium_pct"],
        "hard_pct":          result["hard_pct"],
        "badge":             result["proficiency_level"],
        "gap_resources":     resources,
        "message":           f"'{submission.skill}' assessed as {result['proficiency_level']}. " +
                             (f"Weak areas: {', '.join(result['weak_topics'])}." if result["weak_topics"] else "No weak areas detected."),
        "breakdown":         grade_answers(submission.answers, questions)["breakdown"],
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
        "all_done":            all_done,
        "message":             "All gap resources completed. You are ready to start this topic in the roadmap." if all_done else "Keep going — complete all resources before starting the roadmap step.",
    }


# STEP 4 — Full skill assessment status for a user
# GET /api/v1/assessment/status/{user_id}

@app.get("/api/v1/assessment/status/{user_id}")
async def get_assessment_status(user_id: str):
    skills_state = user_assessments.get(user_id, {})

    summary = []
    for skill, state in skills_state.items():
        summary.append({
            "skill":             skill,
            "diagnostic_done":   state["diagnostic_done"],
            "score_pct":         state["score_pct"],
            "proficiency_level": state.get("proficiency_level"),
            "weak_topics":       state.get("weak_topics", []),
            "gap":               state["gap"],
        })

    # Determine overall tier from weakest skill
    levels     = [s["proficiency_level"] for s in summary if s["proficiency_level"]]
    all_adv    = all(l == "Advanced"                       for l in levels) if levels else False
    all_int    = all(l in ["Intermediate", "Advanced"]     for l in levels) if levels else False
    overall    = "Advanced" if all_adv else ("Intermediate" if all_int else "Beginner")

    return {
        "user_id":         user_id,
        "overall_tier":    overall,
        "skills_assessed": summary,
        "all_assessed":    all(s["diagnostic_done"] for s in summary) if summary else False,
    }



# INTEGRATION ENDPOINTS
# Connects to YouTube Learning Platform


# YT recommend engine calls this first before resume/next/popular logic
# GET /api/v1/roadmap/next?user_id=u1&playlist_id=PLxyz

@app.get("/api/v1/roadmap/next")
async def get_next_roadmap_step(user_id: str, playlist_id: str):
    history      = user_histories.get(user_id, [])
    assessed     = user_assessments.get(user_id, {})

    # Find next course not in history — matching user's proficiency level per skill
    for course in mock_courses:
        course_id    = course["id"]
        skill        = course["skill"]
        course_level = course["level"]

        # Skip if already completed
        if course_id in history:
            continue

        # Match course level to user's proficiency for this skill
        user_level = assessed.get(skill, {}).get("proficiency_level", "Beginner")
        if course_level != user_level:
            continue

        return {
            "user_id":     user_id,
            "playlist_id": course.get("resource_url", ""),
            "topic":       course["topic"],
            "skill":       skill,
            "level":       course_level,
            "skill_tags":  course.get("skill_tags", []),
            "reason":      "roadmap_next"
        }

    return {
        "user_id":     user_id,
        "playlist_id": None,
        "reason":      "roadmap_complete",
        "message":     "User has completed all roadmap steps"
    }


# YT progress service calls this when course hits 90% done
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


# Fetch real playlists and popularity scores from YT system
# Replaces mock rating with real popularity data from analytics
# GET /api/v1/sync-playlists

@app.get("/api/v1/sync-playlists")
async def sync_playlists_from_yt_system():
    try:
        # Get all real playlists
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
                "status":           "success",
                "playlists_synced": len(real_playlists),
                "message":          "Real playlists and popularity scores loaded successfully"
            }

    except Exception as e:
        return {
            "status":  "error",
            "message": str(e),
            "note":    "Falling back to mock course data"
        }

    return {"status": "failed", "message": "Could not reach YT service"}