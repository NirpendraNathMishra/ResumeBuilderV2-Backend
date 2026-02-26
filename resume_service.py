"""
Resume Service V2 — Orchestrates LaTeX generation, compilation, and storage.
"""

import httpx
import os
import uuid
import json
from datetime import datetime, timezone

from config import user_profiles_collection, client as ai_client, FREE_FIELD_LIMIT, FREE_TAILOR_CREDITS
from latex_engine import generate_latex_content


# ---------------------------------------------------------------------------
# Supabase Storage config
# ---------------------------------------------------------------------------
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
BUCKET_NAME = os.getenv("BUCKET_NAME", "texfiles")


# ---------------------------------------------------------------------------
# User profile helpers
# ---------------------------------------------------------------------------

async def get_user_profile(clerk_user_id: str) -> dict:
    """Fetch any user profile from MongoDB by clerk_user_id (legacy — returns first match)."""
    from fastapi import HTTPException
    if not clerk_user_id:
        raise HTTPException(status_code=400, detail="clerk_user_id cannot be empty")
    user = await user_profiles_collection.find_one({"clerk_user_id": clerk_user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user["_id"] = str(user["_id"])
    return user


async def get_user_field_profile(clerk_user_id: str, professional_field: str) -> dict | None:
    """Fetch a user profile for a specific professional field. Returns None if not found."""
    if not clerk_user_id:
        return None
    user = await user_profiles_collection.find_one({
        "clerk_user_id": clerk_user_id,
        "professional_field": professional_field,
    })
    if user:
        user["_id"] = str(user["_id"])
    return user


# ---------------------------------------------------------------------------
# Free tier helpers
# ---------------------------------------------------------------------------

async def get_user_used_fields(clerk_user_id: str) -> list[str]:
    """Return a list of distinct professional_field values the user has profiles for."""
    fields = await user_profiles_collection.distinct(
        "professional_field",
        {"clerk_user_id": clerk_user_id}
    )
    return fields


async def get_total_tailor_credits(clerk_user_id: str) -> int:
    """
    Get the total remaining AI tailor credits for a user.
    Credits are stored in a separate 'user_credits' document keyed by clerk_user_id.
    If no document exists, the user has FREE_TAILOR_CREDITS (first time).
    """
    credits_doc = await user_profiles_collection.database.get_collection("user_credits").find_one(
        {"clerk_user_id": clerk_user_id}
    )
    if not credits_doc:
        return FREE_TAILOR_CREDITS
    return credits_doc.get("tailor_credits", 0)


async def decrement_tailor_credits(clerk_user_id: str) -> int:
    """Decrement tailor credits by 1. Returns remaining credits."""
    credits_col = user_profiles_collection.database.get_collection("user_credits")
    credits_doc = await credits_col.find_one({"clerk_user_id": clerk_user_id})

    if not credits_doc:
        # First time using credits — initialize with FREE_TAILOR_CREDITS - 1
        await credits_col.insert_one({
            "clerk_user_id": clerk_user_id,
            "tailor_credits": FREE_TAILOR_CREDITS - 1,
        })
        return FREE_TAILOR_CREDITS - 1
    else:
        new_credits = max(0, credits_doc.get("tailor_credits", 0) - 1)
        await credits_col.update_one(
            {"clerk_user_id": clerk_user_id},
            {"$set": {"tailor_credits": new_credits}},
        )
        return new_credits


async def can_use_field(clerk_user_id: str, field: str) -> bool:
    """Check if user is allowed to use a specific field (already used it, or under free limit)."""
    used_fields = await get_user_used_fields(clerk_user_id)
    if field in used_fields:
        return True  # Already using this field
    if len(used_fields) < FREE_FIELD_LIMIT:
        return True  # Under the free limit
    return False


# ---------------------------------------------------------------------------
# LaTeX → PDF pipeline
# ---------------------------------------------------------------------------

async def compile_latex_to_pdf(latex_content: str) -> bytes:
    """
    Send LaTeX source to latex.ytotech.com API for PDF compilation.
    Returns the raw PDF bytes.
    """
    api_url = "https://latex.ytotech.com/builds/sync"
    payload = {
        "compiler": "pdflatex",
        "resources": [
            {
                "main": True,
                "content": latex_content
            }
        ]
    }
    async with httpx.AsyncClient(timeout=60.0) as http_client:
        response = await http_client.post(api_url, json=payload)
        if response.status_code in (200, 201):
            content_type = response.headers.get("content-type", "")
            if "application/pdf" in content_type:
                return response.content
            else:
                raise Exception(f"LaTeX compilation error: {response.text[:500]}")
        else:
            raise Exception(f"LaTeX API returned {response.status_code}: {response.text[:500]}")


async def upload_pdf_to_supabase(file_bytes: bytes, filename: str) -> str:
    """Upload generated PDF to Supabase Storage and return its public URL."""
    upload_url = f"{SUPABASE_URL}/storage/v1/object/{BUCKET_NAME}/{filename}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/pdf",
        "x-upsert": "true",
    }

    async with httpx.AsyncClient(timeout=30.0) as http_client:
        response = await http_client.post(upload_url, content=file_bytes, headers=headers)
        if response.status_code not in (200, 201):
            raise Exception(f"Supabase upload failed ({response.status_code}): {response.text[:500]}")

    # Return the public URL
    public_url = f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET_NAME}/{filename}"
    return public_url


async def process_resume_generation(user_profile: dict, cv_type: str = "original") -> str:
    """
    Full pipeline: profile → LaTeX → PDF → Supabase Storage → store URL in MongoDB.
    Returns the public PDF URL.
    """
    # 1. Generate LaTeX
    latex_content = generate_latex_content(user_profile)

    # 2. Compile to PDF
    pdf_bytes = await compile_latex_to_pdf(latex_content)

    # 3. Upload to Supabase Storage
    clerk_id = user_profile.get("clerk_user_id", "unknown")
    field = user_profile.get("professional_field", "general")
    filename = f"v2_{clerk_id}_{field}_{cv_type}_{uuid.uuid4().hex[:8]}.pdf"
    pdf_url = await upload_pdf_to_supabase(pdf_bytes, filename)

    # 4. Store CV record in user profile
    cv_record = {
        "cv_type": cv_type,
        "pdf_url": pdf_url,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "professional_field": field,
    }

    await user_profiles_collection.update_one(
        {"clerk_user_id": clerk_id, "professional_field": field},
        {"$push": {"generated_cvs": cv_record}},
    )

    return pdf_url


async def process_tailored_resume(clerk_user_id: str, job_description: str) -> str:
    """
    Generate a tailored CV: fetch profile → AI tailoring → LaTeX → PDF.
    """
    user_profile = await get_user_profile(clerk_user_id)

    # Use AI to tailor the resume content to the job description
    prompt = f"""You are a professional resume writer. Given the following user profile and job description,
tailor the resume content to better match the job requirements. Keep the same JSON structure but improve
descriptions, reorder bullet points, and emphasize relevant skills.

USER PROFILE:
Name: {user_profile.get('name', '')}
Field: {user_profile.get('professional_field', 'general')}
Summary: {user_profile.get('professional_summary', '')}
Experience: {user_profile.get('experience', [])}
Skills: {user_profile.get('skills', [])}
Projects: {user_profile.get('projects', [])}
Education: {user_profile.get('education', [])}

JOB DESCRIPTION:
{job_description}

Return ONLY a JSON object with these keys that should be updated:
- professional_summary (string)
- experience (array of objects with: company, role, start_date, end_date, location, description[])
- skills (array of objects with: category_name, skills[])

Keep all other profile data unchanged. Return ONLY valid JSON, no markdown."""

    try:
        response = ai_client.chat.completions.create(
            model="meta/llama-3.1-70b-instruct",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=4000,
        )
        ai_response = response.choices[0].message.content.strip()

        # Try to parse AI response
        if ai_response.startswith("```"):
            ai_response = ai_response.split("```")[1]
            if ai_response.startswith("json"):
                ai_response = ai_response[4:]

        tailored_data = json.loads(ai_response)

        # Merge tailored data into profile
        if "professional_summary" in tailored_data:
            user_profile["professional_summary"] = tailored_data["professional_summary"]
        if "experience" in tailored_data:
            user_profile["experience"] = tailored_data["experience"]
        if "skills" in tailored_data:
            user_profile["skills"] = tailored_data["skills"]

    except Exception as e:
        print(f"⚠️ AI tailoring failed, generating with original data: {e}")

    # Generate the tailored CV
    return await process_resume_generation(user_profile, cv_type="tailored")
