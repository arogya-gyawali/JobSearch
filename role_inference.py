"""
Role Inference — infers suitable internship roles from parsed resume data.
Uses keyword-based matching (no API required).
"""

import json
from config import logger

# Maps (domain/skill patterns) -> role titles
ROLE_RULES = [
    {
        "triggers": {"python", "machine learning", "tensorflow", "pytorch", "deep learning", "ml", "scikit-learn", "keras"},
        "min_matches": 2,
        "role": "Machine Learning Engineer Intern",
    },
    {
        "triggers": {"python", "ai", "artificial intelligence", "nlp", "natural language processing", "llm", "langchain", "openai", "rag", "transformers"},
        "min_matches": 2,
        "role": "AI Engineer Intern",
    },
    {
        "triggers": {"data science", "pandas", "numpy", "statistics", "data analysis", "jupyter", "matplotlib", "r", "tableau", "power bi"},
        "min_matches": 2,
        "role": "Data Science Intern",
    },
    {
        "triggers": {"data analysis", "sql", "excel", "tableau", "power bi", "analytics", "pandas", "data analytics"},
        "min_matches": 2,
        "role": "Data Analyst Intern",
    },
    {
        "triggers": {"python", "java", "c++", "algorithms", "data structures", "software"},
        "min_matches": 2,
        "role": "Software Engineer Intern",
    },
    {
        "triggers": {"python", "django", "flask", "fastapi", "node.js", "express", "rest", "api", "backend", "postgresql", "mongodb"},
        "min_matches": 2,
        "role": "Backend Engineer Intern",
    },
    {
        "triggers": {"react", "vue", "angular", "javascript", "typescript", "html", "css", "frontend", "front-end", "tailwind"},
        "min_matches": 2,
        "role": "Frontend Engineer Intern",
    },
    {
        "triggers": {"react", "node.js", "javascript", "full-stack", "fullstack", "mongodb", "postgresql", "express"},
        "min_matches": 2,
        "role": "Full Stack Engineer Intern",
    },
    {
        "triggers": {"docker", "kubernetes", "aws", "azure", "gcp", "terraform", "ci/cd", "devops", "jenkins", "linux"},
        "min_matches": 2,
        "role": "DevOps Engineer Intern",
    },
    {
        "triggers": {"aws", "azure", "gcp", "cloud", "lambda", "s3", "ec2", "infrastructure"},
        "min_matches": 2,
        "role": "Cloud Engineer Intern",
    },
    {
        "triggers": {"sql", "etl", "airflow", "spark", "kafka", "data pipeline", "data engineering", "hadoop", "dbt"},
        "min_matches": 2,
        "role": "Data Engineer Intern",
    },
    {
        "triggers": {"android", "ios", "swift", "kotlin", "react native", "flutter", "mobile"},
        "min_matches": 2,
        "role": "Mobile Developer Intern",
    },
    {
        "triggers": {"security", "cybersecurity", "penetration", "vulnerability", "encryption", "networking"},
        "min_matches": 2,
        "role": "Cybersecurity Intern",
    },
    {
        "triggers": {"computer vision", "opencv", "image", "video", "convolutional"},
        "min_matches": 2,
        "role": "Computer Vision Engineer Intern",
    },
    {
        "triggers": {"product", "management", "roadmap", "stakeholder", "agile", "scrum", "jira"},
        "min_matches": 3,
        "role": "Product Management Intern",
    },
]


def infer_roles(parsed_resume: dict) -> list[str]:
    """Infer suitable internship roles from parsed resume data."""
    # Build a set of all keywords from the resume (lowercase)
    resume_keywords = set()
    for field in ["skills", "programming_languages", "technologies", "domains", "keywords"]:
        for item in parsed_resume.get(field, []):
            resume_keywords.add(item.lower())

    # Also add words from raw text for broader matching
    raw_text = parsed_resume.get("raw_text", "").lower()

    roles = []
    for rule in ROLE_RULES:
        matches = sum(
            1 for trigger in rule["triggers"]
            if trigger in resume_keywords or trigger in raw_text
        )
        if matches >= rule["min_matches"]:
            roles.append((rule["role"], matches))

    # Sort by match count (best matches first), deduplicate
    roles.sort(key=lambda x: -x[1])
    role_names = list(dict.fromkeys(r[0] for r in roles))

    # Always include generic SWE intern if we have any programming language
    if "Software Engineer Intern" not in role_names and parsed_resume.get("programming_languages"):
        role_names.append("Software Engineer Intern")

    # Cap at 8 roles
    role_names = role_names[:8]

    logger.info(f"Inferred {len(role_names)} roles: {role_names}")
    return role_names


if __name__ == "__main__":
    sample = {
        "skills": ["Python", "SQL", "Machine Learning", "FastAPI"],
        "programming_languages": ["Python", "C++", "Java"],
        "technologies": ["TensorFlow", "Docker", "PostgreSQL"],
        "domains": ["artificial intelligence", "data science", "web development"],
        "keywords": ["python", "api", "data", "model"],
        "experience_level": "student",
        "raw_text": "Python developer with ML experience, TensorFlow, FastAPI, SQL, REST API",
    }
    roles = infer_roles(sample)
    for r in roles:
        print(f"  - {r}")
