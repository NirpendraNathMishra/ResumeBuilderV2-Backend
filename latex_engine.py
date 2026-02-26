"""
LaTeX Engine V2 — Universal multi-field resume generator.

Generates LaTeX content based on user profile and professional field.
Each field gets a tailored section ordering and field-specific sections.
"""

import os
import re
from models import ProfessionalField


# ---------------------------------------------------------------------------
# Section ordering per professional field
# ---------------------------------------------------------------------------
FIELD_SECTION_ORDER = {
    ProfessionalField.TECH: [
        "summary", "education", "experience", "projects",
        "skills", "certifications", "coursework"
    ],
    ProfessionalField.SALES: [
        "summary", "experience", "skills", "education",
        "awards", "certifications"
    ],
    ProfessionalField.MARKETING: [
        "summary", "experience", "skills", "projects",
        "education", "certifications"
    ],
    ProfessionalField.FINANCE: [
        "summary", "education", "experience", "skills",
        "certifications", "awards"
    ],
    ProfessionalField.HEALTHCARE: [
        "summary", "education", "experience", "publications",
        "skills", "certifications"
    ],
    ProfessionalField.EDUCATION: [
        "summary", "education", "experience", "publications",
        "skills", "coursework", "awards"
    ],
    ProfessionalField.DESIGN: [
        "summary", "experience", "projects", "skills",
        "education", "awards"
    ],
    ProfessionalField.LEGAL: [
        "summary", "education", "experience", "skills",
        "publications", "awards", "certifications"
    ],
    ProfessionalField.HR: [
        "summary", "experience", "skills", "education",
        "certifications", "awards"
    ],
    ProfessionalField.GENERAL: [
        "summary", "education", "experience", "skills",
        "projects", "certifications", "volunteer",
        "languages", "awards"
    ],
}


# ---------------------------------------------------------------------------
# LaTeX character escaping
# ---------------------------------------------------------------------------
def escape_latex(text: str) -> str:
    """Escape special LaTeX characters in user-provided text."""
    if not isinstance(text, str):
        text = str(text)
    replacements = {
        '\\': r'\textbackslash{}',
        '&': r'\&',
        '%': r'\%',
        '$': r'\$',
        '#': r'\#',
        '{': r'\{',
        '}': r'\}',
        '~': r'\textasciitilde{}',
        '^': r'\textasciicircum{}',
    }
    pattern = re.compile(
        '|'.join(re.escape(k) for k in sorted(replacements, key=len, reverse=True))
    )
    return pattern.sub(lambda m: replacements[m.group()], text)


# ---------------------------------------------------------------------------
# Section generators
# ---------------------------------------------------------------------------
def _header_section(profile: dict) -> str:
    """Generate the header (name + contact info)."""
    name = escape_latex(profile.get("name", ""))
    contact = profile.get("contact", {})
    phone = escape_latex(contact.get("phone", ""))
    email = escape_latex(contact.get("email", ""))

    parts = []
    parts.append(r"\begin{center}")
    parts.append(rf"    \textbf{{\Huge \scshape {name}}} \\ \vspace{{3pt}}")

    # Build contact line
    contact_items = []
    if phone:
        contact_items.append(rf"\faMobile \hspace{{.5pt}} \href{{tel:{phone}}}{{{phone}}}")
    if email:
        contact_items.append(rf"\faAt \hspace{{.5pt}} \href{{mailto:{email}}}{{{email}}}")
    if contact.get("linkedin"):
        li = escape_latex(contact["linkedin"])
        contact_items.append(rf"\faLinkedinSquare \hspace{{.5pt}} \href{{{li}}}{{LinkedIn}}")
    if contact.get("github"):
        gh = escape_latex(contact["github"])
        contact_items.append(rf"\faGithub \hspace{{.5pt}} \href{{{gh}}}{{GitHub}}")
    if contact.get("portfolio"):
        pf = escape_latex(contact["portfolio"])
        contact_items.append(rf"\faGlobe \hspace{{.5pt}} \href{{{pf}}}{{Portfolio}}")
    if contact.get("website"):
        ws = escape_latex(contact["website"])
        contact_items.append(rf"\faGlobe \hspace{{.5pt}} \href{{{ws}}}{{Website}}")
    if contact.get("twitter"):
        tw = escape_latex(contact["twitter"])
        contact_items.append(rf"\faTwitter \hspace{{.5pt}} \href{{{tw}}}{{Twitter}}")
    if contact.get("location"):
        loc = escape_latex(contact["location"])
        contact_items.append(rf"\faMapMarker \hspace{{.2pt}} {loc}")

    parts.append(r"    \small")
    parts.append("    " + "\n    $|$\n    ".join(contact_items))
    parts.append(r"\end{center}")
    return "\n".join(parts)


def _summary_section(profile: dict) -> str:
    """Professional Summary / Objective."""
    summary = profile.get("professional_summary", "")
    if not summary or not summary.strip():
        return ""
    return (
        "\\section{Professional Summary}\n"
        f"\\small{{{escape_latex(summary)}}}\n"
    )


def _education_section(education: list) -> str:
    if not education:
        return ""
    lines = ["\\section{Education}", "\\vspace{-1pt}", "\\resumeSubHeadingListStart"]
    for edu in education:
        inst = escape_latex(edu.get("institution", ""))
        loc = escape_latex(edu.get("location", ""))
        deg = escape_latex(edu.get("degree", ""))
        grad = escape_latex(edu.get("graduation_date", ""))
        lines.append(f"\\resumeEducationHeading{{{inst}}}{{{loc}}}{{{deg}}}{{{grad}}}")
        gpa = edu.get("gpa", "")
        if gpa:
            lines.append(f"\\resumeItemListStart")
            lines.append(f"  \\resumeItem{{GPA: {escape_latex(gpa)}}}")
            lines.append(f"\\resumeItemListEnd")
    lines.append("\\resumeSubHeadingListEnd")
    return "\n".join(lines)


def _experience_section(experience: list) -> str:
    if not experience:
        return ""
    lines = ["\\section{Work Experience}", "\\vspace{-1pt}", "\\resumeSubHeadingListStart"]
    for job in experience:
        company = escape_latex(job.get("company", ""))
        loc = escape_latex(job.get("location", ""))
        role = escape_latex(job.get("role", ""))
        start = escape_latex(job.get("start_date", ""))
        end = escape_latex(job.get("end_date", ""))
        lines.append(f"\\resumeSubheading{{{company}}}{{{loc}}}{{{role}}}{{{start} -- {end}}}")
        lines.append("\\resumeItemListStart")
        for desc in job.get("description", []):
            if desc.strip():
                lines.append(f"  \\resumeItem{{{escape_latex(desc)}}}")
        lines.append("\\resumeItemListEnd")
    lines.append("\\resumeSubHeadingListEnd")
    return "\n".join(lines)


def _projects_section(projects: list) -> str:
    if not projects:
        return ""
    lines = ["\\section{Projects}", "\\vspace{3pt}", "\\resumeSubHeadingListStart"]
    for proj in projects:
        name = escape_latex(proj.get("name", ""))
        demo = proj.get("demo_link", "")
        tech = proj.get("technologies", "")
        right_col = ""
        if demo:
            right_col = f" \\emph{{\\href{{{demo}}}{{\\color{{blue}}Demo}}}}"
        if tech:
            right_col += f" \\textit{{\\small {escape_latex(tech)}}}" if right_col else f"\\textit{{\\small {escape_latex(tech)}}}"
        lines.append(f"\\resumeProjectHeading{{{name}}}{{{right_col}}}")
        lines.append("\\resumeItemListStart")
        for desc in proj.get("description", []):
            if desc.strip():
                lines.append(f"  \\resumeItem{{{escape_latex(desc)}}}")
        lines.append("\\resumeItemListEnd")
    lines.append("\\resumeSubHeadingListEnd")
    return "\n".join(lines)


def _skills_section(skills: list) -> str:
    if not skills:
        return ""
    lines = ["\\section{Skills}", "\\vspace{2pt}", "\\resumeSubHeadingListStart"]
    lines.append("\\small{\\item{")
    for i, cat in enumerate(skills):
        cat_name = escape_latex(cat.get("category_name", ""))
        skill_list = ", ".join(escape_latex(s) for s in cat.get("skills", []))
        separator = " \\\\ \\vspace{3pt}" if i < len(skills) - 1 else ""
        lines.append(f"  \\textbf{{{cat_name}:}} {{ {skill_list} }}{separator}")
    lines.append("}}")
    lines.append("\\resumeSubHeadingListEnd")
    return "\n".join(lines)


def _certifications_section(certifications: list) -> str:
    if not certifications:
        return ""
    lines = ["\\section{Certifications}", "\\vspace{2pt}", "\\resumeSubHeadingListStart"]
    lines.append("\\resumeItemListStart")
    for cert in certifications:
        if cert.strip():
            lines.append(f"  \\resumeItem{{{escape_latex(cert)}}}")
    lines.append("\\resumeItemListEnd")
    lines.append("\\resumeSubHeadingListEnd")
    return "\n".join(lines)


def _publications_section(publications: list) -> str:
    if not publications:
        return ""
    lines = ["\\section{Publications}", "\\vspace{2pt}", "\\resumeSubHeadingListStart"]
    for pub in publications:
        title = escape_latex(pub.get("title", ""))
        date = escape_latex(pub.get("date", ""))
        publisher = escape_latex(pub.get("publisher", ""))
        lines.append(f"\\resumePublicationHeading{{{title}}}{{{date}}}{{{publisher}}}")
        summary = pub.get("summary", "")
        if summary and summary.strip():
            lines.append("\\resumeItemListStart")
            lines.append(f"  \\resumeItem{{{escape_latex(summary)}}}")
            lines.append("\\resumeItemListEnd")
    lines.append("\\resumeSubHeadingListEnd")
    return "\n".join(lines)


def _awards_section(awards: list) -> str:
    if not awards:
        return ""
    lines = ["\\section{Awards \\& Honors}", "\\vspace{2pt}", "\\resumeSubHeadingListStart"]
    for award in awards:
        title = escape_latex(award.get("title", ""))
        date = escape_latex(award.get("date", ""))
        awarder = escape_latex(award.get("awarder", ""))
        lines.append(f"\\resumeAwardHeading{{{title}}}{{{date}}}{{{awarder}}}")
        summary = award.get("summary", "")
        if summary and summary.strip():
            lines.append("\\resumeItemListStart")
            lines.append(f"  \\resumeItem{{{escape_latex(summary)}}}")
            lines.append("\\resumeItemListEnd")
    lines.append("\\resumeSubHeadingListEnd")
    return "\n".join(lines)


def _volunteer_section(volunteer: list) -> str:
    if not volunteer:
        return ""
    lines = ["\\section{Volunteer Experience}", "\\vspace{-1pt}", "\\resumeSubHeadingListStart"]
    for vol in volunteer:
        org = escape_latex(vol.get("organization", ""))
        role = escape_latex(vol.get("role", ""))
        start = escape_latex(vol.get("start_date", ""))
        end = escape_latex(vol.get("end_date", ""))
        date_str = f"{start} -- {end}" if start else ""
        lines.append(f"\\resumeSubheading{{{org}}}{{}}{{{role}}}{{{date_str}}}")
        lines.append("\\resumeItemListStart")
        for desc in vol.get("description", []):
            if desc.strip():
                lines.append(f"  \\resumeItem{{{escape_latex(desc)}}}")
        lines.append("\\resumeItemListEnd")
    lines.append("\\resumeSubHeadingListEnd")
    return "\n".join(lines)


def _languages_section(languages: list) -> str:
    if not languages:
        return ""
    lang_str = ", ".join(escape_latex(l) for l in languages)
    return (
        "\\section{Languages}\n"
        "\\vspace{2pt}\n"
        "\\resumeSubHeadingListStart\n"
        f"\\small{{\\item{{\\textbf{{Languages:}} {{ {lang_str} }}}}}}\n"
        "\\resumeSubHeadingListEnd\n"
    )


def _coursework_section(coursework: dict) -> str:
    if not coursework:
        return ""
    major = coursework.get("major_coursework", [])
    minor = coursework.get("minor_coursework", [])
    if not major and not minor:
        return ""
    lines = ["\\section{Relevant Coursework}", "\\vspace{2pt}", "\\resumeSubHeadingListStart"]
    lines.append("\\small{\\item{")
    if major:
        maj_str = ", ".join(escape_latex(c) for c in major)
        separator = " \\\\ \\vspace{3pt}" if minor else ""
        lines.append(f"  \\textbf{{Major coursework:}} {{ {maj_str} }}{separator}")
    if minor:
        min_str = ", ".join(escape_latex(c) for c in minor)
        lines.append(f"  \\textbf{{Minor coursework:}} {{ {min_str} }}")
    lines.append("}}")
    lines.append("\\resumeSubHeadingListEnd")
    return "\n".join(lines)


# Map section names to generator functions
SECTION_GENERATORS = {
    "summary": lambda p: _summary_section(p),
    "education": lambda p: _education_section(p.get("education", [])),
    "experience": lambda p: _experience_section(p.get("experience", [])),
    "projects": lambda p: _projects_section(p.get("projects") or []),
    "skills": lambda p: _skills_section(p.get("skills", [])),
    "certifications": lambda p: _certifications_section(p.get("certifications") or []),
    "publications": lambda p: _publications_section(p.get("publications") or []),
    "awards": lambda p: _awards_section(p.get("awards") or []),
    "volunteer": lambda p: _volunteer_section(p.get("volunteer") or []),
    "languages": lambda p: _languages_section(p.get("languages") or []),
    "coursework": lambda p: _coursework_section(p.get("coursework") or {}),
}


# ---------------------------------------------------------------------------
# Main generator
# ---------------------------------------------------------------------------
def generate_latex_content(profile: dict) -> str:
    """
    Generate complete LaTeX document from a user profile.

    The section ordering is determined by the user's professional_field.
    Sections that have no data are automatically skipped.
    """
    template_dir = os.path.dirname(os.path.abspath(__file__))
    template_path = os.path.join(template_dir, "templates", "base_template.tex")

    if not os.path.exists(template_path):
        raise FileNotFoundError(f"LaTeX template not found at {template_path}")

    with open(template_path, "r", encoding="utf-8") as f:
        template = f.read()

    # Determine field
    field_str = profile.get("professional_field", "general")
    try:
        field = ProfessionalField(field_str)
    except ValueError:
        field = ProfessionalField.GENERAL

    # Build header
    header = _header_section(profile)

    # Build sections in field-specific order
    section_order = FIELD_SECTION_ORDER.get(field, FIELD_SECTION_ORDER[ProfessionalField.GENERAL])
    sections_content = []
    for section_name in section_order:
        generator = SECTION_GENERATORS.get(section_name)
        if generator:
            content = generator(profile)
            if content and content.strip():
                sections_content.append(content)

    # Replace placeholders
    latex = template.replace("% HEADER_PLACEHOLDER", header)
    latex = latex.replace("% SECTIONS_PLACEHOLDER", "\n\n".join(sections_content))

    return latex
