"""Executive Intelligence specialist — CEO morning briefing."""
from google.adk.agents import Agent
from src.adk_tools.growth_intel_tools import morning_briefing

executive_specialist = Agent(
    name="executive",
    model="gemini-2.5-flash",
    description=(
        "CEO morning briefing: recent revenue, inventory alerts, listings needing attention and top "
        "sellers — a fast executive overview. Use for 'morning briefing', 'CEO dashboard', 'today's "
        "revenue/risks', 'what needs my attention'."
    ),
    instruction="""
    You are the Executive Intelligence briefing. Read-only.

    Call `morning_briefing()` and deliver a crisp executive briefing: headline revenue/units first,
    then Top Risks (inventory reorder breaches, listings suppressed/inactive), then top sellers as
    opportunities. Keep it short and scannable — a founder reads this in 30 seconds.
    """,
    tools=[morning_briefing],
)
