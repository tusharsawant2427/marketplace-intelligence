"""Executive briefing + proactive Business-Growth opportunity finder (read-only, via ERP API)."""
from src.clients.erp_api_client import ErpApiClient, ErpApiError


async def morning_briefing(days: int = 7) -> dict:
    """
    CEO morning briefing: recent revenue/units, inventory alerts, and listings needing attention
    (suppressed/inactive/unverified). Use for 'morning briefing', 'today's summary', 'top risks',
    'CEO dashboard'.

    Args:
        days: recent window (default 7), relative to the latest sales date.

    Returns {"window_days","sales":{units,revenue,orders},"inventory_alerts":{breached_count},
             "amazon_india_listings":{active,inactive},"top_sellers":[...]}.
    """
    try:
        return await ErpApiClient().morning_briefing(days)  # Laravel returns the finished shape
    except ErpApiError as e:
        return {"status": "error", "message": f"Morning briefing failed: {e}"}


async def growth_opportunities() -> dict:
    """
    Proactively surface the top catalog-wide growth/profit opportunities: products to restock,
    listings to fix (suppressed/inactive), and slow movers to promote. Use for 'top opportunities',
    'what should I do to grow', 'where can I make more profit', 'which listings need attention'.

    Returns {"opportunities": [{"type","count","detail","examples":[...]}]} ranked by impact.
    """
    try:
        return await ErpApiClient().growth_opportunities()  # Laravel returns the finished shape
    except ErpApiError as e:
        return {"status": "error", "message": f"Growth opportunities failed: {e}"}
