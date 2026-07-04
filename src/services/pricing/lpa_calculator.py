from src.domain.pricing_scenario import PricingScenario
from src.domain.fulfillment_strategy import FulfillmentStrategy
from src.domain.selling_information import SellingInformation
from src.domain.marketplace_fee import MarketplaceFee
from src.domain.cost_breakdown import CostBreakdown
from src.domain.profit_analysis import ProfitAnalysis
from src.domain.erp_pricing_context import ErpPricingContext, AmazonFeeMasters
import math

class LpaCalculator:
    """
    Deterministic forward calculator replicating pulse_erp's LpaCalculation.
    """
    
    def calculate_amazon_scenario(
        self, 
        candidate_price: float, 
        context: ErpPricingContext, 
        fee_masters: AmazonFeeMasters,
        zone: str = "NATIONAL",
        fulfillment_type: str = "FBA"
    ) -> PricingScenario:
        
        # 1. GST Calculations (backing out GST from the inclusive candidate price)
        # Price = Base + (Base * GST%) => Base = Price / (1 + GST%)
        gst_fraction = context.sale_gst_percentage / 100.0
        base_price = candidate_price / (1.0 + gst_fraction)
        sale_gst_amount = candidate_price - base_price

        # 2. Marketplace Fees (Amazon)
        # a) Referral Fee
        referral_fee = 0.0
        for band in fee_masters.referral_fees:
            if band.min_value <= candidate_price <= band.max_value:
                referral_fee = candidate_price * (band.fee_percentage / 100.0)
                break
                
        # b) Closing Fee
        closing_fee = 0.0
        for band in fee_masters.closing_fees:
            if band.min_value <= candidate_price <= band.max_value:
                closing_fee = band.fee
                break
                
        # c) Weight Handling Fee
        weight_handling_fee = 0.0
        for slab in fee_masters.weight_handling_fees:
            if slab.zone == zone and slab.min_weight_slab <= context.weight_grams <= slab.max_weight_slab:
                # Simplified calculation: base fee + (weight / step) * additional_fee
                # Real logic might step through the slab. We will use a simplified flat fee for the slab.
                weight_handling_fee = slab.fee
                break

        # Platform GST (usually 18% on fees in India)
        platform_fee_gst_rate = 0.18
        total_platform_fee_base = referral_fee + closing_fee + weight_handling_fee
        platform_fee_gst = total_platform_fee_base * platform_fee_gst_rate
        total_platform_deduction = total_platform_fee_base + platform_fee_gst

        # 3. Product Costs
        transport_cost = (context.weight_grams / 1000.0) * context.transport_per_kg_rate
        advertisement_cost = context.mrp * (context.advertisement_percentage / 100.0)
        royalty_cost = candidate_price * (context.royalty_percentage / 100.0)
        
        total_cost = (
            context.purchase_cost + 
            context.packaging_cost + 
            transport_cost + 
            advertisement_cost + 
            royalty_cost
        )

        # Customer Pays
        customer_pays = candidate_price

        # Gross Profit
        # Settled amount from Amazon = Customer Pays - Total Platform Deduction
        settled_amount = customer_pays - total_platform_deduction
        
        # Net Profit = Settled Amount - Sale GST - Total Cost
        gross_profit = settled_amount - sale_gst_amount - total_cost
        
        profit_percentage = 0.0
        if candidate_price > 0:
            profit_percentage = (gross_profit / candidate_price) * 100.0

        # Construct the pricing scenario
        return PricingScenario(
            fulfillment_strategy=FulfillmentStrategy(
                fulfillment_type=fulfillment_type,
                selling_zone=zone
            ),
            selling_information=SellingInformation(
                mrp=context.mrp,
                selling_price=candidate_price,
                customer_pays=customer_pays,
                delivery_charge=0.0,
                minimum_price=0.0 # Will be populated by reverse calculator
            ),
            marketplace_fee=MarketplaceFee(
                commission_fee=referral_fee,
                fulfillment_fee=weight_handling_fee,
                collection_fee=closing_fee,
                storage_fee=0.0, # omitted for brevity
                pick_pack_fee=0.0, # omitted for brevity
                total_platform_fee=total_platform_deduction
            ),
            cost_breakdown=CostBreakdown(
                purchase_cost=context.purchase_cost,
                transport_cost=transport_cost,
                packaging_cost=context.packaging_cost,
                advertisement_cost=advertisement_cost,
                royalty_cost=royalty_cost
            ),
            profit_analysis=ProfitAnalysis(
                gross_profit=round(gross_profit, 2),
                profit_percentage=round(profit_percentage, 2),
                profit_per_item=round(gross_profit, 2),
                break_even_price=0.0 # Will be populated by reverse calculator
            )
        )
