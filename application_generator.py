"""
Application Generator — creates tailored cover letters and resume notes.
Uses template-based generation (no API required).
"""

import re
from datetime import datetime
from pathlib import Path

from config import APPLICATIONS_DIR, logger


def _sanitize_dirname(name: str) -> str:
    return re.sub(r"[^\w\-]", "_", name.lower()).strip("_")


def _find_matching_skills(parsed_resume: dict, job: dict) -> list[str]:
    """Find skills from the resume that appear in the job description."""
    job_text = (job.get("description", "") + " " + job.get("title", "")).lower()
    all_skills = (
        parsed_resume.get("skills", [])
        + parsed_resume.get("programming_languages", [])
        + parsed_resume.get("technologies", [])
    )
    return [s for s in all_skills if s.lower() in job_text]


def generate_application_materials(job: dict, parsed_resume: dict) -> dict[str, Path]:
    """Generate a tailored cover letter and resume tips for a specific job."""
    company = job.get("company", "Unknown")
    title = job.get("title", "Unknown Role")
    name = parsed_resume.get("name", "Candidate")
    email = parsed_resume.get("email", "")
    matching_skills = _find_matching_skills(parsed_resume, job)
    all_skills = parsed_resume.get("skills", [])[:10]
    projects = parsed_resume.get("projects", [])
    experience = parsed_resume.get("experience", [])

    dir_name = _sanitize_dirname(company)
    out_dir = APPLICATIONS_DIR / dir_name
    out_dir.mkdir(parents=True, exist_ok=True)
    outputs = {}

    # --- Cover Letter ---
    date_str = datetime.now().strftime("%B %d, %Y")
    skills_str = ", ".join(matching_skills[:5]) if matching_skills else ", ".join(all_skills[:5])

    project_paragraph = ""
    if projects:
        p = projects[0]
        project_paragraph = (
            f"\n\nIn my project \"{p.get('name', 'a recent project')}\", "
            f"{p.get('description', 'I applied relevant technical skills')}. "
            f"This experience has prepared me well for the challenges of the {title} role."
        )

    exp_paragraph = ""
    if experience:
        e = experience[0]
        exp_paragraph = (
            f"\n\nIn my role as {e.get('title', 'a team member')} at "
            f"{e.get('company', 'my previous employer')}, "
            f"{e.get('description', 'I contributed to technical projects')}."
        )

    cover_letter = f"""{date_str}

Dear Hiring Manager,

I am writing to express my strong interest in the {title} position at {company}. With my background in {skills_str}, I am confident I would be a valuable addition to your team.{exp_paragraph}{project_paragraph}

My technical skills include {', '.join(all_skills[:8])}. I am eager to apply these skills in a professional environment and continue growing as an engineer.

I would welcome the opportunity to discuss how my skills and enthusiasm align with {company}'s goals. Thank you for considering my application.

Sincerely,
{name}
{email}
"""

    cover_path = out_dir / f"cover_letter_{_sanitize_dirname(title)}.txt"
    cover_path.write_text(cover_letter, encoding="utf-8")
    outputs["cover_letter"] = cover_path
    logger.info(f"Generated cover letter: {cover_path}")

    # --- Resume Tailoring Tips ---
    tips = f"""RESUME TAILORING TIPS FOR: {title} at {company}
{'=' * 60}

MATCHING SKILLS (emphasize these):
{chr(10).join(f'  ✓ {s}' for s in matching_skills) if matching_skills else '  (No direct keyword matches found — review the job description manually)'}

SUGGESTED OBJECTIVE:
  "{parsed_resume.get('experience_level', 'Student').title()}-level {' / '.join(parsed_resume.get('domains', ['technology'])[:2])} "
  "enthusiast seeking to contribute {skills_str} expertise as a {title} at {company}."

SKILLS TO HIGHLIGHT FIRST:
  {', '.join(matching_skills[:6]) if matching_skills else ', '.join(all_skills[:6])}

PROJECTS TO EMPHASIZE:
"""
    for p in projects[:3]:
        tips += f"  - {p.get('name', 'Project')}: {p.get('description', '')[:100]}\n"

    tips += f"""
KEYWORDS TO INCLUDE:
  {', '.join(matching_skills + [title.lower().replace('intern', '').strip()])}

GENERAL TIPS:
  - Quantify achievements (numbers, percentages, scale)
  - Use action verbs: Built, Developed, Implemented, Designed, Optimized
  - Match the job description's language where truthful
  - Put most relevant experience/projects first
"""

    resume_path = out_dir / f"tailored_resume_{_sanitize_dirname(title)}.txt"
    resume_path.write_text(tips, encoding="utf-8")
    outputs["tailored_resume"] = resume_path
    logger.info(f"Generated tailored resume notes: {resume_path}")

    return outputs


def generate_for_top_jobs(jobs: list[dict], parsed_resume: dict, top_n: int = 5) -> list[dict]:
    results = []
    for job in jobs[:top_n]:
        logger.info(f"Generating materials for: {job.get('title')} @ {job.get('company')}")
        paths = generate_application_materials(job, parsed_resume)
        results.append({
            "company": job.get("company"),
            "title": job.get("title"),
            "files": {k: str(v) for k, v in paths.items()},
        })
    return results


if __name__ == "__main__":
    sample_resume = {
        "name": "John Doe",
        "email": "john@example.com",
        "raw_text": "Python developer with ML experience",
        "skills": ["Python", "TensorFlow", "SQL"],
        "programming_languages": ["Python"],
        "technologies": ["TensorFlow"],
        "domains": ["AI"],
        "projects": [{"name": "Chatbot", "description": "Built an NLP chatbot using Python and transformers"}],
        "experience": [{"title": "SWE Intern", "company": "TechCo", "description": "Developed REST APIs"}],
        "experience_level": "student",
    }
    sample_job = {
        "title": "ML Engineer Intern",
        "company": "Acme AI",
        "description": "Build ML pipelines with Python and TensorFlow.",
    }
    result = generate_application_materials(sample_job, sample_resume)
    for k, v in result.items():
        print(f"  {k}: {v}")
