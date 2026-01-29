from typing import Any, List, Optional, TypedDict


class CVAnalysis(TypedDict):
    skills: List[str]
    experience_years: int
    previous_roles: List[str]
    education: List[str]
    certifications: List[str]
    domains: List[str]
    key_achievements: List[str]
    technologies: List[str]


class ApplicationRequest(TypedDict):
    job_id: int
    monthly_salary: int


class ApplicationResult(TypedDict):
    id_job: int
    success: bool
    error: Optional[str]


class JobResult(TypedDict):
    id_job: int
    job_description: str


class AuthState(TypedDict):
    email: str
    password: str
    browser_manager: Any
    authenticated: bool
    captcha_detected: bool
    captcha_solved: bool
    error: str
