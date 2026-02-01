"""Simple test for search_jobs tool."""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_search_jobs():
    """Test search_jobs tool directly."""
    from src.linkedin_mcp.services.job_search_service import JobSearchService

    load_dotenv()

    # Initialize service
    service = JobSearchService()

    # Set parameters
    job_title = "Software Engineer"
    location = "Remote"
    limit = 10
    user_credentials = {
        "email": os.getenv("LINKEDIN_EMAIL", "test@example.com"),
        "password": os.getenv("LINKEDIN_PASSWORD", "test_password"),
    }

    # Call search_jobs
    results = service.search_jobs(
        job_title=job_title,
        location=location,
        limit=limit,
        user_credentials=user_credentials,
    )

    print(f"Found {len(results)} jobs")
    return results


if __name__ == "__main__":
    test_search_jobs()
