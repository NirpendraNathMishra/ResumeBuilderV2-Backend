from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field


# ---------------------------------------------------------------------------
# Professional Field Enum
# ---------------------------------------------------------------------------
class ProfessionalField(str, Enum):
    TECH = "tech"
    SALES = "sales"
    MARKETING = "marketing"
    FINANCE = "finance"
    HEALTHCARE = "healthcare"
    EDUCATION = "education"
    DESIGN = "design"
    LEGAL = "legal"
    HR = "hr"
    GENERAL = "general"


class CVType(str, Enum):
    original = "original"
    tailored = "tailored"


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------
class Contact(BaseModel):
    phone: str
    location: str
    email: EmailStr
    linkedin: Optional[str] = None
    github: Optional[str] = None
    portfolio: Optional[str] = None
    website: Optional[str] = None
    twitter: Optional[str] = None


class Education(BaseModel):
    institution: str
    location: str
    degree: str
    gpa: Optional[str] = None
    graduation_date: str


class Experience(BaseModel):
    company: str
    role: str
    start_date: str
    end_date: str
    location: str
    description: List[str]


class Project(BaseModel):
    name: str
    demo_link: Optional[str] = None
    technologies: Optional[str] = None
    description: List[str]


class SkillCategory(BaseModel):
    category_name: str  # e.g. "Programming Languages", "Sales Tools", "Marketing Platforms"
    skills: List[str]


class Publication(BaseModel):
    title: str
    publisher: Optional[str] = None
    date: Optional[str] = None
    url: Optional[str] = None
    summary: Optional[str] = None


class Award(BaseModel):
    title: str
    awarder: Optional[str] = None
    date: Optional[str] = None
    summary: Optional[str] = None


class Volunteer(BaseModel):
    organization: str
    role: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    description: List[str] = []


class Coursework(BaseModel):
    major_coursework: List[str] = []
    minor_coursework: List[str] = []


class GeneratedCV(BaseModel):
    cv_type: CVType
    pdf_url: str
    generated_at: Optional[str] = None
    professional_field: Optional[str] = None


# ---------------------------------------------------------------------------
# Main User Profile — universal across all fields
# ---------------------------------------------------------------------------
class UserProfileV2(BaseModel):
    clerk_user_id: str
    name: str
    professional_field: ProfessionalField = ProfessionalField.GENERAL
    professional_summary: Optional[str] = None
    contact: Contact
    education: List[Education] = []
    experience: List[Experience] = []
    skills: List[SkillCategory] = []
    # Optional field-specific sections
    projects: Optional[List[Project]] = None
    certifications: Optional[List[str]] = None
    publications: Optional[List[Publication]] = None
    awards: Optional[List[Award]] = None
    volunteer: Optional[List[Volunteer]] = None
    languages: Optional[List[str]] = None
    coursework: Optional[Coursework] = None
    # Stored CVs & credits
    generated_cvs: List[GeneratedCV] = Field(default_factory=list)
    tailored_cv_credits: int = 4


# ---------------------------------------------------------------------------
# Request Models
# ---------------------------------------------------------------------------
class GenerateResumeRequest(BaseModel):
    user_profile: UserProfileV2


class TailoredResumeRequest(BaseModel):
    job_description: str
    clerk_user_id: str


class PaymentRequest(BaseModel):
    clerk_user_id: str
    tier: str
