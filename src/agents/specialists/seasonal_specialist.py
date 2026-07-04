"""Seasonal Intelligence specialist — calendar demand patterns."""
from google.adk.agents import Agent
from src.adk_tools.seasonal_tools import seasonal_pattern

seasonal_specialist = Agent(
    name="seasonal",
    model="gemini-2.5-flash",
    description=(
        "Seasonal demand intelligence from multi-year sales history: when demand peaks (exam season, "
        "back-to-school, festivals), and when to build inventory. Use for 'when should I increase "
        "inventory', 'exam/festival/holiday demand', 'seasonal trend', 'peak months'."
    ),
    instruction="""
    You are the Seasonal Intelligence specialist. Read-only, multi-year sales history.

    Call `seasonal_pattern(category, title_id)` (filter by category like 'XII' or 'MHT-CET', or a
    specific title). Report the peak months and the month-by-month demand, and translate it into an
    inventory-timing recommendation (e.g. "peaks Feb-May, build stock by January"). Base everything
    on the tool output.
    """,
    tools=[seasonal_pattern],
)
