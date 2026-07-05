"""Listing Optimization tools — SEO score + Gemini-rewritten title/bullets/description.

Data (current catalog content) comes from the ERP API; the SEO-gap check and the Gemini rewrite stay
local (LLM generation, no secrets/data-access). This tool never edits the live listing.
"""
from google import genai
from src.clients.erp_api_client import ErpApiClient, ErpApiError

_MODEL = "gemini-2.5-flash"


def _seo_gaps(title: str, bullets: list, description: str) -> list[str]:
    gaps = []
    if len(title) < 50:
        gaps.append("Title is short (<50 chars) — add key attributes/keywords.")
    if len(bullets) < 5:
        gaps.append(f"Only {len(bullets)} bullet points — Amazon allows 5.")
    if not description:
        gaps.append("No description / A+ text.")
    return gaps


async def optimize_listing_content(asin: str, marketplace_id: int = 1) -> dict:
    """
    Suggest SEO-optimized listing content for an Amazon ASIN. Reads the current catalog title,
    bullet points and description, then uses Gemini to propose an improved, keyword-rich title,
    5 bullet points and a description following Amazon SEO best practices. Use for 'title
    optimization', 'keyword optimization', 'improve my bullet points/description', 'SEO score'.

    Args:
        asin: The Amazon ASIN.
        marketplace_id: internal marketplace id (default 1 = Amazon-India).

    Returns {"asin","current":{title,bullet_count,has_description},"suggestions": <text>,
             "seo_gaps":[...]}. Suggestions are AI-generated drafts for a human to review/publish —
             this tool never edits the live listing.
    """
    try:
        current = await ErpApiClient().catalog_content(marketplace_id, asin)  # data: from ERP
    except ErpApiError as e:
        return {"status": "error", "message": f"Listing optimization failed for {asin}: {e}"}

    title = current.get("title") or ""
    bullets = current.get("bullets") or []
    description = current.get("description") or ""
    brand = current.get("brand")

    seo_gaps = _seo_gaps(title, bullets, description)  # local

    prompt = f"""You are an Amazon SEO expert. Rewrite this listing following Amazon best
practices (keyword-rich but not stuffed, title <= 200 chars, exactly 5 benefit-led bullet points,
a concise scannable description). Product brand: {brand}.

CURRENT TITLE: {title}
CURRENT BULLETS: {bullets}
CURRENT DESCRIPTION: {description or '(none)'}

Return:
1. Optimized Title
2. 5 Optimized Bullet Points
3. Optimized Description
Keep claims consistent with the current content; do not invent specs."""

    try:
        client = genai.Client()  # local LLM, no secrets/DB
        resp = client.models.generate_content(model=_MODEL, contents=prompt)
    except Exception as e:
        return {"status": "error", "message": f"Listing optimization rewrite failed for {asin}: {e}"}

    return {
        "asin": asin,
        "current": {"title": title, "bullet_count": len(bullets), "has_description": bool(description)},
        "seo_gaps": seo_gaps,
        "suggestions": resp.text,
    }
