#!/usr/bin/env python3
"""
Simple test script for JobApplicationService debugging
"""

import json
import os
import sys

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.linkedin_mcp.linkedin.model.types import ApplicationRequest
from src.linkedin_mcp.linkedin.services.job_application_service import JobApplicationService


def main():
    # Test data
    applications = [
        ApplicationRequest(job_id=4309119518, monthly_salary=4000),
        ApplicationRequest(job_id=4308566123, monthly_salary=4500),
    ]

    # Load CV analysis from file
    cv_file_path = os.getenv("CV_FILE_PATH")
    if not cv_file_path:
        cv_file_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data",
            "cv_data.json",
        )

    with open(cv_file_path, "r", encoding="utf-8") as f:
        cv_analysis = json.load(f)

    user_credentials = {
        "email": os.getenv("LINKEDIN_EMAIL"),
        "password": os.getenv("LINKEDIN_PASSWORD"),
    }

    # Initialize and run
    service = JobApplicationService("chrome")

    try:
        results = service.apply_to_jobs(applications, cv_analysis, user_credentials)

        print(f"Results: {len(results)} applications processed")
        for result in results:
            status = "SUCCESS" if result["success"] else "FAILED"
            print(f"Job {result['id_job']}: {status}")
            if not result["success"] and result.get("error"):
                print(f"  Error: {result['error']}")

    except Exception as e:
        print(f"Error: {str(e)}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
