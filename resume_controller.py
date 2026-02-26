"""
Resume Controller V2 — API routes for the multi-field resume builder.
"""
import httpx
from fastapi import APIRouter, Body, HTTPException
from starlette import status
from starlette.responses import StreamingResponse
from datetime import datetime, timezone
from io import BytesIO

from models import GenerateResumeRequest, TailoredResumeRequest, PaymentRequest, ProfessionalField
from config import user_profiles_collection, clientdb, FREE_FIELD_LIMIT, FREE_TAILOR_CREDITS
from paymentservice import create_order, verify_payment
from resume_service import (
    process_resume_generation, process_tailored_resume,
    get_user_profile, get_user_field_profile,
    get_user_used_fields, get_total_tailor_credits, decrement_tailor_credits, can_use_field,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------
@router.get("/health", tags=["health"])
async def health_check():
    try:
        await clientdb.admin.command("ping")
        return {
            "status": "healthy",
            "version": "2.0",
            "database": "connected",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connection failed: {str(e)}",
        )


# ---------------------------------------------------------------------------
# Field Metadata — returns available fields and their form sections
# ---------------------------------------------------------------------------
FIELD_FORM_SECTIONS = {
    "tech": {
        "label": "Technology",
        "icon": "💻",
        "sections": ["summary", "education", "experience", "projects", "skills", "certifications", "coursework"],
        "skill_suggestions": ["Programming Languages", "Frameworks & Libraries", "Databases", "Cloud & DevOps", "Tools"],
    },
    "sales": {
        "label": "Sales",
        "icon": "📈",
        "sections": ["summary", "experience", "skills", "education", "awards", "certifications"],
        "skill_suggestions": ["CRM Tools", "Sales Methodologies", "Negotiation", "Lead Generation", "Industry Knowledge"],
    },
    "marketing": {
        "label": "Marketing",
        "icon": "📣",
        "sections": ["summary", "experience", "skills", "projects", "education", "certifications"],
        "skill_suggestions": ["Digital Marketing", "Analytics Tools", "Content Strategy", "Social Media", "SEO/SEM"],
    },
    "finance": {
        "label": "Finance",
        "icon": "💰",
        "sections": ["summary", "education", "experience", "skills", "certifications", "awards"],
        "skill_suggestions": ["Financial Analysis", "Accounting Software", "Risk Management", "Compliance", "Excel & Modeling"],
    },
    "healthcare": {
        "label": "Healthcare",
        "icon": "🏥",
        "sections": ["summary", "education", "experience", "publications", "skills", "certifications"],
        "skill_suggestions": ["Clinical Skills", "Patient Care", "Medical Software", "Research Methods", "Compliance"],
    },
    "education": {
        "label": "Education",
        "icon": "🎓",
        "sections": ["summary", "education", "experience", "publications", "skills", "coursework", "awards"],
        "skill_suggestions": ["Teaching Methods", "Curriculum Design", "Ed-Tech Tools", "Assessment", "Research"],
    },
    "design": {
        "label": "Design",
        "icon": "🎨",
        "sections": ["summary", "experience", "projects", "skills", "education", "awards"],
        "skill_suggestions": ["Design Tools", "UI/UX", "Typography", "Branding", "Motion Graphics"],
    },
    "legal": {
        "label": "Legal",
        "icon": "⚖️",
        "sections": ["summary", "education", "experience", "skills", "publications", "awards", "certifications"],
        "skill_suggestions": ["Practice Areas", "Legal Research", "Case Management", "Compliance", "Bar Admissions"],
    },
    "hr": {
        "label": "Human Resources",
        "icon": "👥",
        "sections": ["summary", "experience", "skills", "education", "certifications", "awards"],
        "skill_suggestions": ["HRIS Systems", "Recruitment", "Employee Relations", "Compensation & Benefits", "Training"],
    },
    "general": {
        "label": "General",
        "icon": "📄",
        "sections": ["summary", "education", "experience", "skills", "projects", "certifications", "volunteer", "languages", "awards"],
        "skill_suggestions": ["Technical Skills", "Soft Skills", "Tools & Software", "Languages"],
    },
}


@router.get("/fields", tags=["fields"])
async def get_available_fields():
    """Return all available professional fields with metadata."""
    return FIELD_FORM_SECTIONS


@router.get("/fields/{field_name}", tags=["fields"])
async def get_field_details(field_name: str):
    """Return form sections and skill suggestions for a specific field."""
    if field_name not in FIELD_FORM_SECTIONS:
        raise HTTPException(status_code=404, detail=f"Field '{field_name}' not found")
    return FIELD_FORM_SECTIONS[field_name]


# ---------------------------------------------------------------------------
# User Profile CRUD
# ---------------------------------------------------------------------------
@router.get("/get_user_profile/{clerk_user_id}")
async def get_user_profile_route(clerk_user_id: str):
    return await get_user_profile(clerk_user_id)


@router.get("/get_user_profile/{clerk_user_id}/{field}")
async def get_user_field_profile_route(clerk_user_id: str, field: str):
    """Fetch profile for a specific professional field. Returns empty dict if none found."""
    profile = await get_user_field_profile(clerk_user_id, field)
    if not profile:
        return {}  # Blank form for new field
    return profile


@router.delete("/delete_user/{clerk_user_id}", tags=["User Management"])
async def delete_user(clerk_user_id: str):
    try:
        result = await user_profiles_collection.delete_one({"clerk_user_id": clerk_user_id})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="User not found")
        return {"detail": "User deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/update_user/{clerk_user_id}", tags=["User Management"])
async def update_user(clerk_user_id: str, update_data: dict = Body(...)):
    try:
        if not update_data:
            raise HTTPException(status_code=400, detail="No update data provided")
        result = await user_profiles_collection.update_one(
            {"clerk_user_id": clerk_user_id},
            {"$set": update_data},
        )
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="User not found or no changes")
        updated = await user_profiles_collection.find_one({"clerk_user_id": clerk_user_id})
        if updated:
            updated["_id"] = str(updated["_id"])
        return updated
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Resume Generation
# ---------------------------------------------------------------------------
@router.post("/generate_resume")
async def generate_resume(request: GenerateResumeRequest):
    try:
        profile = request.user_profile.dict()
        clerk_id = profile["clerk_user_id"]
        field = profile.get("professional_field", "general")

        # Check free tier field limit
        if not await can_use_field(clerk_id, field):
            raise HTTPException(
                status_code=403,
                detail=f"Free tier allows only {FREE_FIELD_LIMIT} field types. Upgrade to Pro for unlimited fields."
            )

        compound_filter = {
            "clerk_user_id": clerk_id,
            "professional_field": field,
        }
        existing = await user_profiles_collection.find_one(compound_filter)
        if not existing:
            await user_profiles_collection.insert_one(profile)
        else:
            # Update this field-specific profile
            await user_profiles_collection.update_one(
                compound_filter,
                {"$set": {
                    k: v for k, v in profile.items()
                    if k not in ("clerk_user_id", "professional_field", "generated_cvs")
                }},
            )
        pdf_url = await process_resume_generation(profile, cv_type="original")
        return {"pdf_url": pdf_url}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.post("/generate_tailored_cv")
async def generate_tailored_cv(request: TailoredResumeRequest):
    try:
        # Check shared tailor credits
        remaining = await get_total_tailor_credits(request.clerk_user_id)
        if remaining <= 0:
            raise HTTPException(
                status_code=402,
                detail="No AI tailor credits remaining. Upgrade to Pro for more credits."
            )

        pdf_url = await process_tailored_resume(request.clerk_user_id, request.job_description)

        # Decrement shared credits
        new_remaining = await decrement_tailor_credits(request.clerk_user_id)

        return {
            "pdf_url": pdf_url,
            "remaining_credits": new_remaining,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---------------------------------------------------------------------------
# User Limits & Credits (for frontend gating)
# ---------------------------------------------------------------------------
@router.get("/user_limits/{clerk_user_id}", tags=["Limits"])
async def get_user_limits(clerk_user_id: str):
    """Return the user's current usage vs free tier limits."""
    used_fields = await get_user_used_fields(clerk_user_id)
    tailor_credits = await get_total_tailor_credits(clerk_user_id)
    return {
        "used_fields": used_fields,
        "field_limit": FREE_FIELD_LIMIT,
        "fields_remaining": max(0, FREE_FIELD_LIMIT - len(used_fields)),
        "tailor_credits": tailor_credits,
    }


# ---------------------------------------------------------------------------
# Fetch All Profiles (for My Resumes — live rendering)
# ---------------------------------------------------------------------------
@router.get("/user_profiles/{clerk_user_id}", tags=["Profiles"])
async def get_all_user_profiles(clerk_user_id: str):
    """Return all field profiles for a user so frontend can render them live."""
    cursor = user_profiles_collection.find({"clerk_user_id": clerk_user_id})
    profiles = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        profiles.append(doc)
    return {"profiles": profiles}


# ---------------------------------------------------------------------------
# Fetch CVs (legacy — stored PDF records)
# ---------------------------------------------------------------------------
@router.get("/allcvs/{clerk_user_id}")
async def get_all_cvs(clerk_user_id: str):
    profile = await get_user_profile(clerk_user_id)
    return {"clerk_user_id": clerk_user_id, "cvs": profile.get("generated_cvs", [])}


@router.get("/originalcv/{clerk_user_id}")
async def get_original_cv(clerk_user_id: str):
    profile = await get_user_profile(clerk_user_id)
    original = next(
        (cv for cv in profile.get("generated_cvs", []) if cv.get("cv_type") == "original"),
        None,
    )
    if not original:
        raise HTTPException(status_code=404, detail="Original CV not found")
    return original


@router.get("/tailoredcv/{clerk_user_id}")
async def get_latest_tailored_cv(clerk_user_id: str):
    profile = await get_user_profile(clerk_user_id)
    tailored = [cv for cv in profile.get("generated_cvs", []) if cv.get("cv_type") == "tailored"]
    if not tailored:
        raise HTTPException(status_code=404, detail="Tailored CV not found")
    return max(tailored, key=lambda cv: cv.get("generated_at", ""))


# ---------------------------------------------------------------------------
# Proxy Download
# ---------------------------------------------------------------------------
@router.get("/proxy-download/")
async def proxy_download(pdf_url: str):
    try:
        async with httpx.AsyncClient() as http_client:
            resp = await http_client.get(pdf_url)
            resp.raise_for_status()
            return StreamingResponse(
                BytesIO(resp.content),
                media_type="application/pdf",
                headers={"Content-Disposition": "attachment; filename=Resume.pdf"},
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/download-resume/")
async def download_resume(resume_url: str):
    try:
        async with httpx.AsyncClient() as http_client:
            resp = await http_client.get(resume_url)
            resp.raise_for_status()
            return StreamingResponse(
                BytesIO(resp.content),
                media_type="application/pdf",
                headers={"Content-Disposition": "attachment; filename=Tailored_Resume.pdf"},
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Payments
# ---------------------------------------------------------------------------
@router.post("/create_payment_order", tags=["Payment"])
async def create_payment_order(request: PaymentRequest):
    tier_pricing = {
        "tier1": {"amount": 100, "credits": 100},
        "tier2": {"amount": 250, "credits": 500},
        "tier3": {"amount": 500, "credits": 1000},
    }
    if request.tier not in tier_pricing:
        raise HTTPException(status_code=400, detail="Invalid tier")
    amount = tier_pricing[request.tier]["amount"]
    order = await create_order(amount=amount, currency="INR", receipt=request.clerk_user_id)
    return {"order": order, "credits": tier_pricing[request.tier]["credits"]}


@router.post("/payment_callback", tags=["Payment"])
async def payment_callback(payload: dict = Body(...)):
    try:
        payment_id = payload.get("payment_id")
        order_id = payload.get("order_id")
        signature = payload.get("signature")
        clerk_user_id = payload.get("clerk_user_id")
        tier = payload.get("tier")

        await verify_payment(payment_id, order_id, signature)

        tier_credits = {"tier1": 100, "tier2": 500, "tier3": 1000}
        if tier not in tier_credits:
            raise HTTPException(status_code=400, detail="Invalid tier")

        await user_profiles_collection.update_one(
            {"clerk_user_id": clerk_user_id},
            {"$inc": {"tailored_cv_credits": tier_credits[tier]}},
        )
        return {"detail": "Payment verified and credits updated"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/")
async def root():
    return {"app": "Resume Builder V2", "status": "running"}
