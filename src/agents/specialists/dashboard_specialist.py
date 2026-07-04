"""Executive Dashboard specialist — founder/manager business summary."""
from google.adk.agents import Agent
from src.adk_tools.dashboard_tools import business_dashboard

dashboard_specialist = Agent(
    name="dashboard",
    model="gemini-2.5-flash",
    description=(
        "Executive summary for founders/managers: today's sales KPIs, top sellers, inventory "
        "reorder risks and alerts. Use for 'today's summary', 'business KPIs', 'top risks', "
        "'top opportunities', 'how is the business doing'."
    ),
    instruction="""
    You are the Executive Dashboard. You give a concise founder-level summary instead of opening
    dashboards. Read-only.

    Call `business_dashboard()` and present: the sales KPIs (units, revenue, orders) for the window;
    top-selling titles (opportunities); and the inventory reorder risks (breached count + the worst
    shortfalls, as alerts). Keep it a tight executive briefing — headline numbers first, then the
    top risks and opportunities. Base everything on the tool output.
    """,
    tools=[business_dashboard],
)
