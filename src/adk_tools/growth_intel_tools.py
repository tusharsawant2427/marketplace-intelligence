"""Executive briefing + proactive Business-Growth opportunity finder (read-only ERP DB)."""
from sqlalchemy import text
from src.database.connection import async_session


async def morning_briefing(days: int = 7) -> dict:
    """
    CEO morning briefing: recent revenue/units, inventory alerts, and listings needing attention
    (suppressed/inactive/unverified). Use for 'morning briefing', 'today's summary', 'top risks',
    'CEO dashboard'.

    Args:
        days: recent window (default 7), relative to the latest sales date.

    Returns {"window_days","sales":{units,revenue,orders},"inventory_alerts":{breached_count},
             "listings_to_fix":{suppressed_or_inactive},"top_sellers":[...]}.
    """
    try:
        async with async_session() as s:
            sales = (await s.execute(text("""
                SELECT COALESCE(SUM(qty),0) units, COALESCE(SUM(amount),0) revenue,
                       COUNT(DISTINCT transaction_id) orders
                FROM product_wise_net_sales_reports
                WHERE date >= (SELECT DATE_SUB(MAX(date), INTERVAL :d DAY) FROM product_wise_net_sales_reports)
            """), {"d": days})).fetchone()
            breached = (await s.execute(text(
                "SELECT COUNT(*) c FROM fact_title_re_order_levels WHERE is_breached=1"))).fetchone()
            # Real marketplace-level listing counts (Amazon-India), NOT the ERP `listings` pipeline table.
            mkt = (await s.execute(text("""
                SELECT SUM(lm.state='ACTIVE') active, SUM(lm.state='INACTIVE') inactive
                FROM listing_marketplaces lm JOIN marketplaces m ON lm.marketplace_id=m.id
                WHERE m.name='Amazon-India' AND lm.deleted_at IS NULL
            """))).fetchone()
            top = (await s.execute(text("""
                SELECT MAX(item_name) item_name, SUM(qty) units FROM product_wise_net_sales_reports
                WHERE title_id IS NOT NULL
                  AND date >= (SELECT DATE_SUB(MAX(date), INTERVAL :d DAY) FROM product_wise_net_sales_reports)
                GROUP BY title_id ORDER BY units DESC LIMIT 3
            """), {"d": days})).fetchall()
        return {
            "window_days": days,
            "sales": {"units": int(sales.units), "revenue": float(sales.revenue), "orders": int(sales.orders)},
            "inventory_alerts": {"breached_count": int(breached.c)},
            "amazon_india_listings": {"active": int(mkt.active or 0), "inactive": int(mkt.inactive or 0)},
            "top_sellers": [{"item_name": r.item_name, "units": int(r.units)} for r in top],
        }
    except Exception as e:
        return {"status": "error", "message": f"Morning briefing failed: {e}"}


async def growth_opportunities() -> dict:
    """
    Proactively surface the top catalog-wide growth/profit opportunities: products to restock,
    listings to fix (suppressed/inactive), and slow movers to promote. Use for 'top opportunities',
    'what should I do to grow', 'where can I make more profit', 'which listings need attention'.

    Returns {"opportunities": [{"type","count","detail","examples":[...]}]} ranked by impact.
    """
    try:
        async with async_session() as s:
            restock = (await s.execute(text("""
                SELECT COUNT(*) c, (SELECT title_name FROM fact_title_re_order_levels WHERE is_breached=1
                    ORDER BY (re_order_level-stock_in_hand) DESC LIMIT 1) top
                FROM fact_title_re_order_levels WHERE is_breached=1
            """))).fetchone()
            # Real inactive Amazon-India marketplace listings (candidates to review for reactivation).
            inactive_mkt = (await s.execute(text("""
                SELECT COUNT(*) c FROM listing_marketplaces lm JOIN marketplaces m ON lm.marketplace_id=m.id
                WHERE m.name='Amazon-India' AND lm.state='INACTIVE' AND lm.deleted_at IS NULL
            """))).fetchone()
            slow = (await s.execute(text("""
                SELECT MAX(item_name) nm, SUM(qty) u FROM product_wise_net_sales_reports
                WHERE title_id IS NOT NULL
                  AND date >= (SELECT DATE_SUB(MAX(date), INTERVAL 90 DAY) FROM product_wise_net_sales_reports)
                GROUP BY title_id ORDER BY u ASC LIMIT 5
            """))).fetchall()

        opportunities = [
            {"type": "restock", "count": int(restock.c),
             "detail": "Products below reorder level — restock to avoid lost sales.",
             "examples": [restock.top] if restock.top else []},
            {"type": "review_inactive_amazon_listings", "count": int(inactive_mkt.c),
             "detail": "Inactive Amazon-India marketplace listings — review which should be reactivated. "
                       "(Per-listing suppression is confirmed on demand via the listing_health tool, not "
                       "in bulk.)"},
            {"type": "promote_slow_movers", "count": len(slow),
             "detail": "Slow-moving titles — consider promotion/discount/bundling.",
             "examples": [r.nm for r in slow[:3]]},
        ]
        opportunities.sort(key=lambda o: o["count"], reverse=True)
        return {"opportunities": opportunities}
    except Exception as e:
        return {"status": "error", "message": f"Growth opportunities failed: {e}"}
