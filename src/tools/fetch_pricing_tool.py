from src.models.pricing import Pricing
from src.tools.base_tool import BaseTool
from src.utils.json_loader import load_json
class FetchPricingTool(BaseTool):
    """ Tool to fetch pricing data."""

    def execute(self, listing_id:str) -> Pricing:
        data = load_json("pricing.json")
        return Pricing(
            minimum_price=data["minimum_price"],
            selling_price=data["selling_price"],
            mrp=data["mrp"],
        )