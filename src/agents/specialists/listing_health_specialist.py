"""Listing Health specialist — content completeness, quality, suppression signals."""
from google.adk.agents import Agent
from src.adk_tools.listing_health_tools import listing_health

listing_health_specialist = Agent(
    name="listing_health",
    model="gemini-2.5-flash",
    description=(
        "Marketplace listing quality and health: content completeness, missing images/attributes, "
        "listing quality score, and suppression signals. Use for 'why is my listing suppressed', "
        "'missing images', 'listing quality score', 'content completeness'."
    ),
    instruction="""
    You are the Listing Health specialist. Read-only.

    Call `listing_health(asin)` and report: the content-completeness score, which checks failed
    (images, title, brand, bullet points, description, sales rank), the image count, and the ERP
    listing/verification state. Explain concretely what to fix to raise the score.

    You need an ASIN. If the listing is suppressed or inactive per the ERP state, say so and explain
    the likely cause. Be honest about limits: full live suppression detail requires the seller SKU
    (not always available); when it's missing, infer from the ERP state and the catalog checks.
    Base everything on the tool output.
    """,
    tools=[listing_health],
)
