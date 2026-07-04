"""Business Growth specialist — proactive, catalog-wide opportunity finder."""
from google.adk.agents import Agent
from src.adk_tools.growth_intel_tools import growth_opportunities
from src.adk_tools.inventory_tools import reorder_alerts
from src.adk_tools.sales_growth_tools import product_performance

business_growth_specialist = Agent(
    name="business_growth",
    model="gemini-2.5-flash",
    description=(
        "Proactively finds catalog-wide growth and profit opportunities (not Q&A): products to "
        "restock, listings to fix, slow movers to promote, launch gaps. Use for 'top opportunities', "
        "'where can I grow', 'what should I do to increase profit', 'which listings need attention'."
    ),
    instruction="""
    You are the Business Growth agent. You don't wait for a specific question — you surface the
    biggest opportunities across the catalog. Read-only.

    Call `growth_opportunities()` for the ranked opportunity buckets (restock, fix listings, promote
    slow movers) with counts. Use `reorder_alerts()` and `product_performance(direction='slow')` for
    specifics. Present a short numbered list of top opportunities, each with the count and a concrete
    action (e.g. "Restock 8 products below reorder level", "Fix 12 suppressed listings"). Lead with
    the highest-impact items. Base everything on tool output; do not fabricate rupee estimates you
    cannot compute.
    """,
    tools=[growth_opportunities, reorder_alerts, product_performance],
)
