# Backend Architecture: LearningPath Recommendation Engine

This document outlines the technical architecture, data flow, and logic implementation for the **LearningPath Backend POC**.

## 1. System Overview
The backend is built using **FastAPI**, chosen for its high performance, asynchronous capabilities, and native support for Pydantic data validation. The system serves as a "Hybrid Recommendation Engine," balancing local rule-based logic with external AI inference.

### Component Structure
The following hierarchy represents how the system processes a user request:
```
Frontend (React UI)
        │
        ▼
FastAPI Backend (API Gateway)
        │
        ├─ Tier Detection Logic: Identifies user level (Beginner/Advanced).
        ├─ Scoring Algorithm: Ranks available content based on 40/30/20/10 weightage.
        ├─ Roadmap Generator: Formats the final JSON sequence for the UI.
        └─ Mock Course Data: Local repository for zero-cost path generation.
```
### Architectural Workflow
The diagram below illustrates the high-level request-response flow for generating a personalized learning path.



---

## 2. Core Components

### A. API Layer (FastAPI)
* **RESTful Endpoints:** Handles incoming requests for user registration, skill assessment, and learning path generation.
* **Asynchronous Handling:** Utilizes Python's `async/await` to handle concurrent user requests without blocking the main execution thread.
* **Auto-Documentation:** Integrated Swagger UI (`/docs`) for real-time API testing and endpoint verification.

### B. Hybrid Recommendation Engine
The core logic is divided into two distinct processing tiers to optimize for both accuracy and cost:

1. **Rules-Based Tier (Beginner):**
   - Targets users with "Beginner" proficiency.
   - Utilizes a local **Scoring Algorithm** to map predefined high-quality courses to user goals.
   - **Cost:** ₹0 API overhead.

2. **AI-Inference Tier (Advanced/Expert):**
   - Targets users with specialized or niche skill requirements.
   - Interfaces with **LLM APIs** (e.g., GPT-4o mini / Gemini Flash) to generate non-linear, complex roadmaps.

### C. Data Persistence (PostgreSQL)
* **User Profiles:** Stores demographic data, current skill sets, and career goals.
* **Learning History:** Tracks previously completed modules to ensure the recommendation engine provides "Next-Step" logic rather than repeating known content.

---

## 3. The Scoring Algorithm
The backend calculates the relevance of a course or path using a weighted scoring system:

| Metric | Weight | Description |
| :--- | :--- | :--- |
| **Skill Match** | 40% | Direct correlation between user gap and course content. |
| **Rating/Authority** | 30% | Based on course provider reputation and user feedback. |
| **Difficulty Alignment** | 20% | Matches user proficiency level to course complexity. |
| **Recency** | 10% | Prioritizes up-to-date industry content. |

---

## 4. Scalability Roadmap: Caching Layer
While the current POC implements direct logic execution, the architecture is designed for the future integration of a **Redis Caching Layer**.

* **Mechanism:** The system will hash the `(User_Goal + Current_Skills)` input.
* **Result:** If a matching hash exists in Redis, the system returns the cached roadmap in **<50ms**, bypassing the AI engine and reducing operational costs by ~50%.

---

## 5. Security & Validation
* **Pydantic Schemas:** All incoming JSON payloads are strictly validated against predefined schemas to prevent injection and malformed data entry.
* **CORS Middleware:** Configured to allow secure communication only between the verified Frontend UI and the Backend API.