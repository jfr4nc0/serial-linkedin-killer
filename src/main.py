#!/usr/bin/env python3
"""
Main entry point for the Job Application Agent.
Demonstrates how to use the agent with MCP client communication.
"""

import os
import sys
from typing import List

from dotenv import load_dotenv

from src import JobApplicationAgent, JobSearchRequest

load_dotenv(override=True)


def main():
    """Example usage of the JobApplicationAgent."""

    # Configuration
    mcp_server_host = os.getenv("MCP_SERVER_HOST", "localhost")
    mcp_server_port = int(os.getenv("MCP_SERVER_PORT", "3000"))

    # Example job search requests
    job_searches: List[JobSearchRequest] = [
        {
            "job_title": "Software Engineer",
            "location": "Remote",
            "monthly_salary": 5000,
            "limit": 20,
        },
        {
            "job_title": "Software Engineer",
            "location": "San Francisco",
            "monthly_salary": 7000,
            "limit": 15,
        },
    ]

    # User credentials (in production, these should come from secure environment variables)
    user_credentials = {
        "email": os.getenv("LINKEDIN_EMAIL", ""),
        "password": os.getenv("LINKEDIN_PASSWORD", ""),
    }

    if not user_credentials["email"] or not user_credentials["password"]:
        print(
            "Error: LinkedIn credentials not provided. Set LINKEDIN_EMAIL and LINKEDIN_PASSWORD environment variables."
        )
        sys.exit(1)

    # CV data JSON file path
    cv_data_path = os.getenv("CV_DATA_PATH", "./data/cv_data.json")

    if not os.path.exists(cv_data_path):
        print(f"Error: CV data file not found at {cv_data_path}")
        sys.exit(1)

    print("Starting LinkedIn Job Application Agent...")
    print(f"MCP Server Host: {mcp_server_host}")
    print(f"MCP Server Port: {mcp_server_port}")
    print(f"CV Data: {cv_data_path}")
    print(f"Job Searches: {len(job_searches)} searches configured")

    try:
        # Initialize the agent
        agent = JobApplicationAgent(
            server_host=mcp_server_host, server_port=mcp_server_port
        )

        # Run the complete workflow
        result = agent.run(
            job_searches=job_searches,
            user_credentials=user_credentials,
            cv_data_path=cv_data_path,  # Now expecting JSON CV data path
        )

        # Print results
        print("\n" + "=" * 50)
        print("JOB APPLICATION RESULTS")
        print("=" * 50)

        print(f"Status: {result['current_status']}")
        print(f"Total Jobs Found: {result['total_jobs_found']}")
        print(f"Jobs After Filtering: {len(result['filtered_jobs'])}")
        print(f"Total Applications Submitted: {result['total_jobs_applied']}")

        if result.get("errors"):
            print(f"\nErrors Encountered: {len(result['errors'])}")
            for i, error in enumerate(result["errors"], 1):
                print(f"  {i}. {error}")

        print("\nApplication Results:")
        for app_result in result.get("application_results", []):
            status = "✅ SUCCESS" if app_result["success"] else "❌ FAILED"
            print(f"  Job {app_result['id_job']}: {status}")
            if app_result.get("error"):
                print(f"    Error: {app_result['error']}")

        print("\nCV Analysis:")
        cv_analysis = result["cv_analysis"]
        print(f"  Experience Years: {cv_analysis['experience_years']}")
        print(
            f"  Skills: {', '.join(cv_analysis['skills'][:5])}{'...' if len(cv_analysis['skills']) > 5 else ''}"
        )
        print(
            f"  Previous Roles: {', '.join(cv_analysis['previous_roles'][:3])}{'...' if len(cv_analysis['previous_roles']) > 3 else ''}"
        )

        print("\n" + "=" * 50)
        print("Job application workflow completed!")

    except Exception as e:
        print(f"Error: Job application workflow failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
