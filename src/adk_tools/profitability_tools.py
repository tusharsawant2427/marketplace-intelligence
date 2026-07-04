"""Profitability tools — explain WHAT changed in a product's cost/price/fee inputs (read-only DB)."""
from sqlalchemy import text
from src.database.connection import async_session
from src.database.repository import ErpRepository


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
        async with async_session() as s:
            repo = ErpRepository(s)
            mrps = (await s.execute(text("""
                SELECT mrp, wef FROM saleable_mrps
                WHERE mrpable_id = :o AND mrpable_type LIKE '%OnlineSellingProduct'
                ORDER BY wef DESC LIMIT 8
            """), {"o": osp_id})).fetchall()
            fees = (await s.execute(text("""
                SELECT 'referral' AS kind, fee_percentage AS value, with_effect_from
                FROM amazon_referral_fees
                WHERE marketplace_id = :m AND (:n IS NULL OR node_id = :n)
                  AND with_effect_from >= DATE_SUB(NOW(), INTERVAL 180 DAY)
                UNION ALL
                SELECT 'closing', fee, with_effect_from FROM amazon_closing_fees
                WHERE with_effect_from >= DATE_SUB(NOW(), INTERVAL 180 DAY)
                  AND fulfillment_type_meta_data_id IN
                      (SELECT id FROM fulfillment_type_meta_data WHERE marketplace_id = :m)
                UNION ALL
                SELECT 'weight_handling', fee, with_effect_from FROM amazon_weight_handling_fees
                WHERE with_effect_from >= DATE_SUB(NOW(), INTERVAL 180 DAY)
                  AND fulfillment_type_meta_data_id IN
                      (SELECT id FROM fulfillment_type_meta_data WHERE marketplace_id = :m)
                ORDER BY with_effect_from DESC LIMIT 15
            """), {"m": marketplace_id, "n": node_id})).fetchall()
            cost = await repo.get_purchase_cost_breakdown_for_osp(osp_id)

        mrp_history = [{"mrp": float(r.mrp), "wef": str(r.wef)} for r in mrps]
        mrp_change = None
        if mrp_history:
            current = mrp_history[0]["mrp"]
            # most recent MRP that differs from the current value (the actual last change)
            prev = next((h for h in mrp_history[1:] if h["mrp"] != current), None)
            if prev:
                delta = current - prev["mrp"]
                mrp_change = {"from": prev["mrp"], "to": current, "delta": round(delta, 2),
                              "changed_on": mrp_history[0]["wef"],
                              "direction": "down" if delta < 0 else "up"}
            else:
                mrp_change = {"from": current, "to": current, "delta": 0.0, "direction": "unchanged"}

        return {
            "osp_id": osp_id,
            "mrp_history": mrp_history,
            "mrp_change": mrp_change,
            "purchase_cost": cost,
            "recent_fee_changes": [
                {"kind": r.kind, "value": float(r.value) if r.value is not None else None,
                 "with_effect_from": str(r.with_effect_from)} for r in fees],
        }
    except Exception as e:
        return {"status": "error", "message": f"Profit drivers failed for OSP {osp_id}: {e}"}
