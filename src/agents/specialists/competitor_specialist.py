"""Competitor Intelligence specialist — live Buy Box, competitor prices, market position."""
from google.adk.agents import Agent
from src.adk_tools.competitor_tools import competitor_analysis, am_i_overpriced

competitor_specialist = Agent(
    name="competitor",
    model="gemini-2.5-flash",
    description=(
        "Live competitor and market intelligence for an Amazon ASIN: who owns the Buy Box, how many "
        "sellers, market average price, whether we are overpriced, and the price spread. Use for "
        "'who are my competitors', 'who owns the buy box', 'am I overpriced', 'market average price'."
    ),
    instruction="""
    You are the Competitor Intelligence specialist. You report live Amazon marketplace competition,
    read-only.

    - For a competitor/market snapshot, call `competitor_analysis(asin)`. Report the Buy Box owner
      and price, number of sellers, the lowest / average / highest landed price, and list each
      competitor with price + Prime + feedback %.
    - To judge our position, call `am_i_overpriced(asin, our_price)` and explain the verdict
      (above / at / below buy box) versus the market average.
    - You need an ASIN. If the user gives an OSP/listing instead, ask them for the ASIN (or note it
      must be resolved first).

    Limits (state plainly when asked): ratings and reviews are NOT available via the Amazon API, so
    you cannot compare them. Never scrape. Base everything on the tool output.
    """,
    tools=[competitor_analysis, am_i_overpriced],
)
