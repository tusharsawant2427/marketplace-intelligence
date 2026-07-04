"""Listing Health tools — Amazon catalog content completeness + ERP listing state (read-only)."""
from src.services.sp_api_factory import build_sp_api
from src.services.amazon_sp_api_service import SpApiWriteOperationBlocked
from src.database.connection import async_session
from src.database.repository import ErpRepository


async def listing_health(asin: str, marketplace_id: int = 1) -> dict:
    """
    Health / content-quality check for an Amazon listing: image count, title presence/length, key
    attribute coverage and sales rank (from the Amazon catalog), plus the ERP listing/verification
    state. Use for 'why is my listing suppressed', 'missing images', 'listing quality score',
    'content completeness'.

    Args:
        asin: The Amazon ASIN.
        marketplace_id: Internal marketplace id (default 1 = Amazon-India).

    Returns a dict with a content-completeness score (0-100), the individual checks, the Amazon
    title/image count, and the ERP state (listing_state / verification_state / inactive reason).
    Note: live Amazon suppression detail needs the seller SKU (Listings Items API); when unavailable,
    suppression is inferred from ERP state and the catalog checks.
    """
    try:
        svc, amazon_marketplace_id = await build_sp_api(marketplace_id)
        cat = await svc.get_catalog_item(asin, amazon_marketplace_id)
        summary = (cat.get("summaries") or [{}])[0]
        images = ((cat.get("images") or [{}])[0]).get("images", [])
        attrs = cat.get("attributes", {})
        title = summary.get("itemName")

        checks = {
            "has_title": bool(title),
            "title_length_ok": bool(title) and len(title) >= 30,
            "has_multiple_images": len(images) >= 4,
            "has_brand": bool(attrs.get("brand")),
            "has_bullet_points": bool(attrs.get("bullet_point")),
            "has_description": bool(attrs.get("product_description")),
            "has_sales_rank": bool(cat.get("salesRanks")),
        }
        score = round(100.0 * sum(1 for v in checks.values() if v) / len(checks), 1)

        facts = None
        async with async_session() as session:
            facts = await ErpRepository(session).get_listing_erp_facts(asin)

        return {
            "asin": asin,
            "content_completeness_score": score,
            "checks": checks,
            "image_count": len(images),
            "title": title,
            "erp_state": None if not facts else {
                "listing_state": facts["listing_state"],
                "verification_state": facts["verification_state"],
                "inactive_status_reason_id": facts["inactive_status_reason_id"],
                "osp_name": facts["osp_name"],
            },
        }
    except SpApiWriteOperationBlocked:
        raise
    except Exception as e:
        return {"status": "error", "message": f"Listing health check failed for {asin}: {e}"}
