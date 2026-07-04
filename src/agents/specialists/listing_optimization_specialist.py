"""Listing Optimization specialist — SEO-optimized title/bullets/description (Gemini)."""
from google.adk.agents import Agent
from src.adk_tools.listing_optimization_tools import optimize_listing_content

listing_optimization_specialist = Agent(
    name="listing_optimization",
    model="gemini-2.5-flash",
    description=(
        "Improves listing content for sales/SEO: rewrites title, bullet points and description "
        "following Amazon SEO best practices, and flags SEO gaps. Use for 'title optimization', "
        "'keyword optimization', 'improve my bullets/description', 'SEO score', 'A+ content'."
    ),
    instruction="""
    You are the Listing Optimization specialist. You suggest improved content — you never edit the
    live listing (read-only).

    Call `optimize_listing_content(asin)`. Present the current state, the SEO gaps, and the AI-drafted
    optimized Title, 5 Bullet Points and Description as suggestions for the user to review and
    publish themselves. Make clear these are drafts and must be human-approved before going live.
    """,
    tools=[optimize_listing_content],
)
