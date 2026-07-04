"""Sales Growth tools — trends, top/slow products, promotion candidates (read-only ERP DB)."""
from sqlalchemy import text
from src.database.connection import async_session


async def sales_trend(months: int = 6) -> dict:
    """
    Monthly sales trend (units + revenue) over the recent months, to see if sales are growing or
    slipping. Use for 'sales trend', 'why aren't sales increasing'.

    Args:
        months: number of trailing months (default 6), relative to the latest sales date on record.

    Returns {"months": [{"month","units","revenue"}]} oldest→newest.
    """
    try:
        async with async_session() as s:
            rows = (await s.execute(text("""
                SELECT DATE_FORMAT(date, '%Y-%m') AS month, SUM(qty) AS units, SUM(amount) AS revenue
                FROM product_wise_net_sales_reports
                WHERE date >= (SELECT DATE_SUB(MAX(date), INTERVAL :m MONTH) FROM product_wise_net_sales_reports)
                GROUP BY month ORDER BY month
            """), {"m": months})).fetchall()
        return {"months": [{"month": r.month, "units": int(r.units or 0), "revenue": float(r.revenue or 0)} for r in rows]}
    except Exception as e:
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
        order = "DESC" if direction == "top" else "ASC"
        async with async_session() as s:
            rows = (await s.execute(text(f"""
                SELECT title_id, MAX(item_name) AS item_name, SUM(qty) AS units, SUM(amount) AS revenue
                FROM product_wise_net_sales_reports
                WHERE title_id IS NOT NULL
                  AND date >= (SELECT DATE_SUB(MAX(date), INTERVAL :d DAY) FROM product_wise_net_sales_reports)
                GROUP BY title_id ORDER BY units {order} LIMIT :lim
            """), {"d": days, "lim": limit})).fetchall()
        return {"direction": direction, "window_days": days,
                "items": [{"title_id": r.title_id, "item_name": r.item_name,
                           "units": int(r.units or 0), "revenue": float(r.revenue or 0)} for r in rows]}
    except Exception as e:
        return {"status": "error", "message": f"Product performance failed: {e}"}


async def best_categories(days: int = 90, limit: int = 10) -> dict:
    """
    Best-selling categories (course/sales group) by units in the recent window. Use for
    'best-selling category', 'which category sells most'.

    Returns {"window_days","categories":[{category,units,revenue}]}.
    """
    try:
        async with async_session() as s:
            rows = (await s.execute(text("""
                SELECT COALESCE(NULLIF(course,''), sales_group, 'Unknown') AS category,
                       SUM(qty) AS units, SUM(amount) AS revenue
                FROM product_wise_net_sales_reports
                WHERE date >= (SELECT DATE_SUB(MAX(date), INTERVAL :d DAY) FROM product_wise_net_sales_reports)
                GROUP BY category ORDER BY units DESC LIMIT :lim
            """), {"d": days, "lim": limit})).fetchall()
        return {"window_days": days,
                "categories": [{"category": r.category, "units": int(r.units or 0),
                                "revenue": float(r.revenue or 0)} for r in rows]}
    except Exception as e:
        return {"status": "error", "message": f"Best categories failed: {e}"}
