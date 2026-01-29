"""
CV Data Loader - Loads structured CV data from JSON file.
Replaces PDF CV processing with structured JSON data.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List


def load_cv_data(cv_file_path: str = None) -> Dict[str, Any]:
    """
    Load CV data from JSON file.

    Args:
        cv_file_path: Path to CV JSON file (defaults to ./data/cv_data.json)

    Returns:
        Dictionary containing structured CV data

    Raises:
        FileNotFoundError: If CV JSON file not found
        ValueError: If CV JSON file is invalid
    """
    # Default to data/cv_data.json if not specified
    if cv_file_path is None:
        cv_file_path = os.path.join(os.getcwd(), "data", "cv_data.json")

    cv_path = Path(cv_file_path)

    if not cv_path.exists():
        raise FileNotFoundError(f"CV data file not found: {cv_file_path}")

    try:
        with open(cv_path, "r", encoding="utf-8") as f:
            cv_data = json.load(f)

        # Validate required fields
        required_fields = ["name", "email", "work_experience", "skills"]
        for field in required_fields:
            if field not in cv_data:
                raise ValueError(f"Missing required CV field: {field}")

        return cv_data

    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in CV file: {e}")
    except Exception as e:
        raise ValueError(f"Error loading CV data: {e}")


def extract_cv_analysis(cv_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract CV analysis data compatible with existing CVAnalysis model.

    Args:
        cv_data: Raw CV data from JSON

    Returns:
        Dictionary compatible with CVAnalysis structure
    """
    # Extract skills from skills array
    skills = [skill["title"] for skill in cv_data.get("skills", [])]

    # Calculate experience years from work experience
    experience_years = calculate_experience_years(cv_data.get("work_experience", []))

    # Extract previous roles
    previous_roles = [exp["title"] for exp in cv_data.get("work_experience", [])]

    # Extract education
    education = [edu["title"] for edu in cv_data.get("education", [])]

    # Extract certifications
    certifications = [cert["title"] for cert in cv_data.get("certifications", [])]

    # Extract technology domains from work experience stacks
    technologies = []
    domains = set()

    for exp in cv_data.get("work_experience", []):
        if "stack" in exp:
            technologies.extend(exp["stack"])

    # Determine domains based on technologies
    if any(tech in ["Java", "Spring", "Kotlin"] for tech in technologies):
        domains.add("Backend Development")
    if any(
        tech in ["JavaScript", "TypeScript", "React", "Vue"] for tech in technologies
    ):
        domains.add("Frontend Development")
    if any(tech in ["AWS", "Docker", "Kubernetes"] for tech in technologies):
        domains.add("DevOps/Cloud")
    if any(tech in ["Python", "Machine Learning", "AI"] for tech in technologies):
        domains.add("Data Science/AI")

    # Extract key achievements from descriptions
    key_achievements = []
    for exp in cv_data.get("work_experience", []):
        desc = exp.get("description", "")
        # Extract first sentence as key achievement
        if desc:
            first_sentence = desc.split(".")[0].strip()
            if first_sentence:
                key_achievements.append(first_sentence)

    return {
        "skills": list(set(skills)),  # Remove duplicates
        "experience_years": experience_years,
        "previous_roles": previous_roles,
        "education": education,
        "certifications": certifications,
        "domains": list(domains),
        "key_achievements": key_achievements[:3],  # Top 3 achievements
        "technologies": list(set(technologies)),  # Remove duplicates
    }


def calculate_experience_years(work_experience: List[Dict[str, Any]]) -> int:
    """
    Calculate total years of work experience from work experience array.

    Args:
        work_experience: List of work experience entries

    Returns:
        Total years of experience (rounded)
    """
    from datetime import datetime

    total_months = 0

    for exp in work_experience:
        start_date = exp.get("start_date", "")
        end_date = exp.get("end_date", "")

        if not start_date:
            continue

        try:
            # Parse MM-YYYY format
            start_month, start_year = map(int, start_date.split("-"))

            if end_date:
                end_month, end_year = map(int, end_date.split("-"))
            else:
                # Use current date if no end date
                now = datetime.now()
                end_month, end_year = now.month, now.year

            # Calculate months difference
            months = (end_year - start_year) * 12 + (end_month - start_month)
            total_months += max(0, months)  # Ensure non-negative

        except (ValueError, AttributeError):
            # Skip invalid date formats
            continue

    return round(total_months / 12)


def get_technology_stack(cv_data: Dict[str, Any]) -> List[str]:
    """
    Get comprehensive technology stack from CV data.

    Args:
        cv_data: CV data dictionary

    Returns:
        List of all technologies mentioned in CV
    """
    technologies = set()

    # From work experience stacks
    for exp in cv_data.get("work_experience", []):
        if "stack" in exp:
            technologies.update(exp["stack"])

    # From skills (if they match common technologies)
    tech_skills = []
    for skill in cv_data.get("skills", []):
        skill_title = skill["title"]
        # Common technology patterns
        if any(
            tech in skill_title.lower()
            for tech in [
                "java",
                "python",
                "javascript",
                "react",
                "spring",
                "aws",
                "docker",
                "mysql",
            ]
        ):
            tech_skills.append(skill_title)

    technologies.update(tech_skills)

    return sorted(list(technologies))
