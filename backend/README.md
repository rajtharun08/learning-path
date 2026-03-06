# Technical Overview
The backend is built with FastAPI and implements three core logic
layers:

**Tier Detection:** Automatically classifies users into Beginner,
Intermediate, or Advanced tracks based on input skills (Pills).

**Redundancy Filtering:** Automatically completes roadmap steps if the user
demonstrates existing mastery of the topic.

**Weighted Scoring:** Ranks course recommendations using a multi-factor
algorithm (Rating: 30%, Skill Relevance: 40%, Level Match: 20%, Provider
Authority: 10%).

# Getting Started

## Prerequisites

Python 3.8+
pip

## Installation

``` bash
cd backend
python -m venv .venv 
.venv\Scripts\activate
pip install fastapi uvicorn pydantic
```

## Running the Server
run the following
command from the root directory:

``` bash
uvicorn main:app --reload
```

The server will be available at http://127.0.0.1:8000 

# API Documentation and Integration

## Interactive Documentation

Once the server is running, access the full API contract and testing
suite at: http://127.0.0.1:8000/docs


# Core Endpoints

## 1. Generate Learning Path

**Endpoint:** POST /api/v1/generate-path

**Payload:** UserProfile (user_id, role, current_skills)

**Logic:** Returns a dynamic roadmap where each step is marked as completed,
active, or locked.

## 2. Update User History

**Endpoint:** POST /api/v1/user/history

**Payload:** HistoryUpdate (user_id, course_id)

**Logic:** Persists course completion state to unlock subsequent roadmap
milestones.

# UI State Mapping Reference
The frontend should utilize the status field in the roadmap steps for
conditional rendering:

**completed:** Topic mastered. Render with a finished state.

**active:** Current focus. Render course cards and details.

**locked:** Prerequisite required. Render as disabled or hidden.

The is_path_finished boolean should be used to trigger the final
completion state in the user interface.
