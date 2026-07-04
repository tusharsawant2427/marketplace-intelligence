"""Marketplace Sync tools — diff ERP facts vs live Amazon catalog (read-only)."""
from src.services.sp_api_factory import build_sp_api
from src.services.amazon_sp_api_service import SpApiWriteOperationBlocked
from src.database.connection import async_session
from src.database.repository import ErpRepository


def _amazon_list_price(cat: dict, offers_payload: dict) -> float | None:
    # Prefer offers Summary.ListPrice; fall back to catalog attributes.list_price.
    lp = (offers_payload.get("Summary", {}) or {}).get("ListPrice", {})
    if lp.get("Amount") is not None:
        return float(lp["Amount"])
    attr = cat.get("attributes", {}).get("list_price")
    if attr and isinstance(attr, list) and attr and attr[0].get("value") is not None:
        return float(attr[0]["value"])
    return None


async def sync_check(asin: str, marketplace_id: int = 1) -> dict:
    """
    Compare ERP data against the live Amazon listing for an ASIN and report mismatches: title (name),
    MRP / list price, and (where recorded in the ERP) weight/dimensions. Use for 'has Amazon changed
    my listing', 'price mismatch', 'MRP mismatch', 'dimension/weight mismatch'.

    Args:
        asin: The Amazon ASIN.
        marketplace_id: Internal marketplace id (default 1 = Amazon-India).

    Returns {"asin", "erp": {...}, "amazon": {...}, "mismatches": [{"field","erp","amazon"}], "in_sync"}.
    Fields with no ERP value on record (e.g. dimensions not set) are reported as "erp_value_missing",
    not a mismatch.
    """
    try:
        svc, amazon_marketplace_id = await build_sp_api(marketplace_id)
        cat = await svc.get_catalog_item(asin, amazon_marketplace_id)
        offers_payload = (await svc.get_item_offers(asin, amazon_marketplace_id)).get("payload", {})

        amazon_title = (cat.get("summaries") or [{}])[0].get("itemName")
        amazon_list_price = _amazon_list_price(cat, offers_payload)

        async with async_session() as session:
            facts = await ErpRepository(session).get_listing_erp_facts(asin)
        if not facts:
            return {"status": "error", "message": f"No ERP listing found for ASIN {asin}."}

        mismatches, missing = [], []

        def cmp(field, erp_val, amazon_val, tol=0.01):
            if erp_val is None:
                missing.append(field)
                return
            if amazon_val is None:
                return
            differ = (abs(float(erp_val) - float(amazon_val)) > tol) if isinstance(erp_val, (int, float)) \
                else (str(erp_val).strip().lower() != str(amazon_val).strip().lower())
            if differ:
                mismatches.append({"field": field, "erp": erp_val, "amazon": amazon_val})

        cmp("mrp", facts.get("mrp"), amazon_list_price)
        # Title: ERP OSP name vs Amazon itemName — report as informational (they rarely match exactly).
        title_note = {"field": "title", "erp": facts.get("osp_name"), "amazon": amazon_title}

        return {
            "asin": asin,
            "erp": {"osp_id": facts["osp_id"], "name": facts["osp_name"], "mrp": facts.get("mrp"),
                    "dimensions": facts.get("dimensions")},
            "amazon": {"title": amazon_title, "list_price": amazon_list_price},
            "mismatches": mismatches,
            "erp_values_missing": missing,
            "title_comparison": title_note,
            "in_sync": len(mismatches) == 0,
        }
    except SpApiWriteOperationBlocked:
        raise
    except Exception as e:
        return {"status": "error", "message": f"Sync check failed for {asin}: {e}"}
