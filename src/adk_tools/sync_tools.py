"""Marketplace Sync tools — diff ERP facts vs live Amazon catalog (read-only, via ERP API)."""
from src.clients.erp_api_client import ErpApiClient, ErpApiError


async def sync_check(asin: str, marketplace_id: int = 1) -> dict:
    """
    Compare ERP data against the live Amazon listing for an ASIN and report mismatches: title (name),
    MRP / list price, and (where recorded in the ERP) weight/dimensions. Use for 'has Amazon changed
    my listing', 'price mismatch', 'MRP mismatch', 'dimension/weight mismatch'.

    Args:
        asin: The Amazon ASIN.
        marketplace_id: Internal marketplace id (default 1 = Amazon-India).

    Returns {"asin", "erp": {...}, "amazon": {...}, "mismatches": [{"field","erp","amazon"}], "in_sync"}.
    Fields with no ERP value on record (e.g. dimensions not set) are reported as "erp_values_missing",
    not a mismatch.
    """
    try:
        # Passthrough: Laravel diffs ERP facts vs the live Amazon listing and returns the result.
        result = await ErpApiClient().sync_check(marketplace_id, asin)
    except ErpApiError as e:
        return {"status": "error", "message": f"Sync check failed for {asin}: {e}"}
    if result is None:
        # A6 returns a real 404 when there is no ERP listing for the ASIN — surface it, don't swallow.
        return {"status": "not_found", "asin": asin,
                "message": f"ASIN {asin} is not listed in the ERP."}
    return result
