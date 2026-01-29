import os
import re

import pdfplumber
import pypdf
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool

from src.core.model.cv_analysis import CVAnalysis
from src.core.providers.llm_client import get_llm_client


@tool
def read_pdf_cv(file_path: str) -> str:
    """
    Extract text content from PDF CV file.

    Args:
        file_path: Path to the PDF CV file

    Returns:
        Extracted text content from the PDF
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"CV file not found at: {file_path}")

    if not file_path.lower().endswith(".pdf"):
        raise ValueError("File must be a PDF")

    try:
        # Try pdfplumber first (better text extraction)
        with pdfplumber.open(file_path) as pdf:
            text = ""
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\\n\\n"

            if text.strip():
                return text.strip()

    except Exception as e:
        print(f"pdfplumber failed: {e}, trying pypdf...")

    try:
        # Fallback to pypdf
        with open(file_path, "rb") as file:
            pdf_reader = pypdf.PdfReader(file)
            text = ""

            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text += page.extract_text() + "\\n\\n"

            return text.strip()

    except Exception as e:
        raise Exception(f"Failed to extract text from PDF: {str(e)}")


@tool
def analyze_cv_structure(cv_text: str) -> CVAnalysis:
    """
    Use AI to extract structured data from CV text.

    Args:
        cv_text: Raw text content from CV

    Returns:
        Structured CV analysis data
    """
    # Initialize the VLLM model
    model = get_llm_client()

    # Create analysis prompt
    prompt = ChatPromptTemplate.from_template(
        """
    Analyze the following CV text and extract structured information.

    CV Content:
    {cv_text}

    Extract and return ONLY a JSON object with these fields:
    {{
        "skills": ["list of technical skills"],
        "experience_years": number_of_years_experience,
        "previous_roles": ["list of job titles/positions"],
        "education": ["degrees, universities, relevant education"],
        "certifications": ["professional certifications"],
        "domains": ["industry domains/sectors worked in"],
        "key_achievements": ["notable achievements or projects"],
        "technologies": ["programming languages, frameworks, tools"]
    }}

    Be specific and comprehensive. Extract only factual information present in the CV.
    """
    )

    try:
        # Get AI analysis
        chain = prompt | model
        response = chain.invoke({"cv_text": cv_text})

        # Parse the response (assuming it returns structured data)
        import json

        # Clean the response text to extract JSON
        response_text = (
            response.content if hasattr(response, "content") else str(response)
        )

        # Try to extract JSON from the response
        json_match = re.search(r"\\{.*\\}", response_text, re.DOTALL)
        if json_match:
            json_str = json_match.group()
            analysis_data = json.loads(json_str)
        else:
            # Fallback parsing
            analysis_data = json.loads(response_text)

        # Ensure all required fields exist
        cv_analysis = CVAnalysis(
            skills=analysis_data.get("skills", []),
            experience_years=analysis_data.get("experience_years", 0),
            previous_roles=analysis_data.get("previous_roles", []),
            education=analysis_data.get("education", []),
            certifications=analysis_data.get("certifications", []),
            domains=analysis_data.get("domains", []),
            key_achievements=analysis_data.get("key_achievements", []),
            technologies=analysis_data.get("technologies", []),
        )

        return cv_analysis

    except Exception as e:
        print(f"Error analyzing CV with AI: {e}")
        # Return basic fallback analysis
        return CVAnalysis(
            skills=_extract_basic_skills(cv_text),
            experience_years=_extract_basic_experience(cv_text),
            previous_roles=_extract_basic_roles(cv_text),
            education=[],
            certifications=[],
            domains=[],
            key_achievements=[],
            technologies=[],
        )


def _extract_basic_skills(text: str) -> list:
    """Fallback basic skill extraction using regex"""
    common_skills = [
        "python",
        "javascript",
        "java",
        "react",
        "django",
        "flask",
        "sql",
        "postgresql",
        "mysql",
        "mongodb",
        "docker",
        "kubernetes",
        "aws",
        "azure",
        "gcp",
        "machine learning",
        "deep learning",
        "tensorflow",
        "pytorch",
        "pandas",
        "numpy",
        "scikit-learn",
    ]

    found_skills = []
    text_lower = text.lower()

    for skill in common_skills:
        if skill in text_lower:
            found_skills.append(skill.title())

    return found_skills


def _extract_basic_experience(text: str) -> int:
    """Fallback basic experience extraction using regex"""
    # Look for patterns like "5 years", "3+ years", etc.
    experience_patterns = [
        r"(\\d+)\\s*\\+?\\s*years?\\s+(?:of\\s+)?experience",
        r"(\\d+)\\s*years?\\s+(?:of\\s+)?(?:professional\\s+)?experience",
        r"experience\\s*:?\\s*(\\d+)\\s*years?",
    ]

    for pattern in experience_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            return int(matches[0])

    return 0


def _extract_basic_roles(text: str) -> list:
    """Fallback basic role extraction"""
    common_roles = [
        "software engineer",
        "developer",
        "data scientist",
        "analyst",
        "manager",
        "senior",
        "junior",
        "lead",
        "architect",
        "consultant",
    ]

    found_roles = []
    text_lower = text.lower()

    for role in common_roles:
        if role in text_lower:
            found_roles.append(role.title())

    return list(set(found_roles))  # Remove duplicates


def _calculate_job_duration(start_date: str, end_date: str) -> float:
    """
    Calculate job duration in years from start and end dates.

    Args:
        start_date: Start date in format YYYY-MM-DD, YYYY-MM, or YYYY
        end_date: End date in format YYYY-MM-DD, YYYY-MM, YYYY, or "Present"

    Returns:
        Duration in years as float
    """
    import re
    from datetime import datetime

    if not start_date:
        return 0.0

    # Parse start date
    start_year = None
    start_month = 1  # Default to January if month not specified

    if re.match(r"\d{4}-\d{2}-\d{2}", start_date):  # YYYY-MM-DD
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            start_year = start_dt.year
            start_month = start_dt.month
        except ValueError:
            pass
    elif re.match(r"\d{4}-\d{2}", start_date):  # YYYY-MM
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m")
            start_year = start_dt.year
            start_month = start_dt.month
        except ValueError:
            pass
    elif re.match(r"\d{4}", start_date):  # YYYY
        try:
            start_year = int(start_date)
        except ValueError:
            pass

    if not start_year:
        return 0.0

    # Parse end date
    end_year = None
    end_month = 12  # Default to December if month not specified

    if end_date and end_date != "Present":
        if re.match(r"\d{4}-\d{2}-\d{2}", end_date):  # YYYY-MM-DD
            try:
                end_dt = datetime.strptime(end_date, "%Y-%m-%d")
                end_year = end_dt.year
                end_month = end_dt.month
            except ValueError:
                pass
        elif re.match(r"\d{4}-\d{2}", end_date):  # YYYY-MM
            try:
                end_dt = datetime.strptime(end_date, "%Y-%m")
                end_year = end_dt.year
                end_month = end_dt.month
            except ValueError:
                pass
        elif re.match(r"\d{4}", end_date):  # YYYY
            try:
                end_year = int(end_date)
            except ValueError:
                pass
    else:
        # If end date is "Present" or None, use current year/month
        end_year = datetime.now().year
        end_month = datetime.now().month

    if not end_year:
        return 0.0

    # Calculate duration in years
    years = end_year - start_year
    months = end_month - start_month

    total_months = years * 12 + months
    return round(total_months / 12.0, 1)


def _infer_domain_from_position(position: str) -> str:
    """
    Infer domain/area from job position title.

    Args:
        position: Job position title

    Returns:
        Domain/area string or None
    """
    position_lower = position.lower()

    # Define domain keywords
    domains = {
        "software_engineering": [
            "developer",
            "software",
            "programmer",
            "engineer",
            "architect",
        ],
        "data_science": [
            "data scientist",
            "data analyst",
            "machine learning",
            "ml",
            "ai",
            "analytics",
        ],
        "product_management": [
            "product manager",
            "product owner",
            "pm",
            "scrum master",
        ],
        "project_management": ["project manager", "program manager", "pmo"],
        "design": ["designer", "ux", "ui", "graphic designer", "product designer"],
        "sales": ["sales", "business development", "account manager"],
        "marketing": ["marketing", "digital marketing", "growth", "content"],
        "finance": ["financial", "accountant", "finance", "cfo"],
        "hr": ["hr", "human resources", "recruiter", "talent"],
        "operations": ["operations", "operations manager", "ops"],
    }

    for domain, keywords in domains.items():
        for keyword in keywords:
            if keyword in position_lower:
                return domain.replace("_", " ").title()

    return "General"


def _group_similar_jobs(job_experiences: list) -> list:
    """
    Group similar jobs by area/domain and count them.

    Args:
        job_experiences: List of job experience dictionaries

    Returns:
        List of SimilarJobGroup objects
    """
    from collections import defaultdict

    domain_groups = defaultdict(
        lambda: {"job_count": 0, "total_duration": 0.0, "companies": []}
    )

    for job in job_experiences:
        domain = job.get("domain", "General") or "General"
        company = job.get("company", "Unknown")

        domain_groups[domain]["job_count"] += 1
        domain_groups[domain]["total_duration"] += job.get("duration_years", 0.0)
        if company not in domain_groups[domain]["companies"]:
            domain_groups[domain]["companies"].append(company)

    # Convert to the required format
    groups = []
    for domain, data in domain_groups.items():
        groups.append(
            {
                "area": domain,
                "job_count": data["job_count"],
                "total_duration": round(data["total_duration"], 1),
                "companies": data["companies"],
            }
        )

    return groups


def _extract_job_history_from_text(cv_text: str) -> list:
    """
    Extract job history from CV text using regex patterns as fallback.

    Args:
        cv_text: Raw CV text content

    Returns:
        List of job experience dictionaries
    """
    import re

    # This is a simplified implementation - in a real scenario,
    # you might want more sophisticated parsing
    job_experiences = []

    # Basic attempt to find date patterns in CV
    # This is a simplified approach - proper NLP would be more complex
    lines = cv_text.split("\n")

    current_job = {}
    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Look for date patterns like "Jan 2020 - Mar 2022" or "2020 - 2022"
        date_match = re.search(
            r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}\s*[-–]\s*(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|May|June|July|August|September|October|November|December|Present)\s+\d{4}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}\s*[-–]\s*Present|\d{4}\s*[-–]\s*\d{4}|\d{4}\s*[-–]\s*Present)",
            line,
            re.IGNORECASE,
        )

        if date_match:
            dates = date_match.group(1)
            # Simplified: assume the previous non-date line was the position/company
            # This is a very basic approach - real implementation would need NLP
            continue

    # Return empty list since this is just a placeholder
    return []


def _calculate_total_experience_from_jobs(job_experiences: list) -> float:
    """
    Calculate total experience from job experiences list.

    Args:
        job_experiences: List of job experience dictionaries

    Returns:
        Total experience in years
    """
    total = 0.0
    for job in job_experiences:
        total += job.get("duration_years", 0.0)
    return round(total, 1)


def _get_main_domains_from_jobs(job_experiences: list) -> list:
    """
    Get main domains from job experiences.

    Args:
        job_experiences: List of job experience dictionaries

    Returns:
        List of main domains
    """
    domains = set()
    for job in job_experiences:
        domain = job.get("domain")
        if domain:
            domains.add(domain)
    return list(domains)
