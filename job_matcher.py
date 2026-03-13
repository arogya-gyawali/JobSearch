"""
Job Matcher — scores job listings against a resume using keyword overlap.
No API required.
"""

import re
from config import MIN_MATCH_SCORE, logger


def _tokenize(text: str) -> set[str]:
    """Extract lowercase tokens from text."""
    return set(re.findall(r"\b[a-z][\w.+#-]*\b", text.lower()))


def score_job_match(resume_text: str, job: dict) -> int:
    """Score how well a job matches the resume. Returns 1-10."""
    resume_tokens = _tokenize(resume_text)

    job_text = " ".join([
        job.get("title", ""),
        job.get("description", ""),
        job.get("company", ""),
    ])
    job_tokens = _tokenize(job_text)

    if not job_tokens:
        return 3  # No description available, give benefit of doubt

    # Calculate overlap
    common = resume_tokens & job_tokens
    # Filter out very common words
    stop_words = {"the", "and", "for", "with", "from", "that", "this", "are", "was",
                  "our", "you", "your", "will", "have", "has", "been", "can", "all",
                  "about", "team", "work", "working", "experience", "role", "join",
                  "looking", "company", "position", "opportunity", "including", "also",
                  "new", "help", "use", "using", "build", "building", "strong", "able"}
    meaningful_common = common - stop_words

    # Score components
    overlap_ratio = len(meaningful_common) / max(len(job_tokens - stop_words), 1)

    # Bonus for key tech terms matching
    tech_terms = {"python", "java", "javascript", "typescript", "react", "node.js",
                  "sql", "aws", "docker", "kubernetes", "tensorflow", "pytorch",
                  "django", "flask", "fastapi", "spring", "angular", "vue",
                  "machine", "learning", "data", "science", "ai", "ml",
                  "c++", "go", "rust", "ruby", "swift", "kotlin"}
    tech_overlap = len(meaningful_common & tech_terms)

    # Title-based scoring (important when descriptions are sparse/missing)
    title_lower = job.get("title", "").lower()
    title_bonus = 0
    if "intern" in title_lower:
        title_bonus += 2
    if any(kw in title_lower for kw in ["software", "engineer", "developer", "swe"]):
        title_bonus += 2
    if any(kw in title_lower for kw in ["data", "ml", "ai", "machine learning", "backend",
                                         "frontend", "full stack", "fullstack", "cloud", "devops"]):
        title_bonus += 2

    # Resume-role alignment: check if title keywords appear in resume
    title_words = set(title_lower.split()) - stop_words - {"intern", "internship", "-", "–", "@", "summer", "2026", "2025"}
    resume_title_overlap = len(title_words & resume_tokens)
    title_relevance = min(3, resume_title_overlap)  # cap at 3

    # Calculate final score — weighted toward title matching for sparse listings
    raw_score = (overlap_ratio * 3) + (tech_overlap * 0.5) + title_bonus + title_relevance
    score = max(1, min(10, round(raw_score)))

    return score


def filter_jobs(resume_text: str, jobs: list[dict]) -> list[dict]:
    """Score all jobs and return only those meeting the minimum threshold."""
    scored_jobs = []

    for i, job in enumerate(jobs):
        logger.info(f"Scoring job {i + 1}/{len(jobs)}: {job.get('title')} @ {job.get('company')}")
        score = score_job_match(resume_text, job)
        job["match_score"] = score

        if score >= MIN_MATCH_SCORE:
            scored_jobs.append(job)
            logger.info(f"  ✓ Score: {score}/10 — KEPT")
        else:
            logger.info(f"  ✗ Score: {score}/10 — filtered out")

    scored_jobs.sort(key=lambda j: j["match_score"], reverse=True)
    logger.info(
        f"Matching complete: {len(scored_jobs)}/{len(jobs)} jobs passed "
        f"(threshold: {MIN_MATCH_SCORE})"
    )
    return scored_jobs


if __name__ == "__main__":
    sample_resume = "Python developer with ML experience, TensorFlow, FastAPI, SQL, REST APIs, Docker, AWS"
    sample_jobs = [
        {
            "title": "ML Engineer Intern",
            "company": "Acme AI",
            "location": "SF",
            "description": "Build ML pipelines with Python and TensorFlow. Deploy on AWS with Docker.",
        },
        {
            "title": "Marketing Intern",
            "company": "BrandCo",
            "location": "NYC",
            "description": "Social media campaigns and content creation for brand awareness.",
        },
    ]
    results = filter_jobs(sample_resume, sample_jobs)
    for j in results:
        print(f"  {j['title']} @ {j['company']} — Score: {j['match_score']}")
