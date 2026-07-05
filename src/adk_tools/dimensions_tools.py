"""Fetch package weight + dimensions for an ASIN from the Amazon catalog (read-only, via ERP API)."""
from src.clients.erp_api_client import ErpApiClient, ErpApiError


async def get_package_dimensions(asin: str, marketplace_id: int = 1) -> dict:
    """
    Fetch the package weight (grams) and length/width/height (cm) for an Amazon ASIN from the
    catalog, so pricing/recommendation tools don't have to ask the user. Prefers package
    weight/dimensions, falls back to item weight/dimensions. Units are normalized to g / cm.

    Args:
        asin: The Amazon ASIN.
        marketplace_id: Internal marketplace id (default 1 = Amazon-India).

    Returns {"asin","weight","length","width","height","source"} or a status="error"/"not_found".
    Call this before recommend_optimal_price / analyze_listing when weight/dimensions are unknown.
    """
    try:
        # Passthrough: Laravel normalizes units (g/cm) and returns {"status":"not_found"} when the
        # catalog has none — surface that so pricing tools then ask the user for dimensions.
        return await ErpApiClient().dimensions(marketplace_id, asin)
    except ErpApiError as e:
        return {"status": "error", "message": f"Dimension lookup failed for {asin}: {e}"}
