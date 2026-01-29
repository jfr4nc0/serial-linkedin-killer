from datetime import datetime
from typing import List, Optional, TypedDict


class JobExperience(TypedDict):
    company: str
    position: str
    start_date: Optional[str]  # Format: YYYY-MM-DD or YYYY-MM or YYYY
    end_date: Optional[
        str
    ]  # Format: YYYY-MM-DD or YYYY-MM or YYYY, 'Present' if current
    duration_years: float  # Calculated duration in years


class SimilarJobGroup(TypedDict):
    area: str  # Domain/field of expertise
    job_count: int  # Number of similar jobs
    total_duration: float  # Total years in this area
    companies: List[str]  # Companies where these jobs were held


class CVAnalysis(TypedDict):
    skills: List[str]
    experience_years: int  # Total years of experience (from jobs with dates)
    previous_roles: List[str]  # General list of previous roles
    education: List[str]
    certifications: List[str]
    domains: List[str]
    key_achievements: List[str]
    technologies: List[str]
    # Enhanced experience analysis
    job_experiences: List[JobExperience]  # Detailed job history with dates
    similar_job_groups: List[SimilarJobGroup]  # Grouped similar jobs by area
    calculated_experience_years: float  # Calculated total from job dates
    main_domains: List[str]  # Main areas of expertise based on job history
