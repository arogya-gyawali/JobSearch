"""
Resume Parser — extracts structured data from PDF, DOCX, or TXT resumes.
Uses keyword-based NLP extraction (no API required).
"""

import json
import re
from pathlib import Path

import pdfplumber
from docx import Document

from config import logger

# --- Known keywords for extraction ---
PROGRAMMING_LANGUAGES = {
    "python", "java", "javascript", "typescript", "c++", "c#", "c", "go", "golang",
    "rust", "ruby", "php", "swift", "kotlin", "scala", "r", "matlab", "perl",
    "haskell", "lua", "dart", "sql", "html", "css", "bash", "shell", "powershell",
    "objective-c", "assembly", "vhdl", "verilog", "julia", "elixir", "clojure",
}

TECHNOLOGIES = {
    "react", "angular", "vue", "next.js", "nextjs", "node.js", "nodejs", "express",
    "django", "flask", "fastapi", "spring", "spring boot", "rails", "laravel",
    "tensorflow", "pytorch", "keras", "scikit-learn", "sklearn", "pandas", "numpy",
    "opencv", "docker", "kubernetes", "k8s", "aws", "azure", "gcp", "google cloud",
    "firebase", "heroku", "vercel", "netlify", "jenkins", "github actions", "ci/cd",
    "terraform", "ansible", "linux", "unix", "git", "mongodb", "postgresql", "postgres",
    "mysql", "redis", "elasticsearch", "kafka", "rabbitmq", "graphql", "rest",
    "restful", "grpc", "apache", "nginx", "hadoop", "spark", "airflow", "dbt",
    "tableau", "power bi", "streamlit", "gradio", "langchain", "openai", "huggingface",
    "transformers", "bert", "gpt", "llm", "rag", "vector database", "pinecone",
    "chromadb", "supabase", "prisma", "tailwind", "bootstrap", "material ui",
    "figma", "jira", "confluence", "notion", "slack", "agile", "scrum",
    "s3", "lambda", "ec2", "dynamodb", "cloudfront", "sagemaker",
}

DOMAINS = {
    "machine learning": ["machine learning", "ml", "deep learning", "neural network"],
    "artificial intelligence": ["artificial intelligence", "ai", "nlp", "natural language processing", "computer vision"],
    "data science": ["data science", "data analysis", "data analytics", "statistical"],
    "web development": ["web development", "frontend", "front-end", "backend", "back-end", "full-stack", "fullstack"],
    "mobile development": ["mobile", "android", "ios", "react native", "flutter"],
    "cloud computing": ["cloud", "aws", "azure", "gcp", "devops", "infrastructure"],
    "cybersecurity": ["security", "cybersecurity", "penetration", "encryption"],
    "database": ["database", "sql", "nosql", "data engineering", "etl"],
    "systems": ["systems", "distributed", "operating system", "embedded"],
    "game development": ["game", "unity", "unreal", "graphics"],
}


def extract_text_from_pdf(filepath: str) -> str:
    text = ""
    with pdfplumber.open(filepath) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text.strip()


def extract_text_from_docx(filepath: str) -> str:
    doc = Document(filepath)
    return "\n".join(para.text for para in doc.paragraphs if para.text.strip())


def extract_text_from_txt(filepath: str) -> str:
    return Path(filepath).read_text(encoding="utf-8").strip()


def extract_text(filepath: str) -> str:
    filepath = str(filepath)
    ext = Path(filepath).suffix.lower()
    extractors = {
        ".pdf": extract_text_from_pdf,
        ".docx": extract_text_from_docx,
        ".txt": extract_text_from_txt,
    }
    extractor = extractors.get(ext)
    if not extractor:
        raise ValueError(f"Unsupported file format: {ext}. Use PDF, DOCX, or TXT.")
    text = extractor(filepath)
    if not text:
        raise ValueError(f"Could not extract any text from {filepath}")
    logger.info(f"Extracted {len(text)} characters from {filepath}")
    return text


def _extract_email(text: str) -> str | None:
    match = re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text)
    return match.group(0) if match else None


def _extract_phone(text: str) -> str | None:
    match = re.search(r"[\(]?\d{3}[\)]?[-.\s]?\d{3}[-.\s]?\d{4}", text)
    return match.group(0) if match else None


def _extract_name(text: str) -> str:
    """Best-effort: first non-empty line that looks like a name."""
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        # Skip lines that look like addresses, emails, URLs
        if "@" in line or "http" in line or line.startswith("+"):
            continue
        # A name line is usually short and has mostly alpha chars
        if len(line) < 50 and re.match(r"^[A-Za-z\s\.\-']+$", line):
            return line
    return "Unknown"


def _find_keywords(text: str, keyword_set: set) -> list[str]:
    """Find which keywords from a set appear in the text."""
    text_lower = text.lower()
    found = []
    # Sort by length descending so "spring boot" matches before "spring"
    for kw in sorted(keyword_set, key=len, reverse=True):
        if kw.lower() in text_lower:
            found.append(kw)
    return found


def _find_domains(text: str) -> list[str]:
    text_lower = text.lower()
    found = []
    for domain, keywords in DOMAINS.items():
        if any(kw in text_lower for kw in keywords):
            found.append(domain)
    return found


def _extract_sections(text: str) -> dict[str, str]:
    """Split resume into sections based on common headers (fuzzy matching)."""
    # Map patterns to normalized section names
    section_patterns = {
        "education": ["education", "education & certifications", "education and certifications"],
        "experience": ["experience", "work experience", "professional experience",
                       "leadership & campus experience", "leadership & experience",
                       "leadership experience", "campus experience"],
        "projects": ["projects", "projects & hackathons", "projects and hackathons",
                     "personal projects", "academic projects", "technical projects"],
        "skills": ["skills", "technical skills", "core skills", "technologies",
                   "tools & technologies", "core strengths"],
        "certifications": ["certifications", "certificates", "licenses"],
        "summary": ["summary", "profile", "objective", "professional summary", "about"],
        "awards": ["awards", "honors", "achievements"],
        "activities": ["activities", "extracurricular", "volunteer", "involvement",
                       "leadership", "organizations"],
    }

    # Build reverse lookup: lowercase header text → normalized name
    header_map = {}
    for normalized, variants in section_patterns.items():
        for v in variants:
            header_map[v] = normalized

    sections = {}
    lines = text.split("\n")
    current_section = "header"
    current_content = []

    for line in lines:
        stripped = line.strip().lower().rstrip(": ")
        # Check exact and fuzzy match
        matched_section = header_map.get(stripped)
        if not matched_section:
            # Try partial match — if the line IS a section header
            for header_text, norm in header_map.items():
                if stripped == header_text or (len(stripped) < 60 and stripped.startswith(header_text)):
                    matched_section = norm
                    break

        if matched_section:
            sections[current_section] = "\n".join(current_content)
            current_section = matched_section
            current_content = []
        else:
            current_content.append(line)

    sections[current_section] = "\n".join(current_content)
    return sections


def _extract_projects(sections: dict) -> list[dict]:
    """Extract projects from the projects section."""
    projects_text = sections.get("projects", "")
    if not projects_text:
        return []

    projects = []
    lines = projects_text.strip().split("\n")
    current_project = None

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # A bullet/dash line is a description of the current project
        is_bullet = stripped.startswith("-") or stripped.startswith("•") or stripped.startswith("●")

        if is_bullet and current_project:
            desc_line = stripped.lstrip("-•● ").strip()
            if current_project["description"]:
                current_project["description"] += " " + desc_line
            else:
                current_project["description"] = desc_line
        elif not is_bullet:
            # This is a project title line
            if current_project:
                projects.append(current_project)
            # Try to split "Project Name — Context (Year)" or "Project Name (Tech1, Tech2)"
            # Remove date/year parenthetical
            tech_match = re.search(r"\(([^)]*(?:20\d{2})[^)]*)\)", stripped)
            year_str = ""
            if tech_match:
                year_str = tech_match.group(1)
                stripped_clean = stripped.replace(tech_match.group(0), "").strip()
            else:
                stripped_clean = stripped

            tech_match2 = re.search(r"\(([^)]+)\)", stripped_clean)
            techs = [t.strip() for t in tech_match2.group(1).split(",")] if tech_match2 else []
            name = re.sub(r"\([^)]+\)", "", stripped_clean).strip().rstrip("—–- ")
            current_project = {"name": name, "description": "", "technologies": techs, "year": year_str}

    if current_project:
        projects.append(current_project)
    return projects


def _extract_experience(sections: dict) -> list[dict]:
    """Extract work experience entries."""
    exp_text = sections.get("experience", "") or sections.get("work experience", "")
    if not exp_text:
        return []

    experiences = []
    lines = exp_text.strip().split("\n")
    current_exp = None

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Look for lines with " — " or " - " or " | " separators (Company — Title pattern)
        if (not line.startswith(" ") and not line.startswith("-") and not line.startswith("•")
                and len(stripped) < 120):
            # Check if it looks like a job title line
            separators = [" — ", " - ", " | ", ", "]
            for sep in separators:
                if sep in stripped:
                    parts = stripped.split(sep, 1)
                    if current_exp:
                        experiences.append(current_exp)
                    current_exp = {
                        "company": parts[0].strip(),
                        "title": parts[1].strip() if len(parts) > 1 else "",
                        "duration": "",
                        "description": "",
                    }
                    break
            else:
                # Might be a duration line or continuation
                if current_exp and re.search(r"\d{4}", stripped):
                    current_exp["duration"] = stripped
                elif not current_exp:
                    current_exp = {"company": stripped, "title": "", "duration": "", "description": ""}
        elif current_exp:
            desc_line = stripped.lstrip("-•● ")
            if current_exp["description"]:
                current_exp["description"] += " " + desc_line
            else:
                current_exp["description"] = desc_line

    if current_exp:
        experiences.append(current_exp)
    return experiences


def _extract_education(sections: dict) -> list[dict]:
    """Extract education entries."""
    edu_text = sections.get("education", "")
    if not edu_text:
        return []

    education = []
    lines = edu_text.strip().split("\n")

    entry = {"institution": "", "degree": "", "field": "", "gpa": None, "graduation": ""}
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # GPA
        gpa_match = re.search(r"GPA[:\s]*(\d+\.\d+)", stripped, re.IGNORECASE)
        if gpa_match:
            entry["gpa"] = gpa_match.group(1)

        # Graduation date
        grad_match = re.search(r"(Expected\s+)?(May|June|December|Spring|Fall|Summer|January)?\s*\d{4}", stripped, re.IGNORECASE)
        if grad_match:
            entry["graduation"] = grad_match.group(0).strip()

        # Degree
        degree_match = re.search(r"(Bachelor|Master|Ph\.?D|Associate|B\.?S\.?|M\.?S\.?|B\.?A\.?|M\.?A\.?)[^,\n]*", stripped, re.IGNORECASE)
        if degree_match:
            entry["degree"] = degree_match.group(0).strip()

        # Institution — typically the first substantial line
        if not entry["institution"] and len(stripped) > 5 and not stripped.startswith("-"):
            entry["institution"] = stripped

        # Field
        field_match = re.search(r"in\s+([A-Za-z\s]+?)(?:\s*,|\s*$|\s*GPA)", stripped, re.IGNORECASE)
        if field_match:
            entry["field"] = field_match.group(1).strip()

    if entry["institution"]:
        education.append(entry)
    return education


def _infer_experience_level(text: str, experience: list) -> str:
    text_lower = text.lower()
    # Check for student indicators first (strongest signal for internship seekers)
    if any(kw in text_lower for kw in ["student", "expected graduation", "bachelor", "pursuing",
                                         "university", "college", "coursework", "gpa"]):
        return "student"
    if any(kw in text_lower for kw in ["senior engineer", "lead engineer", "principal", "staff engineer", "director"]):
        return "senior"
    if any(kw in text_lower for kw in ["mid-level", "3+ years", "4+ years", "5+ years"]):
        return "mid-level"
    if len(experience) >= 3:
        return "mid-level"
    if len(experience) >= 1:
        return "entry-level"
    return "student"


def parse_resume(filepath: str) -> dict:
    """Parse a resume file into structured JSON using keyword extraction."""
    raw_text = extract_text(filepath)
    sections = _extract_sections(raw_text)

    languages = _find_keywords(raw_text, PROGRAMMING_LANGUAGES)
    technologies = _find_keywords(raw_text, TECHNOLOGIES)
    domains = _find_domains(raw_text)
    projects = _extract_projects(sections)
    experience = _extract_experience(sections)
    education = _extract_education(sections)

    # Skills = languages + technologies + any other keywords
    skills = list(set(languages + technologies))

    # Extract additional keywords (words that appear frequently)
    words = re.findall(r"\b[A-Za-z][\w.+#-]*\b", raw_text)
    word_freq = {}
    for w in words:
        wl = w.lower()
        if len(wl) > 2 and wl not in {"the", "and", "for", "with", "from", "that", "this", "are", "was", "were", "been", "have", "has", "had"}:
            word_freq[wl] = word_freq.get(wl, 0) + 1
    keywords = [w for w, c in sorted(word_freq.items(), key=lambda x: -x[1])[:30] if c >= 2]

    parsed = {
        "name": _extract_name(raw_text),
        "email": _extract_email(raw_text),
        "phone": _extract_phone(raw_text),
        "skills": skills,
        "programming_languages": languages,
        "technologies": technologies,
        "projects": projects,
        "education": education,
        "experience": experience,
        "certifications": [],
        "keywords": keywords,
        "domains": domains,
        "experience_level": _infer_experience_level(raw_text, experience),
        "raw_text": raw_text,
        "source_file": str(filepath),
    }

    logger.info(
        f"Parsed resume: {parsed['name']} — "
        f"{len(skills)} skills, {len(projects)} projects, "
        f"{len(experience)} experience entries"
    )
    return parsed


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python resume_parser.py <resume_file>")
        sys.exit(1)
    result = parse_resume(sys.argv[1])
    # Don't print raw_text in output
    display = {k: v for k, v in result.items() if k != "raw_text"}
    print(json.dumps(display, indent=2, default=str))
