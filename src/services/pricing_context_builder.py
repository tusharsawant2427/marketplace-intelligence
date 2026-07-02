from src.tools.fetch_listing_tool import FetchListingTool
from src.tools.fetch_pricing_tool import FetchPricingTool
from src.tools.fetch_charges_tool import FetchChargesTool
from src.contexts.pricing_analysis_context import PricingAnalysisContext

class PricingContextBuilder:
    """ Builds a pricing context for a given listing. """
    def build(self, request) -> PricingAnalysisContext:
            listing = FetchListingTool().execute(request.listing_id)
            pricing = FetchPricingTool().execute(request.listing_id)
            charges = FetchChargesTool().execute(request.listing_id)
            return PricingAnalysisContext(
                    request=request,
                    listing=listing,
                    pricing=pricing,
                    charges=charges
            )