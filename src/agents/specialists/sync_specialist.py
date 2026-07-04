"""Marketplace Sync specialist — ERP vs Amazon mismatch detection."""
from google.adk.agents import Agent
from src.adk_tools.sync_tools import sync_check

sync_specialist = Agent(
    name="marketplace_sync",
    model="gemini-2.5-flash",
    description=(
        "Synchronization between ERP and Amazon: detect price/MRP/dimension/weight/title mismatches "
        "and whether Amazon has changed a listing. Use for 'has Amazon changed my listing', "
        "'price mismatch', 'MRP mismatch', 'dimension/weight mismatch'."
    ),
    instruction="""
    You are the Marketplace Sync specialist. Read-only.

    Call `sync_check(asin)` and produce a short synchronization report: list each mismatch
    (field, ERP value, Amazon value); note any ERP fields that are not set (reported as
    `erp_values_missing`) — those are gaps to fill, not mismatches; and state whether the listing is
    in sync. Show the title comparison for context.

    You need an ASIN. Base everything on the tool output; never guess values.
    """,
    tools=[sync_check],
)
