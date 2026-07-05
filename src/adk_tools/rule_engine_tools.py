"""Rule Engine tool — deterministic policy checks for a proposed listing/price.

Inputs come from the ERP API; the deterministic evaluation (`evaluate_rules`) stays local — it is
pure policy logic with no secrets or data access.
"""
from src.clients.erp_api_client import ErpApiClient, ErpApiError
from src.services.rule_engine import evaluate_rules


async def check_listing_rules(osp_id: int, marketplace_id: int = None,
                              listing_price: float = None, margin_pct: float = None) -> dict:
    """
    Run the deterministic business rules against a proposed listing/price for an OSP. Rules:
    never below the minimum listing price, never above MRP, margin >= 8%, HSN present, royalty
    present (if royalty-bearing), title complete. Use to check whether something is allowed to be
    published or priced a certain way — this is policy, not opinion.

    Args:
        osp_id: internal OnlineSellingProduct id.
        marketplace_id: internal marketplace id (needed for the minimum-price floor check).
        listing_price: the proposed price to validate (optional).
        margin_pct: the resulting margin % (optional).

    Returns {"osp_id", "publishable": bool, "results": [{"rule","status","message"}], "inputs": {...}}.
    """
    try:
        inputs = await ErpApiClient().rule_inputs(osp_id, marketplace_id)  # inputs only, from ERP
    except ErpApiError as e:
        return {"status": "error", "message": f"Rule check failed for OSP {osp_id}: {e}"}
    # Deterministic policy eval stays local: min-price floor, MRP cap, 8% margin, HSN, royalty, title.
    outcome = evaluate_rules(inputs, listing_price=listing_price, margin_pct=margin_pct)
    return {"osp_id": osp_id, **outcome, "inputs": inputs}
