"""Listing Health tools — Amazon catalog content completeness + ERP listing state (read-only, via ERP API)."""
from src.clients.erp_api_client import ErpApiClient, ErpApiError


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
        # Passthrough: Laravel merges the Amazon catalog checks + ERP state and returns the score.
        # `erp_state` is null when no ERP listing matches the ASIN (still a 200).
        return await ErpApiClient().listing_health(marketplace_id, asin)
    except ErpApiError as e:
        return {"status": "error", "message": f"Listing health check failed for {asin}: {e}"}
