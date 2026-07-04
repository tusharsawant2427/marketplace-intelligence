"""Marketplace Expansion specialist — footprint, gaps, projected margin."""
from google.adk.agents import Agent
from src.adk_tools.expansion_tools import marketplace_expansion
from src.adk_tools.dimensions_tools import get_package_dimensions

expansion_specialist = Agent(
    name="expansion",
    model="gemini-2.5-flash",
    description=(
        "Marketplace expansion: where a product is and isn't listed, best marketplace, expected "
        "margin/commission, and launch readiness. Use for 'can this sell on Flipkart', 'best "
        "marketplace', 'expected margin', 'where should I launch'."
    ),
    instruction="""
    You are the Marketplace Expansion specialist. Read-only.

    Call `marketplace_expansion(osp_id, listing_price, weight, length, width, height)`. Report:
    - the current footprint (which platforms it's listed on and their state),
    - expansion gaps (fee-configured marketplaces where it is NOT yet listed),
    - the Amazon-India margin projection (best fulfillment/zone, gross profit, profit %, commission)
      when a price and weight/dimensions are provided.
    For the margin projection, fetch weight/dimensions with `get_package_dimensions(asin)` rather
    than asking the user; only ask for the price (or use the MRP). Relay the `note` honestly:
    non-Amazon (Flipkart/Meesho) margin projection is not yet available from the ERP API.
    """,
    tools=[marketplace_expansion, get_package_dimensions],
)
