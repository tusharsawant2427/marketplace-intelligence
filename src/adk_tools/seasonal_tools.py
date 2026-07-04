"""Seasonal Intelligence tools — calendar-month demand patterns from multi-year sales history."""
from sqlalchemy import text
from src.database.connection import async_session

_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


async def seasonal_pattern(category: str = None, title_id: int = None) -> dict:
    """
    Demand seasonality by calendar month across the sales history — which months peak (festival,
    exam, back-to-school). Use for 'when should inventory increase', 'exam/festival/holiday demand',
    'seasonal trend', 'back-to-school'.

    Args:
        category: optional course/sales-group filter (e.g. 'XII', 'MHT-CET').
        title_id: optional specific title to analyse.

    Returns {"scope","by_month":[{month,units,avg_per_year}],"peak_months":[...]}.
    """
    try:
        clauses = ["date >= '2018-01-01'"]
        params: dict = {}
        if title_id is not None:
            clauses.append("title_id = :t"); params["t"] = title_id
        if category:
            clauses.append("(course LIKE :c OR sales_group LIKE :c OR item_name LIKE :c)")
            params["c"] = f"%{category}%"
        where = " AND ".join(clauses)
        async with async_session() as s:
            rows = (await s.execute(text(f"""
                SELECT MONTH(date) AS m, SUM(qty) AS units, COUNT(DISTINCT YEAR(date)) AS years
                FROM product_wise_net_sales_reports
                WHERE {where}
                GROUP BY m ORDER BY m
            """), params)).fetchall()

        by_month = [{"month": _MONTHS[r.m - 1], "units": int(r.units or 0),
                     "avg_per_year": round((r.units or 0) / max(r.years or 1, 1))} for r in rows if r.m]
        peak = sorted(by_month, key=lambda x: x["avg_per_year"], reverse=True)[:3]
        return {
            "scope": {"category": category, "title_id": title_id},
            "by_month": by_month,
            "peak_months": [p["month"] for p in peak],
        }
    except Exception as e:
        return {"status": "error", "message": f"Seasonal analysis failed: {e}"}
