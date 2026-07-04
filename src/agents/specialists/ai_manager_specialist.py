"""AI Marketplace Manager — top-level strategist that produces a business plan from a goal."""
from google.adk.agents import Agent
from src.adk_tools.sales_growth_tools import sales_trend, product_performance
from src.adk_tools.seasonal_tools import seasonal_pattern
from src.adk_tools.growth_intel_tools import growth_opportunities
from src.adk_tools.inventory_tools import reorder_alerts
from src.adk_tools.competitor_tools import competitor_analysis
from src.adk_tools.recommend_price_tool import recommend_optimal_price
from src.adk_tools.resolve_pricing_context_tool import resolve_pricing_context

ai_manager_specialist = Agent(
    name="ai_manager",
    model="gemini-2.5-flash",
    description=(
        "The AI Marketplace Manager — a strategist for goal-driven questions like 'how can I "
        "increase sales this month by 15%'. It orchestrates sales, seasonal, inventory, pricing and "
        "competitor signals into ONE prioritized business plan. Use for broad strategic goals, not "
        "single-product lookups."
    ),
    instruction="""
    You are the AI Marketplace Manager. Given a business GOAL (e.g. "increase sales 15% this month",
    "improve profit"), you build ONE concrete, prioritized business plan. Read-only.

    Orchestrate the relevant signals before answering:
    - `growth_opportunities()` — catalog-wide restock / fix / promote opportunities.
    - `sales_trend()` and `product_performance()` — momentum and top/slow products.
    - `seasonal_pattern(category)` — is the goal aligned with the season? Time actions accordingly.
    - `reorder_alerts()` — inventory that would block growth.
    - For specific high-value products, `resolve_pricing_context` + `recommend_optimal_price` and
      `competitor_analysis` to justify price/fulfillment moves.

    Then produce a plan: a short ranked list of initiatives, each with the action, the data
    justification, and the expected direction of impact (higher sales / higher profit). Be explicit
    about assumptions and about anything you could not quantify. Do not invent precise rupee figures
    you cannot derive from the tools.
    """,
    tools=[
        growth_opportunities,
        sales_trend,
        product_performance,
        seasonal_pattern,
        reorder_alerts,
        resolve_pricing_context,
        recommend_optimal_price,
        competitor_analysis,
    ],
)
