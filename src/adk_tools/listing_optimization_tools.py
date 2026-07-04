"""Listing Optimization tools — SEO score + Gemini-rewritten title/bullets/description."""
from google import genai
from src.services.sp_api_factory import build_sp_api
from src.services.amazon_sp_api_service import SpApiWriteOperationBlocked

_MODEL = "gemini-2.5-flash"


def _values(attr_list) -> list[str]:
    return [a.get("value") for a in (attr_list or []) if a.get("value")]


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
        svc, amazon_marketplace_id = await build_sp_api(marketplace_id)
        cat = await svc.get_catalog_item(asin, amazon_marketplace_id)
        summary = (cat.get("summaries") or [{}])[0]
        attrs = cat.get("attributes", {})
        title = summary.get("itemName") or ""
        bullets = _values(attrs.get("bullet_point"))
        description = " ".join(_values(attrs.get("product_description")))
        brand = (attrs.get("brand") or [{}])[0].get("value")

        seo_gaps = []
        if len(title) < 50:
            seo_gaps.append("Title is short (<50 chars) — add key attributes/keywords.")
        if len(bullets) < 5:
            seo_gaps.append(f"Only {len(bullets)} bullet points — Amazon allows 5.")
        if not description:
            seo_gaps.append("No description / A+ text.")

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

        client = genai.Client()
        resp = client.models.generate_content(model=_MODEL, contents=prompt)

        return {
            "asin": asin,
            "current": {"title": title, "bullet_count": len(bullets), "has_description": bool(description)},
            "seo_gaps": seo_gaps,
            "suggestions": resp.text,
        }
    except SpApiWriteOperationBlocked:
        raise
    except Exception as e:
        return {"status": "error", "message": f"Listing optimization failed for {asin}: {e}"}
