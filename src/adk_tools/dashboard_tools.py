"""Executive Dashboard tools — business KPIs, risks and opportunities (read-only, via ERP API)."""
from src.clients.erp_api_client import ErpApiClient, ErpApiError


async def business_dashboard(days: int = 30) -> dict:
    """
    Founder/manager summary: sales KPIs for the recent window, top-selling titles (opportunities),
    and inventory reorder risks. Use for 'today's summary', 'business KPIs', 'top risks/opportunities',
    'revenue/profit impact', 'important alerts'.

    Args:
        days: sales window in days (default 30), relative to the latest sales date on record.

    Returns {"window_days","since","sales":{"units","revenue","orders"},
             "top_sellers":[{title_id,item_name,units,revenue}],
             "reorder_risk":{"breached_count","top":[{title_name,shortfall,stock_in_hand}]}}.
    """
    try:
        return await ErpApiClient().dashboard(days)  # Laravel returns the finished shape
    except ErpApiError as e:
        return {"status": "error", "message": f"Dashboard failed: {e}"}
