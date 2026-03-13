#!/usr/bin/env python3
"""
AI Internship Discovery System — Main Orchestrator

Usage:
    python main.py                                   # Uses default resume
    python main.py resumes/custom_resume.pdf         # Specify resume
    python main.py --location "San Francisco, CA"    # Filter by location
    python main.py --generate-apps --top 3           # Generate cover letters

Full pipeline:
    1. Parse resume
    2. Infer suitable roles
    3. Search job boards (concurrent)
    4. Score & filter matches
    5. Store in SQLite + Google Sheets
    6. (Optional) Generate tailored application materials
"""

import argparse
import json
import sys
from datetime import datetime

from config import DEFAULT_RESUME, logger
from resume_parser import parse_resume
from role_inference import infer_roles
from job_scraper import search_all_sources
from job_matcher import filter_jobs
from database import insert_jobs, get_stats
from job_tracker import append_jobs_to_sheet
from application_generator import generate_for_top_jobs


def run_pipeline(
    resume_path: str,
    location: str = "",
    generate_apps: bool = False,
    top_n: int = 5,
):
    """Run the full internship discovery pipeline."""
    start_time = datetime.now()
    print("\n" + "=" * 60)
    print("  🎯 AI INTERNSHIP DISCOVERY SYSTEM")
    print("=" * 60)
    print(f"  📄 Resume: {resume_path}")
    print(f"  📍 Location: {location or 'Anywhere'}")
    print(f"  ⏰ Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60 + "\n")

    # Step 1: Parse resume
    print("[1/6] 📄 Parsing resume...")
    parsed_resume = parse_resume(resume_path)
    print(f"  Name: {parsed_resume.get('name', 'Unknown')}")
    print(f"  Skills: {', '.join(parsed_resume.get('skills', [])[:12])}")
    print(f"  Languages: {', '.join(parsed_resume.get('programming_languages', []))}")
    print(f"  Domains: {', '.join(parsed_resume.get('domains', []))}")
    print(f"  Projects: {len(parsed_resume.get('projects', []))}")
    print(f"  Level: {parsed_resume.get('experience_level')}")
    print()

    # Step 2: Infer roles
    print("[2/6] 🔍 Inferring suitable roles...")
    roles = infer_roles(parsed_resume)
    for role in roles:
        print(f"  → {role}")
    print()

    # Step 3: Search for jobs (concurrent)
    print("[3/6] 🌐 Searching job boards (concurrent)...")
    all_jobs = search_all_sources(roles, location)
    print(f"  ✅ Found {len(all_jobs)} total job listings")
    print()

    if not all_jobs:
        print("⚠️  No jobs found. Try broadening your search or checking your internet connection.")
        return

    # Step 4: Score and filter
    print("[4/6] 📊 Scoring jobs against resume...")
    resume_text = parsed_resume.get("raw_text", "")
    matched_jobs = filter_jobs(resume_text, all_jobs)
    print(f"  ✅ {len(matched_jobs)} jobs passed matching threshold")
    print()

    if not matched_jobs:
        print("⚠️  No jobs met the match threshold. Consider lowering MIN_MATCH_SCORE in .env")
        return

    # Step 5: Store results
    print("[5/6] 💾 Storing results...")
    new_db_count = insert_jobs(matched_jobs)
    print(f"  SQLite: {new_db_count} new jobs added")

    sheet_count = append_jobs_to_sheet(matched_jobs)
    if sheet_count > 0:
        print(f"  Google Sheets: {sheet_count} new jobs synced ✅")
    else:
        print(f"  Google Sheets: skipped (not configured)")
    print()

    # Step 6: Generate application materials (optional)
    if generate_apps:
        print(f"[6/6] ✍️  Generating application materials (top {top_n})...")
        app_results = generate_for_top_jobs(matched_jobs, parsed_resume, top_n)
        for r in app_results:
            print(f"  📝 {r['title']} @ {r['company']}:")
            for ftype, fpath in r["files"].items():
                print(f"     → {ftype}: {fpath}")
    else:
        print("[6/6] ⏭️  Skipping application generation (use --generate-apps to enable)")
    print()

    # Summary
    elapsed = (datetime.now() - start_time).total_seconds()
    stats = get_stats()
    print("=" * 60)
    print("  ✅ PIPELINE COMPLETE")
    print("=" * 60)
    print(f"  ⏱️  Time: {elapsed:.1f}s")
    print(f"  🔎 Jobs found: {len(all_jobs)}")
    print(f"  ✅ Jobs matching: {len(matched_jobs)}")
    print(f"  💾 New to DB: {new_db_count}")
    print(f"  📊 Total in DB: {stats['total']}")
    print(f"  📈 Avg score: {stats['avg_score']}")
    print("=" * 60)

    # Print ALL matches grouped by score
    print(f"\n🏆 ALL {len(matched_jobs)} MATCHING JOBS:\n")
    current_score = None
    for i, job in enumerate(matched_jobs, 1):
        score = job['match_score']
        if score != current_score:
            current_score = score
            stars = "★" * score + "☆" * (10 - score)
            print(f"  ── Score {score}/10 {stars} ──")
        print(f"  {i:3}. {job['title']} @ {job['company']}")
        print(f"       📍 {job.get('location', 'N/A')}  |  {job.get('source', '')}")
        if job.get("link"):
            print(f"       🔗 {job['link']}")
        print()


def main():
    parser = argparse.ArgumentParser(
        description="AI Internship Discovery System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                                        # Use default resume
  python main.py resumes/my_resume.pdf                  # Custom resume
  python main.py --location "San Francisco, CA"         # Filter by location
  python main.py --generate-apps --top 3                # Generate cover letters
        """,
    )
    parser.add_argument(
        "resume",
        nargs="?",
        default=DEFAULT_RESUME,
        help=f"Path to resume file (PDF, DOCX, or TXT). Default: {DEFAULT_RESUME}",
    )
    parser.add_argument("--location", default="", help="Location filter for job search")
    parser.add_argument(
        "--generate-apps",
        action="store_true",
        help="Generate tailored cover letters and resume suggestions",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=5,
        help="Number of top jobs to generate application materials for (default: 5)",
    )

    args = parser.parse_args()

    try:
        run_pipeline(
            resume_path=args.resume,
            location=args.location,
            generate_apps=args.generate_apps,
            top_n=args.top,
        )
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
