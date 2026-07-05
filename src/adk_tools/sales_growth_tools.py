"""Sales Growth tools — trends, top/slow products, promotion candidates (read-only, via ERP API)."""
from src.clients.erp_api_client import ErpApiClient, ErpApiError


async def sales_trend(months: int = 6) -> dict:
    """
    Monthly sales trend (units + revenue) over the recent months, to see if sales are growing or
    slipping. Use for 'sales trend', 'why aren't sales increasing'.

    Args:
        months: number of trailing months (default 6), relative to the latest sales date on record.

    Returns {"months": [{"month","units","revenue"}]} oldest→newest.
    """
    try:
        return await ErpApiClient().sales_trend(months)  # Laravel returns the finished shape
    except ErpApiError as e:
        return {"status": "error", "message": f"Sales trend failed: {e}"}


async def product_performance(direction: str = "top", days: int = 90, limit: int = 10) -> dict:
    """
    Best- or worst-selling titles by units in the recent window. Use for 'top selling products',
    'slow-moving products', 'what should we promote' (direction='slow').

    Args:
        direction: 'top' (best sellers) or 'slow' (slow movers).
        days: window in days (default 90), relative to the latest sales date.
        limit: max rows (default 10).

    Returns {"direction","window_days","items":[{title_id,item_name,units,revenue}]}.
    """
    try:
        return await ErpApiClient().product_performance(direction, days, limit)  # finished shape
    except ErpApiError as e:
        return {"status": "error", "message": f"Product performance failed: {e}"}


async def best_categories(days: int = 90, limit: int = 10) -> dict:
    """
    Best-selling categories (course/sales group) by units in the recent window. Use for
    'best-selling category', 'which category sells most'.

    Returns {"window_days","categories":[{category,units,revenue}]}.
    """
    try:
        return await ErpApiClient().best_categories(days, limit)  # Laravel returns the finished shape
    except ErpApiError as e:
        return {"status": "error", "message": f"Best categories failed: {e}"}
