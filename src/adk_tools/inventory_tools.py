"""Inventory Intelligence tools — warehouse stock, reorder alerts, movers (read-only ERP DB)."""
from sqlalchemy import text
from src.database.connection import async_session


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
        async with async_session() as s:
            rows = (await s.execute(text("""
                SELECT title_id, title_name, re_order_level, stock_in_hand, order_qty, pending_po_qty
                FROM fact_title_re_order_levels
                WHERE is_breached = 1
                ORDER BY (re_order_level - stock_in_hand) DESC
                LIMIT :lim
            """), {"lim": limit})).fetchall()
        items = [{
            "title_id": r.title_id, "title_name": r.title_name,
            "re_order_level": r.re_order_level, "stock_in_hand": r.stock_in_hand,
            "pending_po_qty": r.pending_po_qty,
            "shortfall": (r.re_order_level or 0) - (r.stock_in_hand or 0),
        } for r in rows]
        return {"count": len(items), "items": items}
    except Exception as e:
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
        async with async_session() as s:
            rows = (await s.execute(text("""
                SELECT inv.edition_product_type_id AS ept, SUM(inv.quantity) AS qty,
                       SUM(inv.packed_quantity) AS packed
                FROM inventories inv
                WHERE inv.edition_product_type_id IN (
                    SELECT d.online_selling_productable_id
                    FROM online_selling_product_details d
                    JOIN online_selling_product_combinations c ON d.online_selling_product_combination_id = c.id
                    WHERE c.online_selling_product_id = :o AND c.deleted_at IS NULL AND d.deleted_at IS NULL
                      AND c.id = (SELECT id FROM online_selling_product_combinations
                                  WHERE online_selling_product_id = :o AND wef <= NOW() AND deleted_at IS NULL
                                  ORDER BY wef DESC LIMIT 1)
                )
                GROUP BY inv.edition_product_type_id
            """), {"o": osp_id})).fetchall()
        by_edition = [{"edition_product_type_id": r.ept, "quantity": int(r.qty or 0),
                       "packed": int(r.packed or 0)} for r in rows]
        return {
            "osp_id": osp_id,
            "total_quantity": sum(e["quantity"] for e in by_edition),
            "total_packed": sum(e["packed"] for e in by_edition),
            "by_edition": by_edition,
        }
    except Exception as e:
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

    Returns {"window_days","since","direction","items":[{"title_id","item_name","units","revenue"}]}.
    """
    try:
        order = "DESC" if direction == "fast" else "ASC"
        async with async_session() as s:
            rows = (await s.execute(text(f"""
                SELECT title_id, MAX(item_name) AS item_name, SUM(qty) AS units, SUM(amount) AS revenue
                FROM product_wise_net_sales_reports
                WHERE title_id IS NOT NULL
                  AND date >= (SELECT DATE_SUB(MAX(date), INTERVAL :d DAY) FROM product_wise_net_sales_reports)
                GROUP BY title_id
                ORDER BY units {order}
                LIMIT :lim
            """), {"d": days, "lim": limit})).fetchall()
        items = [{"title_id": r.title_id, "item_name": r.item_name,
                  "units": int(r.units or 0), "revenue": float(r.revenue or 0)} for r in rows]
        return {"window_days": days, "direction": direction, "items": items}
    except Exception as e:
        return {"status": "error", "message": f"Movers query failed: {e}"}
