from src.models.listing import Listing
from src.tools.base_tool import BaseTool
from src.utils.json_loader import load_json

class FetchListingTool(BaseTool):
    """Tool to fetch listing data."""

    def execute(self, listing_id:str) -> Listing:
        data = load_json("listing.json")
        return Listing(
            listing_id=data["listing_id"],
            marketplace_id=data["marketplace_id"],
            platform_unique_id=data["platform_unique_id"],
            title=data["title"],
            description=data["description"],
            status=data["status"],
            platform=data["platform"],
            platform_id=data["platform_id"],
            marketplace=data["marketplace"],
            category=data["category"],
            category_id=data["category_id"],
            inactive_reason=data["inactive_reason"]
        )