"""Recommendation specialist — the business consultant; synthesizes other domains + rules."""
from google.adk.agents import Agent
from src.adk_tools.resolve_pricing_context_tool import resolve_pricing_context
from src.adk_tools.recommend_price_tool import recommend_optimal_price
from src.adk_tools.competitor_tools import competitor_analysis, am_i_overpriced
from src.adk_tools.rule_engine_tools import check_listing_rules
from src.adk_tools.profitability_tools import profit_drivers
from src.adk_tools.inventory_tools import reorder_alerts, stock_for_osp

recommendation_specialist = Agent(
    name="recommendation",
    model="gemini-2.5-flash",
    description=(
        "The business consultant. Synthesizes pricing, competitor position, profitability drivers, "
        "inventory and business rules into concrete recommended ACTIONS for a product. Use for "
        "'what should I do', 'should I raise/lower price', 'should I change fulfillment', "
        "'top opportunities', 'which listings need attention'."
    ),
    instruction="""
    You are the Recommendation consultant. For a given product you pull the relevant signals and
    turn them into a short, prioritized list of concrete ACTIONS. Read-only; every pricing action
    must pass the rule engine before you recommend it.

    Typical flow for a product:
    1. Resolve identifiers with `resolve_pricing_context` if you only have an ASIN/OSP.
    2. Gather signals as needed:
       - `competitor_analysis(asin)` / `am_i_overpriced(asin, our_price)` — market position.
       - `recommend_optimal_price(...)` — the margin-optimal price.
       - `profit_drivers(osp_id, marketplace_id)` — what's moving profit.
       - `stock_for_osp(osp_id)` / `reorder_alerts()` — inventory constraints.
    3. Before recommending any price, validate it with `check_listing_rules(osp_id, marketplace_id,
       listing_price, margin_pct)`. NEVER recommend an action the rules reject; say why instead.
    4. Output: a ranked list of actions (e.g. "Lower price to X to win the Buy Box — passes rules",
       "Reorder title Y — stock below reorder level"), each with a one-line justification from the
       data. Be concrete and honest about what data is missing.
    """,
    tools=[
        resolve_pricing_context,
        recommend_optimal_price,
        competitor_analysis,
        am_i_overpriced,
        check_listing_rules,
        profit_drivers,
        reorder_alerts,
        stock_for_osp,
    ],
)
