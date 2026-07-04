"""
Sample object graph.

This script exists to validate the domain model, not to run business
logic. If assembling this graph feels natural, the model is well shaped.
If it feels awkward, we adjust the model before writing any services.

    OnlineSellingProduct
    └── Platform (Amazon)
        └── Marketplace (India)
            ├── PricingScenario
            │   ├── FulfillmentStrategy
            │   ├── SellingInformation
            │   ├── MarketplaceFee
            │   ├── CostBreakdown
            │   └── ProfitAnalysis
            └── MarketplaceListing (after publishing)
"""

from src.domain.online_selling_product import OnlineSellingProduct
from src.domain.platform import Platform
from src.domain.marketplace import Marketplace
from src.domain.marketplace_listing import MarketplaceListing
from src.domain.pricing_scenario import PricingScenario
from src.domain.fulfillment_strategy import FulfillmentStrategy
from src.domain.selling_information import SellingInformation
from src.domain.marketplace_fee import MarketplaceFee
from src.domain.cost_breakdown import CostBreakdown
from src.domain.profit_analysis import ProfitAnalysis


def build_sample_graph() -> OnlineSellingProduct:
    # A single pricing scenario, assembled from its parts.
    scenario = PricingScenario(
        fulfillment_strategy=FulfillmentStrategy(
            fulfillment_type="FBA",
            selling_zone="Local",
        ),
        selling_information=SellingInformation(
            mrp=999.0,
            selling_price=799.0,
            customer_pays=799.0,
            delivery_charge=0.0,
            minimum_price=650.0,
        ),
        marketplace_fee=MarketplaceFee(
            commission_fee=80.0,
            fulfillment_fee=45.0,
            collection_fee=12.0,
            storage_fee=8.0,
            pick_pack_fee=15.0,
            total_platform_fee=160.0,
        ),
        cost_breakdown=CostBreakdown(
            purchase_cost=400.0,
            transport_cost=20.0,
            packaging_cost=10.0,
            advertisement_cost=30.0,
            royalty_cost=0.0,
        ),
        profit_analysis=ProfitAnalysis(
            gross_profit=179.0,
            profit_percentage=22.4,
            profit_per_item=179.0,
            break_even_price=620.0,
        ),
    )

    # The marketplace organizes scenarios and, once published, a listing.
    india = Marketplace(
        name="India",
        pricing_scenarios=[scenario],
        listing=MarketplaceListing(
            listing_id="2109",
            platform_listing_id="B0AMZN2109",
            status="ACTIVE",
        ),
    )

    # The platform organizes marketplaces.
    amazon = Platform(name="Amazon")
    amazon.marketplaces.append(india)

    # The product is the root aggregate across platforms.
    product = OnlineSellingProduct(
        product_id="P-1001",
        sku="SKU-1001",
        title="Wireless Earbuds",
        description="Bluetooth 5.3 earbuds with charging case.",
        brand="Acme",
        category="Electronics",
    )
    product.platforms.append(amazon)

    return product


def main():
    product = build_sample_graph()

    print(f"Product: {product.title} (sku={product.sku})")
    for platform in product.platforms:
        print(f"  Platform: {platform.name}")
        for marketplace in platform.marketplaces:
            listing = marketplace.listing
            listing_note = (
                f"listing {listing.listing_id} [{listing.status}]"
                if listing
                else "not published"
            )
            print(f"    Marketplace: {marketplace.name} ({listing_note})")
            for i, scenario in enumerate(marketplace.pricing_scenarios, start=1):
                fs = scenario.fulfillment_strategy
                pa = scenario.profit_analysis
                print(
                    f"      Scenario {i}: {fs.fulfillment_type}/{fs.selling_zone} "
                    f"-> profit {pa.gross_profit} ({pa.profit_percentage}%)"
                )


if __name__ == "__main__":
    main()
