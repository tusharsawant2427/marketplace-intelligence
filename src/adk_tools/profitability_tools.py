"""Profitability tools — explain WHAT changed in a product's cost/price/fee inputs (read-only, via ERP API)."""
from src.clients.erp_api_client import ErpApiClient, ErpApiError


async def profit_drivers(osp_id: int, marketplace_id: int = 1, node_id: int = None) -> dict:
    """
    Explain what is moving a product's profitability by surfacing recently-changed inputs: MRP
    history (a drop reduces profit), current purchase/printing cost, and recent Amazon fee-master
    changes (a fee hike reduces profit). Use for 'why did profit reduce', 'which fees increased',
    'what's impacting my margin'.

    Args:
        osp_id: internal OnlineSellingProduct id.
        marketplace_id: internal marketplace id (default 1 = Amazon-India).
        node_id: category node id (optional; sharpens the referral-fee change lookup).

    Returns {"osp_id","mrp_history","mrp_change","purchase_cost","recent_fee_changes"}.
    """
    try:
        # Passthrough: Laravel computes mrp_change, purchase_cost and recent_fee_changes.
        return await ErpApiClient().profit_drivers(osp_id, marketplace_id, node_id)
    except ErpApiError as e:
        return {"status": "error", "message": f"Profit drivers failed for OSP {osp_id}: {e}"}
