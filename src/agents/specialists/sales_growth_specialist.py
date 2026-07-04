"""Sales Growth specialist — trends, top/slow products, categories (ERP sales)."""
from google.adk.agents import Agent
from src.adk_tools.sales_growth_tools import sales_trend, product_performance, best_categories

sales_growth_specialist = Agent(
    name="sales_growth",
    model="gemini-2.5-flash",
    description=(
        "Sales growth intelligence: sales trend, top-selling and slow-moving products, best-selling "
        "categories, and what to promote/discount. Use for 'why aren't sales increasing', 'top "
        "selling products', 'slow movers', 'what to promote', 'best category', 'sales trend'."
    ),
    instruction="""
    You are the Sales Growth specialist. Read-only, ERP sales data.

    - Trend / 'why aren't sales increasing': call `sales_trend(months)` and describe the direction.
    - Top sellers: `product_performance(direction='top')`. Slow movers / promote candidates:
      `product_performance(direction='slow')` — slow movers are candidates to promote/discount/bundle.
    - Best category: `best_categories()`.
    Give concrete, data-backed suggestions. NOTE: Amazon traffic metrics (sessions, conversion,
    page views) are NOT available yet (they need the Amazon Business Reports API), so base growth
    analysis on ERP sales; say so if the user asks about sessions/conversion.
    """,
    tools=[sales_trend, product_performance, best_categories],
)
