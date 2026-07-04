from src.tools.fetch_listing_tool import FetchListingTool
from src.tools.fetch_pricing_tool import FetchPricingTool
from src.tools.fetch_charges_tool import FetchChargesTool
from src.contexts.listing_intelligence_context import ListingIntelligenceContext

class ListingIntelligenceService:
    """ Builds a pricing context for a given listing. """
    def __init__(self, ):
        self.listing_tool = FetchListingTool()
        self.pricing_tool = FetchPricingTool()
        self.charges_tool = FetchChargesTool()

    def build(self, request) -> ListingIntelligenceContext:
            
            listing = self.listing_tool.execute(request.listing_id)
            pricing = self.pricing_tool.execute(request.listing_id)
            charges = self.charges_tool.execute(request.listing_id)
            
            return ListingIntelligenceContext(
                    request=request,
                    listing=listing,
                    pricing=pricing,
                    charges=charges
            )