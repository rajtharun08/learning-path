## System Architecture

### Phase 1: Onboarding and Unverified Profiling

The onboarding system captures user intent while maintaining strong data
integrity.

**Role Selection** - Users select a specific professional target (e.g.,
Backend Developer).

**Skill Entry** - Users list tools and technologies they know (e.g.,
Python, SQL). - Each skill initially receives an **Unverified badge**.

**System Logic** - Skills are acknowledged but not credited until proven
through assessment.

**Roadmap Lock** - Advanced roadmaps and certificates remain locked
until diagnostic verification occurs.

------------------------------------------------------------------------

### Phase 2: Diagnostic Assessment (Entry Gate)

Before generating a learning path, the platform performs a detailed
diagnostic evaluation.

**Diagnostic Test** - 15 questions total. - 5 targeted questions per
core skill.

**Competency Profile** - Instead of a single percentage score, the
system generates a skill-by-skill competency breakdown.

**Gap Identification** - The system detects the weakest link that blocks
the user's progression. - Example: - Python: 80% - SQL: 30% - SQL
becomes the **primary skill gap** to bridge.

------------------------------------------------------------------------

### Phase 3: Adaptive Roadmap Generation

The backend uses diagnostic data to generate a personalized learning
path that respects the user's existing knowledge.

**Handling Strengths** - Strong skills are marked as **Skipped or
Completed**. - Content remains accessible in **Review Mode**.

**Handling Gaps** - Weak skills become **Bridge Requirements**.

**Resource Ranking Algorithm**

\[ Score = (Relevance × 0.40) + (Difficulty × 0.25) + (Rating × 0.20) +
(Authority × 0.15) \]

**Path Placement** - Users begin in the **Beginner Path** until all
skill gaps are verified.

------------------------------------------------------------------------

### Phase 4: Learning and Delta Validation

Progress is measured through demonstrated mastery rather than passive
engagement.

**Learning History Tracker** - Tracks user interaction with curated
learning resources.

**Delta Trigger** - Completion of the final resource in a gap module
unlocks a **Delta Test**.

**Delta Test** - A short five-question technical validation.

**Skill Verification** - Passing the Delta Test changes skill status
from: - Unverified → Verified

------------------------------------------------------------------------

### Phase 5: Final Tier Assessment (Certification Gate)

Once all gaps are bridged, users must demonstrate integrated competency.

**Holistic Evaluation** - A final assessment evaluates how well skills
work together.

**Applied Synthesis** - Example scenario: - Writing a Python script that
queries a SQL database.

**Certification** - Successful completion awards the **Beginner Tier
Certificate**.

------------------------------------------------------------------------

### Phase 6: Milestone Choice 

To prevent learning fatigue, the system introduces a voluntary pause
point after certification.

**User Autonomy** Users choose one of three options:

1.  Proceed to the Intermediate Tier.
2.  Continue practicing within the current tier through advanced
    beginner projects.
3.  Pause learning while preserving progress.

**Soft Unlock** - The Intermediate tier becomes visible and previewable
in **Discovery Mode**.

------------------------------------------------------------------------

### Phase 7: Tier Evolution and Active Review

The platform evolves alongside the user's professional growth.

**Live Roadmap Recalculation** - When users enter the next tier, a new
adaptive roadmap is generated based on current competency.

**Review Library** - All verified Beginner modules are archived into a
**Review Library**.

**Knowledge Retention** - Key takeaway summaries allow users to revisit
foundational concepts while progressing into advanced material.

------------------------------------------------------------------------

## Key Design Principles

**Skill Verification Over Content Completion** Learning progress is
measured by competency validation rather than time spent consuming
content.

**Adaptive Personalization** Learning paths dynamically adjust based on
diagnostic results and ongoing assessments.

**Gap-Focused Learning** The system prioritizes fixing weaknesses rather
than repeating already mastered topics.

**Progressive Certification** Each tier validates the user's ability to
apply skills in realistic professional scenarios.

------------------------------------------------------------------------

