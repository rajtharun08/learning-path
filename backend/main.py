import os
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

# DATA MODELS
class UserProfile(BaseModel):
    user_id: str
    role: str                 # Goal Dropdown (e.g., "Backend Developer")
    current_skills: List[str] # Skill Pills

class HistoryUpdate(BaseModel):
    user_id: str
    course_id: int

# MOCK DB
mock_courses = [
    # Beginner Topics
    {"id": 1, "title": "Python Syntax & Logic", "topic": "Python Basics", "level": "Beginner", "rating": 0.95, "provider": "FreeCodeCamp", "resource_url": "https://www.youtube.com/watch?v=rfscVS0vtbw"},
    {"id": 14, "title": "Git & GitHub Masterclass", "topic": "Version Control", "level": "Beginner", "rating": 0.94, "provider": "Traversy", "resource_url": "https://www.youtube.com/watch?v=RGOj5yH7evk"},
    {"id": 6, "title": "HTML/CSS Crash Course", "topic": "HTML/CSS Essentials", "level": "Beginner", "rating": 0.94, "provider": "Traversy", "resource_url": "https://www.youtube.com/watch?v=gvOivz9skfA"},
    
    # Intermediate Topics
    {"id": 3, "title": "SQL for Backend Devs", "topic": "Database Integration", "level": "Intermediate", "rating": 0.92, "provider": "Mosh", "resource_url": "https://www.youtube.com/watch?v=HXV3zeQKqGY"},
    {"id": 15, "title": "Build a REST API with FastAPI", "topic": "API Development", "level": "Intermediate", "rating": 0.89, "provider": "Tiangolo", "resource_url": "https://www.youtube.com/watch?v=0sOvCWFmrtA"},
    {"id": 8, "title": "Docker for Developers", "topic": "System Design", "level": "Intermediate", "rating": 0.93, "provider": "TechWorld with Nana", "resource_url": "https://www.youtube.com/watch?v=3c-iKn767wE"},
    {"id": 16, "title": "Celery & Redis for Tasks", "topic": "Asynchronous Tasks", "level": "Intermediate", "rating": 0.87, "provider": "CoreyMS", "resource_url": "https://www.youtube.com/watch?v=68QWw0Ot4Ng"},
    
    # Advanced Topics
    {"id": 5, "title": "Microservices Architecture", "topic": "System Design", "level": "Advanced", "rating": 0.96, "provider": "YouTube", "resource_url": "https://www.youtube.com/watch?v=123456"},
    {"id": 9, "title": "AWS Cloud Architecture", "topic": "Cloud Architecture", "level": "Advanced", "rating": 0.97, "provider": "AWS Training", "resource_url": "https://www.youtube.com/watch?v=ia7Mte8q08I"},
    {"id": 17, "title": "JWT Authentication Patterns", "topic": "Security Patterns", "level": "Advanced", "rating": 0.93, "provider": "Auth0", "resource_url": "https://www.youtube.com/watch?v=7Q17ubqLfaM"},
    {"id": 10, "title": "Redis Caching & Performance", "topic": "Performance Tuning", "level": "Advanced", "rating": 0.94, "provider": "Redis University", "resource_url": "https://www.youtube.com/watch?v=OqZz90v-m5M"}
]

user_histories = {}

# SCORING ALGORITHM
def calculate_score(course, target_level):
    r = course["rating"]
    l = 1.0 if course["level"].lower() == target_level.lower() else 0.5 
    s = 1.0 # Topic Relevance
    p = 1.0 if course["provider"] in ["FreeCodeCamp", "Mosh", "Tiangolo", "AWS Training"] else 0.8 
    
    # Weights: Skill(40%), Rating(30%), Level(20%), Provider(10%)
    final_score = (0.4 * s) + (0.3 * r) + (0.2 * l) + (0.1 * p)
    return round(final_score * 100, 1)

# ROADMAP GENERATION 
@app.post("/api/v1/generate-path")
async def generate_path(profile: UserProfile):
    history = user_histories.get(profile.user_id, [])
    
    # Curriculum 
    beginner_be = ["Python Basics", "Database Integration", "API Development", "Version Control"]
    intermediate_be = ["API Development", "System Design", "Docker & Containers", "Asynchronous Tasks"]
    advanced_be = ["System Design", "Cloud Architecture", "Performance Tuning", "Security Patterns"]
    frontend_path = ["HTML/CSS Essentials", "JavaScript Basics", "React Framework", "State Management"]

    # AutoPromotion Logic
    if "backend" in profile.role.lower():
        has_beg = all(any(pill.lower() in t.lower() for pill in profile.current_skills) for t in beginner_be)
        has_int = all(any(pill.lower() in t.lower() for pill in profile.current_skills) for t in intermediate_be)

        if has_beg and has_int:
            topics, target_level, engine = advanced_be, "Advanced", "AI-Driven - Expert Mode"
        elif has_beg:
            topics, target_level, engine = intermediate_be, "Intermediate", "AI-Driven - Auto-Promoted"
        else:
            topics, target_level, engine = beginner_be, "Beginner", "Rules-Based"
    else:
        topics, target_level, engine = frontend_path, "Beginner", "Rules-Based"

    roadmap = []
    active_found = False

    for i, topic in enumerate(topics):
        relevant_ids = [c["id"] for c in mock_courses if c["topic"] == topic]
        is_done = any(cid in history for cid in relevant_ids) or \
                  any(pill.lower() in topic.lower() for pill in profile.current_skills)

        if is_done:
            status, courses = "completed", []
            for c in [x for x in mock_courses if x["topic"] == topic]:
                courses.append({"course_id": c["id"], "title": c["title"], "resource_url": c["resource_url"], "is_finished": True})
        elif not active_found:
            status, active_found = "active", True
            available = [c for c in mock_courses if c["topic"] == topic]
            courses = sorted([
                {**c, "course_id": c["id"], "match_score": calculate_score(c, target_level), "is_finished": c["id"] in history}
                for c in available
            ], key=lambda x: x["match_score"], reverse=True)
        else:
            status, courses = "locked", []

        roadmap.append({"step": i + 1, "topic": topic, "status": status, "suggested_courses": courses})

    return {
        "user_id": profile.user_id, "role": profile.role, "inferred_level": target_level,
        "engine": engine, "roadmap": roadmap, "is_path_finished": all(s["status"] == "completed" for s in roadmap)
    }

# HISTORY MANAGEMENT
@app.post("/api/v1/user/history")
async def update_history(update: HistoryUpdate):
    user_histories.setdefault(update.user_id, []).append(update.course_id)
    return {"status": "success"}

@app.get("/api/v1/user/{user_id}/history")
async def get_history(user_id: str):
    history_ids = user_histories.get(user_id, [])
    completed = [c for c in mock_courses if c["id"] in history_ids]
    return {"user_id": user_id, "total": len(completed), "courses": completed}
