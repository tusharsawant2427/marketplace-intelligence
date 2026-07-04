"""Marketplace Copilot — launch-readiness orchestration for a single product."""
from google.adk.agents import Agent
from src.adk_tools.resolve_pricing_context_tool import resolve_pricing_context
from src.adk_tools.dimensions_tools import get_package_dimensions
from src.adk_tools.recommend_price_tool import recommend_optimal_price
from src.adk_tools.inventory_tools import stock_for_osp
from src.adk_tools.listing_health_tools import listing_health
from src.adk_tools.rule_engine_tools import check_listing_rules

copilot_specialist = Agent(
    name="copilot",
    model="gemini-2.5-flash",
    description=(
        "Marketplace Copilot: a launch-readiness check for a product ('launch this book'). "
        "Verifies pricing, inventory, listing quality, expected margin and business rules, then gives "
        "a ready-to-publish verdict. Use for 'launch this product', 'is this ready to publish', "
        "'launch readiness'."
    ),
    instruction="""
    You are the Marketplace Copilot. For 'launch this product / is it ready to publish', run a
    launch-readiness checklist and give a clear verdict. Read-only.

    Steps (resolve ids first with `resolve_pricing_context`, pass `asin` so dims auto-fetch):
    - Pricing & margin: `recommend_optimal_price(...)` — is a profitable price achievable?
    - Inventory: `stock_for_osp(osp_id)` — is stock available?
    - Listing quality: `listing_health(asin)` — content completeness score.
    - Policy: `check_listing_rules(osp_id, marketplace_id, listing_price, margin_pct)` — does it pass?

    Present a checklist (✓/✗ per item: Pricing, Inventory, Listing Score, Expected Margin, Rules) and
    a final verdict: "Ready to Publish" only if all critical checks pass and the rule engine allows
    it. If anything fails, say exactly what to fix. Base everything on tool output.
    """,
    tools=[
        resolve_pricing_context,
        get_package_dimensions,
        recommend_optimal_price,
        stock_for_osp,
        listing_health,
        check_listing_rules,
    ],
)
