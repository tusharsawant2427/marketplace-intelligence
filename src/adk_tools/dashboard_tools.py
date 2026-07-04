"""Executive Dashboard tools — business KPIs, risks and opportunities (read-only ERP DB)."""
from sqlalchemy import text
from src.database.connection import async_session


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
        async with async_session() as s:
            sales = (await s.execute(text("""
                SELECT COALESCE(SUM(qty),0) AS units, COALESCE(SUM(amount),0) AS revenue,
                       COUNT(DISTINCT transaction_id) AS orders,
                       (SELECT DATE_SUB(MAX(date), INTERVAL :d DAY) FROM product_wise_net_sales_reports) AS since
                FROM product_wise_net_sales_reports
                WHERE date >= (SELECT DATE_SUB(MAX(date), INTERVAL :d DAY) FROM product_wise_net_sales_reports)
            """), {"d": days})).fetchone()

            top = (await s.execute(text("""
                SELECT title_id, MAX(item_name) AS item_name, SUM(qty) AS units, SUM(amount) AS revenue
                FROM product_wise_net_sales_reports
                WHERE title_id IS NOT NULL
                  AND date >= (SELECT DATE_SUB(MAX(date), INTERVAL :d DAY) FROM product_wise_net_sales_reports)
                GROUP BY title_id ORDER BY units DESC LIMIT 5
            """), {"d": days})).fetchall()

            reorder = (await s.execute(text("""
                SELECT COUNT(*) AS breached FROM fact_title_re_order_levels WHERE is_breached = 1
            """))).fetchone()
            reorder_top = (await s.execute(text("""
                SELECT title_name, (re_order_level - stock_in_hand) AS shortfall, stock_in_hand
                FROM fact_title_re_order_levels WHERE is_breached = 1
                ORDER BY (re_order_level - stock_in_hand) DESC LIMIT 3
            """))).fetchall()

        return {
            "window_days": days,
            "since": str(sales.since) if sales else None,
            "sales": {"units": int(sales.units or 0), "revenue": float(sales.revenue or 0),
                      "orders": int(sales.orders or 0)} if sales else {},
            "top_sellers": [{"title_id": r.title_id, "item_name": r.item_name,
                             "units": int(r.units or 0), "revenue": float(r.revenue or 0)} for r in top],
            "reorder_risk": {
                "breached_count": int(reorder.breached or 0) if reorder else 0,
                "top": [{"title_name": r.title_name, "shortfall": int(r.shortfall or 0),
                         "stock_in_hand": int(r.stock_in_hand or 0)} for r in reorder_top],
            },
        }
    except Exception as e:
        return {"status": "error", "message": f"Dashboard failed: {e}"}
