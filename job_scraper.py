"""
Job Scraper — searches multiple job boards for internship listings.
Uses requests + BeautifulSoup with concurrent scraping for speed.
"""

import random
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from urllib.parse import quote_plus, urljoin

import requests
from bs4 import BeautifulSoup

from config import (
    MAX_JOBS_PER_SOURCE,
    REQUEST_DELAY,
    REQUEST_TIMEOUT,
    USER_AGENT,
    logger,
)


def _get_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
    )
    return session


def _delay():
    time.sleep(random.uniform(*REQUEST_DELAY))


def _safe_get(session: requests.Session, url: str) -> BeautifulSoup | None:
    try:
        resp = session.get(url, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "html.parser")
    except requests.RequestException as e:
        logger.warning(f"Failed to fetch {url}: {e}")
        return None


# ---------------------------------------------------------------------------
# LinkedIn (public listings) — WORKING SOURCE
# ---------------------------------------------------------------------------
def scrape_linkedin(role: str, location: str = "") -> list[dict]:
    """Scrape LinkedIn public job listings."""
    jobs = []
    session = _get_session()
    query = quote_plus(f"{role} internship")
    url = f"https://www.linkedin.com/jobs/search/?keywords={query}&f_E=1&f_TPR=r604800"

    soup = _safe_get(session, url)
    if not soup:
        return jobs

    cards = soup.select("div.base-card, li.result-card")
    for card in cards[:MAX_JOBS_PER_SOURCE]:
        try:
            title_el = card.select_one("h3.base-search-card__title")
            company_el = card.select_one("h4.base-search-card__subtitle a")
            location_el = card.select_one("span.job-search-card__location")
            link_el = card.select_one("a.base-card__full-link")
            date_el = card.select_one("time")

            title = title_el.get_text(strip=True) if title_el else None
            if not title:
                continue

            jobs.append(
                {
                    "title": title,
                    "company": company_el.get_text(strip=True) if company_el else "Unknown",
                    "location": location_el.get_text(strip=True) if location_el else "Remote/Unknown",
                    "type": "Internship",
                    "salary": None,
                    "description": "",
                    "link": link_el["href"] if link_el else "",
                    "date_posted": date_el.get("datetime", "")[:10] if date_el else datetime.now().strftime("%Y-%m-%d"),
                    "source": "LinkedIn",
                }
            )
        except Exception as e:
            logger.debug(f"LinkedIn parse error: {e}")
            continue

    logger.info(f"LinkedIn: found {len(jobs)} jobs for '{role}'")
    return jobs


# ---------------------------------------------------------------------------
# GitHub Jobs / YC (Hacker News Who's Hiring) — WORKING SOURCE
# ---------------------------------------------------------------------------
def scrape_hn_whoishiring(role: str) -> list[dict]:
    """Scrape Hacker News 'Who is Hiring' threads via Algolia API."""
    jobs = []
    session = _get_session()

    # Search for the latest Who is Hiring thread
    search_url = (
        "https://hn.algolia.com/api/v1/search?"
        "query=Ask%20HN%3A%20Who%20is%20hiring&tags=story&hitsPerPage=1"
    )
    try:
        resp = session.get(search_url, timeout=REQUEST_TIMEOUT)
        data = resp.json()
        if not data.get("hits"):
            return jobs
        thread_id = data["hits"][0]["objectID"]
    except Exception as e:
        logger.warning(f"HN search failed: {e}")
        return jobs

    # Fetch comments
    comments_url = f"https://hn.algolia.com/api/v1/items/{thread_id}"
    try:
        resp = session.get(comments_url, timeout=REQUEST_TIMEOUT)
        thread = resp.json()
    except Exception as e:
        logger.warning(f"HN thread fetch failed: {e}")
        return jobs

    role_lower = role.lower()
    keywords = role_lower.split()

    for child in thread.get("children", [])[:200]:
        text = child.get("text", "")
        if not text:
            continue
        text_lower = text.lower()

        # Check if the posting is relevant
        if not any(kw in text_lower for kw in keywords):
            continue
        if "intern" not in text_lower and "entry" not in text_lower and "junior" not in text_lower:
            continue

        # Parse the first line as company/title
        soup = BeautifulSoup(text, "html.parser")
        plain = soup.get_text("\n", strip=True)
        lines = plain.split("\n")
        first_line = lines[0] if lines else ""

        # Try to extract company name (usually first part before |)
        parts = re.split(r"\s*\|\s*", first_line)
        company = parts[0].strip() if parts else "Unknown"
        title = parts[1].strip() if len(parts) > 1 else role
        loc = parts[2].strip() if len(parts) > 2 else "Unknown"

        # Find URLs in the text
        urls = re.findall(r'href="(https?://[^"]+)"', text)
        link = urls[0] if urls else f"https://news.ycombinator.com/item?id={child.get('id', '')}"

        jobs.append(
            {
                "title": title,
                "company": company,
                "location": loc,
                "type": "Internship",
                "salary": None,
                "description": plain[:500],
                "link": link,
                "date_posted": datetime.now().strftime("%Y-%m-%d"),
                "source": "HN Who's Hiring",
            }
        )

        if len(jobs) >= MAX_JOBS_PER_SOURCE:
            break

    logger.info(f"HN: found {len(jobs)} jobs for '{role}'")
    return jobs


# ---------------------------------------------------------------------------
# Greenhouse boards — API-BASED (more reliable than HTML scraping)
# ---------------------------------------------------------------------------
GREENHOUSE_COMPANIES = [
    "airbnb", "figma", "notion", "stripe", "databricks", "anthropic",
    "openai", "vercel", "retool", "dbtlabs", "hashicorp", "datadog",
    "airtable", "plaid", "brex", "ramp", "rippling", "gusto",
]


def scrape_greenhouse(role: str) -> list[dict]:
    """Scrape Greenhouse job boards using their JSON API."""
    jobs = []
    session = _get_session()
    role_lower = role.lower()

    for company in GREENHOUSE_COMPANIES:
        # Use the JSON API endpoint — much more reliable
        url = f"https://boards-api.greenhouse.io/v1/boards/{company}/jobs"
        try:
            resp = session.get(url, timeout=REQUEST_TIMEOUT)
            if resp.status_code != 200:
                continue
            data = resp.json()
        except Exception as e:
            logger.debug(f"Greenhouse API error for {company}: {e}")
            continue

        for posting in data.get("jobs", []):
            title = posting.get("title", "")
            title_lower = title.lower()

            if "intern" not in title_lower:
                continue
            if not any(kw in title_lower for kw in role_lower.split()):
                if "engineer" not in title_lower and "developer" not in title_lower and "analyst" not in title_lower:
                    continue

            loc_data = posting.get("location", {})
            loc = loc_data.get("name", "Unknown") if isinstance(loc_data, dict) else str(loc_data)

            jobs.append(
                {
                    "title": title,
                    "company": company.replace("-", " ").title(),
                    "location": loc,
                    "type": "Internship",
                    "salary": None,
                    "description": "",
                    "link": posting.get("absolute_url", ""),
                    "date_posted": (posting.get("updated_at") or "")[:10] or datetime.now().strftime("%Y-%m-%d"),
                    "source": "Greenhouse",
                }
            )

        if len(jobs) >= MAX_JOBS_PER_SOURCE:
            break

    logger.info(f"Greenhouse: found {len(jobs)} jobs for '{role}'")
    return jobs


# ---------------------------------------------------------------------------
# Lever boards — API-BASED
# ---------------------------------------------------------------------------
LEVER_COMPANIES = [
    "netflix", "coinbase", "verkada", "anduril", "cloudflare",
    "scale", "snorkelai", "weights-and-biases", "figma",
]


def scrape_lever(role: str) -> list[dict]:
    """Scrape Lever job boards using their JSON API."""
    jobs = []
    session = _get_session()
    role_lower = role.lower()

    for company in LEVER_COMPANIES:
        url = f"https://api.lever.co/v0/postings/{company}?mode=json"
        try:
            resp = session.get(url, timeout=REQUEST_TIMEOUT)
            if resp.status_code != 200:
                continue
            data = resp.json()
        except Exception as e:
            logger.debug(f"Lever API error for {company}: {e}")
            continue

        for posting in data:
            title = posting.get("text", "")
            title_lower = title.lower()

            if "intern" not in title_lower:
                continue

            categories = posting.get("categories", {})
            loc = categories.get("location", "Unknown")

            jobs.append(
                {
                    "title": title,
                    "company": company.replace("-", " ").title(),
                    "location": loc,
                    "type": "Internship",
                    "salary": None,
                    "description": posting.get("descriptionPlain", "")[:500],
                    "link": posting.get("hostedUrl", ""),
                    "date_posted": datetime.now().strftime("%Y-%m-%d"),
                    "source": "Lever",
                }
            )

        if len(jobs) >= MAX_JOBS_PER_SOURCE:
            break

    logger.info(f"Lever: found {len(jobs)} jobs for '{role}'")
    return jobs


# ---------------------------------------------------------------------------
# SimplifyJobs GitHub — curated internship list
# ---------------------------------------------------------------------------
def scrape_simplify_github() -> list[dict]:
    """Fetch curated internship listings from SimplifyJobs GitHub repo."""
    jobs = []
    session = _get_session()

    # This repo maintains a curated, regularly-updated list of internships
    url = "https://raw.githubusercontent.com/SimplifyJobs/Summer2025-Internships/dev/README.md"
    try:
        resp = session.get(url, timeout=REQUEST_TIMEOUT)
        if resp.status_code != 200:
            # Try alternative URL
            url = "https://raw.githubusercontent.com/SimplifyJobs/Summer2025-Internships/dev/.github/scripts/listings.json"
            resp = session.get(url, timeout=REQUEST_TIMEOUT)
            if resp.status_code == 200:
                try:
                    data = resp.json()
                    for item in data[:MAX_JOBS_PER_SOURCE * 2]:
                        if not item.get("active", True):
                            continue
                        title = item.get("title", "")
                        if not title:
                            continue
                        locations = item.get("locations", [])
                        loc_str = ", ".join(locations[:3]) if locations else "Various"
                        jobs.append({
                            "title": title,
                            "company": item.get("company_name", "Unknown"),
                            "location": loc_str,
                            "type": "Internship",
                            "salary": None,
                            "description": "",
                            "link": item.get("url", ""),
                            "date_posted": (item.get("date_posted") or datetime.now().strftime("%Y-%m-%d"))[:10],
                            "source": "SimplifyJobs",
                        })
                except Exception:
                    pass
            logger.info(f"SimplifyJobs: found {len(jobs)} jobs")
            return jobs

        # Parse markdown table
        text = resp.text
        lines = text.split("\n")
        in_table = False
        for line in lines:
            if "| Company" in line and "Role" in line:
                in_table = True
                continue
            if in_table and line.startswith("|---"):
                continue
            if in_table and line.startswith("|"):
                cols = [c.strip() for c in line.split("|")[1:-1]]
                if len(cols) >= 4:
                    company_md = cols[0]
                    role_md = cols[1]
                    loc_md = cols[2]

                    # Extract company name (remove markdown links)
                    company = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", company_md).strip()
                    title = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", role_md).strip()
                    location = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", loc_md).strip()

                    # Extract link
                    link_match = re.search(r"\[.*?\]\((https?://[^)]+)\)", role_md)
                    link = link_match.group(1) if link_match else ""

                    if "↳" in company or not title:
                        continue

                    jobs.append({
                        "title": title,
                        "company": company or "Unknown",
                        "location": location,
                        "type": "Internship",
                        "salary": None,
                        "description": "",
                        "link": link,
                        "date_posted": datetime.now().strftime("%Y-%m-%d"),
                        "source": "SimplifyJobs",
                    })

                    if len(jobs) >= MAX_JOBS_PER_SOURCE * 2:
                        break
            elif in_table and not line.startswith("|"):
                in_table = False

    except Exception as e:
        logger.warning(f"SimplifyJobs fetch failed: {e}")

    logger.info(f"SimplifyJobs: found {len(jobs)} jobs")
    return jobs


# ---------------------------------------------------------------------------
# Public API: search all sources — CONCURRENT
# ---------------------------------------------------------------------------
def _scrape_role(role: str, location: str) -> list[dict]:
    """Scrape all sources for a single role. Used for concurrent execution."""
    jobs = []
    jobs.extend(scrape_linkedin(role, location))
    jobs.extend(scrape_hn_whoishiring(role))
    jobs.extend(scrape_greenhouse(role))
    jobs.extend(scrape_lever(role))
    return jobs


def search_all_sources(roles: list[str], location: str = "") -> list[dict]:
    """Search all job sources for given roles concurrently. Returns deduplicated results."""
    all_jobs = []

    # Limit to top 4 roles for speed
    search_roles = roles[:4]
    logger.info(f"Searching for {len(search_roles)} roles concurrently: {search_roles}")

    # Scrape role-specific sources concurrently
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(_scrape_role, role, location): role
            for role in search_roles
        }
        for future in as_completed(futures):
            role = futures[future]
            try:
                jobs = future.result()
                all_jobs.extend(jobs)
                logger.info(f"Completed search for '{role}': {len(jobs)} jobs")
            except Exception as e:
                logger.error(f"Error searching for '{role}': {e}")

    # Also grab curated listings (source-wide, not role-specific)
    try:
        curated = scrape_simplify_github()
        all_jobs.extend(curated)
    except Exception as e:
        logger.warning(f"SimplifyJobs failed: {e}")

    # Deduplicate by link
    seen_links = set()
    unique_jobs = []
    for job in all_jobs:
        link = job.get("link", "")
        if link and link in seen_links:
            continue
        if link:
            seen_links.add(link)
        unique_jobs.append(job)

    logger.info(f"Total unique jobs found: {len(unique_jobs)}")
    return unique_jobs


if __name__ == "__main__":
    jobs = search_all_sources(["Software Engineer Intern", "Data Science Intern"])
    for j in jobs[:5]:
        print(f"  {j['title']} @ {j['company']} ({j['source']})")
    print(f"  ... {len(jobs)} total")
