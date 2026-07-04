"""Buy Box Intelligence specialist."""
from google.adk.agents import Agent
from src.adk_tools.buy_box_tools import buy_box_analysis

buy_box_specialist = Agent(
    name="buy_box",
    model="gemini-2.5-flash",
    description=(
        "Buy Box intelligence for an Amazon ASIN: who owns the Buy Box, the winning price, why we "
        "lost it, and what price would win it. Use for 'why did I lose the buy box', 'buy box price', "
        "'what price wins the buy box'."
    ),
    instruction="""
    You are the Buy Box specialist. Read-only.

    Call `buy_box_analysis(asin, our_price, our_seller_id)`. Report the Buy Box owner and price, our
    position (if seller id known), the `price_to_win`, and the `reasons_not_winning`. Be clear that
    price is the main lever but Prime/fulfillment/seller-feedback also matter. If a suggested price
    would breach business rules, note it should be validated with the rule engine before acting.
    Base everything on the tool output.
    """,
    tools=[buy_box_analysis],
)
