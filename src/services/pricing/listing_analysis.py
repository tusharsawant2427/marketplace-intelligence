"""
Faithful port of pulse_erp's LpaCalculation + AmazonCharges: for a given listing price it
produces one fully-costed row per (fulfillment type x selling zone) — the Listing Price
Analysis (LPA) table — plus a header block.

Formulas verified against the ERP output for OSP 5 / Amazon-India / Educational book:
  net_platform_fee = (commission+fulfillment+fixed+collection+storage+pickpack) * 1.18
  advertisement    = saleable_mrp * advert% * 1.18
  purchase_gst     = Σ(cost*qty*moq*purchase_igst%)  (only when sale_gst == 0)
  gross_profit     = customer_pays - sale_gst - purchase_gst
                     - (transport + packaging + advert + royalty + net_platform_fee + purchase_cost)
  profit%          = gross_profit / saleable_mrp * 100
  profit_per_item  = gross_profit / no_of_item

NOTE: the raw fee-master values (referral/closing/weight-handling/storage/pick-pack) are looked up
live from this DB; a different fee snapshot yields different fee cells (the formula is unchanged).
"""
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.repository import ErpRepository

NET_PLATFORM_GST = 18.0
ADVERTISEMENT_GST = 18.0
ROYALTY_GST = 18.0
CUBIC_CM_PER_CUBIC_FOOT = 28316.846592
VOLUMETRIC_DIVISOR = 5000.0  # Amazon: (LxWxH cm) / 5000 = volumetric weight in kg
AMAZON_DEFAULT_ITEM_TYPE_ID = 2
ZONES = ("LOCAL", "REGIONAL", "NATIONAL")


class ListingAnalysisService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = ErpRepository(session)

    async def _scalar(self, sql: str, params: dict):
        row = (await self.session.execute(text(sql), params)).fetchone()
        return row

    async def analyze(
        self,
        osp_id: int,
        marketplace_id: int,
        node_id: int,
        listing_price: float,
        weight: float,
        length: float,
        width: float,
        height: float,
        marketplace_mrp: float = None,
        advertisement_charge_pct: float = None,
        listing_price_discount: float = 0.0,
        local_delivery_charge: float = 0.0,
        regional_delivery_charge: float = 0.0,
        national_delivery_charge: float = 0.0,
        step_level_name: str = "ADVANCED",
        zones: tuple = ZONES,
        now: datetime = None,
    ) -> dict:
        now = now or datetime.now()

        # ---- DB-derived context (shared across all rows) ----
        purchase_cost = await self.repo.get_purchase_cost_for_osp(osp_id, now)
        purchase_gst = await self.repo.get_purchase_gst_for_osp(osp_id, now)

        osp = await self._scalar(
            "SELECT name, osp_type, transport_per_kg_rate, packaging_charges, is_royalty "
            "FROM online_selling_products WHERE id = :o", {"o": osp_id})
        transport_rate = float(osp.transport_per_kg_rate) if osp and osp.transport_per_kg_rate else 0.0
        packaging_cost = float(osp.packaging_charges) if osp and osp.packaging_charges else 0.0

        saleable_mrp_row = await self._scalar(
            "SELECT mrp FROM saleable_mrps WHERE mrpable_id = :o AND mrpable_type LIKE '%OnlineSellingProduct' "
            "AND wef <= :now ORDER BY wef DESC LIMIT 1", {"o": osp_id, "now": now})
        saleable_mrp = float(saleable_mrp_row.mrp) if saleable_mrp_row else 0.0
        if marketplace_mrp is None:
            marketplace_mrp = saleable_mrp

        noi = await self._scalar(
            "SELECT SUM(d.quantity) noi FROM online_selling_product_details d "
            "JOIN online_selling_product_combinations c ON d.online_selling_product_combination_id = c.id "
            "WHERE c.online_selling_product_id = :o AND c.wef <= :now AND c.deleted_at IS NULL "
            "AND d.deleted_at IS NULL AND c.id = (SELECT id FROM online_selling_product_combinations "
            "WHERE online_selling_product_id = :o AND wef <= :now AND deleted_at IS NULL ORDER BY wef DESC LIMIT 1)",
            {"o": osp_id, "now": now})
        no_of_item = float(noi.noi) if noi and noi.noi else 1.0

        sale_igst_row = await self._scalar(
            "SELECT hc.igst FROM saleable_hsns sh JOIN hsn_codes hc ON sh.hsn_code_id = hc.id "
            "WHERE sh.hsnable_id = :o AND sh.hsnable_type LIKE '%OnlineSellingProduct' AND sh.type = 'SALE' "
            "AND sh.wef <= :now ORDER BY sh.wef DESC LIMIT 1", {"o": osp_id, "now": now})
        sale_igst = float(sale_igst_row.igst) if sale_igst_row and sale_igst_row.igst is not None else 0.0

        platform = await self._scalar(
            "SELECT p.id, p.name, p.advertisement_charge FROM marketplaces m "
            "JOIN platforms p ON m.platform_id = p.id WHERE m.id = :m", {"m": marketplace_id})
        platform_id = platform.id if platform else None
        if advertisement_charge_pct is None:
            advertisement_charge_pct = float(platform.advertisement_charge) if platform and platform.advertisement_charge else 0.0

        level_row = await self._scalar(
            "SELECT id FROM amazon_step_program_levels WHERE marketplace_id = :m AND name = :n LIMIT 1",
            {"m": marketplace_id, "n": step_level_name})
        level_id = level_row.id if level_row else None

        node_row = await self._scalar("SELECT name FROM nodes WHERE id = :n", {"n": node_id})
        node_name = node_row.name if node_row else None

        # weight the fees are computed on = max(actual, volumetric)
        volumetric_grams = (length * width * height) / VOLUMETRIC_DIVISOR * 1000.0 if all([length, width, height]) else 0.0
        weight_for_fee = max(weight or 0.0, volumetric_grams)

        # sale GST is backed out of the (GST-inclusive) listing price
        sale_gst = round(listing_price - (listing_price / (1.0 + sale_igst / 100.0)), 2) if sale_igst > 0 else 0.0
        # ERP: purchase GST only counts when the sale is GST-exempt
        effective_purchase_gst = purchase_gst if sale_gst == 0 else 0.0

        transport_cost = round((weight * 0.001) * transport_rate, 2)
        advert_base = saleable_mrp * (advertisement_charge_pct / 100.0)
        advertisement_cost = round(advert_base + advert_base * (ADVERTISEMENT_GST / 100.0), 2)
        discount_amount = round((marketplace_mrp * listing_price_discount) / 100.0, 2) if listing_price_discount > 0 else 0.0
        royalty_amount = 0.0  # OSP-level royalty base (0 unless is_royalty); GST would apply if > 0

        delivery_by_zone = {
            "LOCAL": local_delivery_charge, "REGIONAL": regional_delivery_charge, "NATIONAL": national_delivery_charge,
        }

        fulfillments = await self.repo.get_fulfillment_options(marketplace_id)

        rows = []
        for f in fulfillments:
            fmid = f["fulfillment_meta_id"]
            for zone in zones:
                delivery_charge = delivery_by_zone.get(zone, 0.0) or 0.0
                customer_pays = listing_price + delivery_charge

                commission = await self._referral_fee(marketplace_id, node_id, listing_price, now)
                collection = await self._closing_fee(fmid, node_id, listing_price, now)
                fulfillment_fee = await self._weight_handling_fee(
                    fmid, level_id, node_id, zone, weight_for_fee, customer_pays, now)
                pick_pack = await self._pick_pack_fee(fmid, level_id, weight_for_fee, now)
                storage = await self._storage_fee(fmid, length, width, height, now)
                fixed_fee = 0.0

                fee_sum = commission + fulfillment_fee + fixed_fee + collection + storage + pick_pack
                net_platform_fee = round(fee_sum + fee_sum * (NET_PLATFORM_GST / 100.0), 2)

                gross_profit = round(
                    customer_pays - sale_gst - effective_purchase_gst
                    - (transport_cost + packaging_cost + advertisement_cost + royalty_amount + net_platform_fee + purchase_cost),
                    2)
                profit_pct = round(gross_profit / saleable_mrp * 100.0, 2) if saleable_mrp else 0.0
                profit_per_item = round(gross_profit / no_of_item, 2) if no_of_item else 0.0

                rows.append({
                    "platform": platform.name if platform else None,
                    "marketplace": (await self._scalar("SELECT name FROM marketplaces WHERE id=:m", {"m": marketplace_id})).name,
                    "fulfillment_type": f["fulfillment_type"],
                    "node_name": node_name,
                    "selling_zone": zone.capitalize(),
                    "no_of_items": no_of_item,
                    "mrp": marketplace_mrp,
                    "listing_price": listing_price,
                    "delivery_charge": delivery_charge,
                    "commission": round(commission, 2),
                    "fulfillment_fees": round(fulfillment_fee, 2),
                    "fixed_fee": round(fixed_fee, 2),
                    "collection_fee": round(collection, 2),
                    "storage_fee": round(storage, 2),
                    "pick_pack": round(pick_pack, 2),
                    "net_platform_fee": net_platform_fee,
                    "discount_amount": discount_amount,
                    "sales_gst": sale_gst,
                    "purchase_cost": round(purchase_cost, 2),
                    "purchase_gst": effective_purchase_gst,
                    "transport_cost": transport_cost,
                    "packaging_cost": packaging_cost,
                    "advertisement_cost": advertisement_cost,
                    "royalty_amount": royalty_amount,
                    "gross_profit": gross_profit,
                    "profit_pct": profit_pct,
                    "profit_per_item": profit_per_item,
                })

        return {
            "header": {
                "listing_name": osp.name if osp else None,
                "osp_id": osp_id,
                "platform": platform.name if platform else None,
                "marketplace_id": marketplace_id,
                "node_id": node_id,
                "node_name": node_name,
                "step_level": step_level_name,
                "saleable_mrp": saleable_mrp,
                "marketplace_mrp": marketplace_mrp,
                "listing_price": listing_price,
                "weight": weight,
                "length": length, "width": width, "height": height,
                "purchase_cost": round(purchase_cost, 2),
                "no_of_item": no_of_item,
                "advertisement_charge_pct": advertisement_charge_pct,
            },
            "rows": rows,
        }

    # ---- fee lookups (faithful to the ERP Actions; latest with_effect_from wins) ----

    async def _referral_fee(self, marketplace_id, node_id, price, now) -> float:
        row = await self._scalar("""
            SELECT fee_percentage FROM amazon_referral_fees
            WHERE marketplace_id = :m AND node_id = :n AND min_value <= :p AND max_value >= :p
              AND with_effect_from <= :now ORDER BY with_effect_from DESC LIMIT 1
        """, {"m": marketplace_id, "n": node_id, "p": price, "now": now})
        return price * (float(row.fee_percentage) / 100.0) if row and row.fee_percentage is not None else 0.0

    async def _closing_fee(self, fmid, node_id, price, now) -> float:
        # node-specific row preferred over the generic (NULL node) row; exception category uses its own fee
        row = await self._scalar("""
            SELECT acf.fee, acf.fee_for_exception_category, n.is_exception_category_in_amazon AS exc
            FROM amazon_closing_fees acf LEFT JOIN nodes n ON n.id = :n
            WHERE acf.fulfillment_type_meta_data_id = :f AND acf.min_value <= :p AND acf.max_value >= :p
              AND (acf.node_id = :n OR acf.node_id IS NULL) AND acf.with_effect_from <= :now
            ORDER BY (acf.node_id = :n) DESC, acf.with_effect_from DESC LIMIT 1
        """, {"f": fmid, "n": node_id, "p": price, "now": now})
        if not row:
            return 0.0
        if row.exc and row.fee_for_exception_category is not None:
            return float(row.fee_for_exception_category)
        return float(row.fee) if row.fee is not None else 0.0

    async def _weight_handling_fee(self, fmid, level_id, node_id, zone, weight_for_fee, customer_pays, now) -> float:
        row = await self._scalar("""
            SELECT fee FROM amazon_weight_handling_fees
            WHERE fulfillment_type_meta_data_id = :f AND level_id = :lvl AND item_type_id = :it
              AND zone = :z AND min_weight_slab <= :w AND max_weight_slab >= :w
              AND min_price <= :cp AND max_price >= :cp AND (node_id = :n OR node_id IS NULL)
              AND with_effect_from <= :now
            ORDER BY (node_id = :n) DESC, with_effect_from DESC LIMIT 1
        """, {"f": fmid, "lvl": level_id, "it": AMAZON_DEFAULT_ITEM_TYPE_ID, "z": zone,
              "w": weight_for_fee, "cp": customer_pays, "n": node_id, "now": now})
        return float(row.fee) if row and row.fee is not None else 0.0

    async def _pick_pack_fee(self, fmid, level_id, weight_for_fee, now) -> float:
        row = await self._scalar("""
            SELECT fee FROM amazon_pick_and_pack_fees
            WHERE fulfillment_type_meta_data_id = :f AND level_id = :lvl AND item_type_id = :it
              AND min_weight_slab <= :w AND max_weight_slab >= :w AND with_effect_from <= :now
            ORDER BY with_effect_from DESC LIMIT 1
        """, {"f": fmid, "lvl": level_id, "it": AMAZON_DEFAULT_ITEM_TYPE_ID, "w": weight_for_fee, "now": now})
        return float(row.fee) if row and row.fee is not None else 0.0

    async def _storage_fee(self, fmid, length, width, height, now) -> float:
        row = await self._scalar("""
            SELECT cost_per_cubic_foot FROM amazon_storage_fees
            WHERE fulfillment_type_meta_data_id = :f AND with_effect_from <= :now
            ORDER BY with_effect_from DESC LIMIT 1
        """, {"f": fmid, "now": now})
        if not row or row.cost_per_cubic_foot is None or not all([length, width, height]):
            return 0.0
        cubic_feet = (length * width * height) / CUBIC_CM_PER_CUBIC_FOOT
        return round(float(row.cost_per_cubic_foot) * cubic_feet, 2)
