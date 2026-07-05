"""Inventory Intelligence tools — warehouse stock, reorder alerts, movers (read-only, via ERP API)."""
from src.clients.erp_api_client import ErpApiClient, ErpApiError


async def reorder_alerts(limit: int = 20) -> dict:
    """
    Titles whose stock has breached the reorder level (will/did go out of stock). Use for 'which
    products will go out of stock', 'reorder recommendation'.

    Args:
        limit: max rows (default 20).

    Returns {"count", "items": [{"title_id","title_name","re_order_level","stock_in_hand",
             "pending_po_qty","shortfall"}]} ordered by largest shortfall first.
    """
    try:
        return await ErpApiClient().reorder_alerts(limit)  # Laravel returns the finished shape
    except ErpApiError as e:
        return {"status": "error", "message": f"Reorder alerts failed: {e}"}


async def stock_for_osp(osp_id: int) -> dict:
    """
    Current warehouse stock for an OSP, summed across its constituent editions and warehouses.

    Args:
        osp_id: internal OnlineSellingProduct id.

    Returns {"osp_id","total_quantity","total_packed","by_edition":[{"edition_product_type_id",
             "quantity","packed"}]}.
    """
    try:
        return await ErpApiClient().stock_for_osp(osp_id)  # Laravel returns the finished shape
    except ErpApiError as e:
        return {"status": "error", "message": f"Stock lookup failed for OSP {osp_id}: {e}"}


async def movers(days: int = 30, direction: str = "fast", limit: int = 10) -> dict:
    """
    Fast- or slow-moving titles by units sold in the most recent `days` window of sales data.
    Use for 'fast-moving products', 'dead inventory' (direction='slow'). The window is relative to
    the latest sales date on record (the DB is a snapshot).

    Args:
        days: window size in days (default 30).
        direction: 'fast' (most sold) or 'slow' (least sold).
        limit: max rows (default 10).

    Returns {"window_days","direction","items":[{"title_id","item_name","units","revenue"}]}.
    """
    try:
        return await ErpApiClient().movers(days, direction, limit)  # Laravel returns the finished shape
    except ErpApiError as e:
        return {"status": "error", "message": f"Movers query failed: {e}"}
