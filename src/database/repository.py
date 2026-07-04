import os
import httpx
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, bindparam
from src.domain.erp_pricing_context import ErpPricingContext, AmazonFeeMasters, ReferralFeeBand, ClosingFeeBand, WeightHandlingSlab
from src.services.amazon_marketplace import resolve_amazon_marketplace_id, platform_has_live_pricing

# --- Purchase-cost constants (mirror pulse_erp) ---
# Polymorphic class string for an edition product type (the constituents of an OSP bundle).
EDITION_PRODUCT_TYPE = "App\\Features\\Saleable\\Titles\\Edition\\Domains\\Models\\EditionProductType"
# master_edition_product_type_id values.
JUP_MASTER_ID = 1
BTB_MASTER_ID = 3
# BaseConstants::ADD_PO_PRICE_FOR_COVER — Rs. added to a JUP price to derive a BTB cover price.
ADD_PO_PRICE_FOR_COVER = 10.0


class ErpRepository:
    """
    Repository to fetch data from pulse_erp database using raw SQL for speed and simplicity.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_erp_pricing_context(self, osp_id: int) -> ErpPricingContext:
        """
        Fetches the pricing context for a given online_selling_product_id.
        """
        # Fetch OSP core details
        osp_query = text("""
            SELECT 
                id, 
                advertisement_charge, 
                transport_per_kg_rate, 
                packaging_charges 
            FROM online_selling_products 
            WHERE id = :osp_id
        """)
        osp_result = await self.session.execute(osp_query, {"osp_id": osp_id})
        osp_row = osp_result.fetchone()
        
        if not osp_row:
            raise ValueError(f"OnlineSellingProduct with ID {osp_id} not found.")

        # Try to parse string values, default to 0.0 if not present
        adv_charge = float(osp_row.advertisement_charge) if osp_row.advertisement_charge else 0.0
        transport_rate = float(osp_row.transport_per_kg_rate) if osp_row.transport_per_kg_rate else 0.0
        packaging_charge = float(osp_row.packaging_charges) if osp_row.packaging_charges else 0.0

        # Fetch MRP (Polymorphic)
        mrp_query = text("""
            SELECT mrp 
            FROM saleable_mrps 
            WHERE mrpable_id = :osp_id 
              AND mrpable_type LIKE '%OnlineSellingProduct'
            ORDER BY wef DESC LIMIT 1
        """)
        mrp_result = await self.session.execute(mrp_query, {"osp_id": osp_id})
        mrp_row = mrp_result.fetchone()
        mrp = float(mrp_row.mrp) if mrp_row else 500.0 # Default fallback

        # Fetch Weight (Polymorphic)
        weight_query = text("""
            SELECT weight 
            FROM dimensions 
            WHERE dimensionable_id = :osp_id 
              AND dimensionable_type LIKE '%OnlineSellingProduct'
            ORDER BY wef DESC LIMIT 1
        """)
        weight_result = await self.session.execute(weight_query, {"osp_id": osp_id})
        weight_row = weight_result.fetchone()
        weight_grams = float(weight_row.weight) if weight_row else 500.0

        # Fetch GST (Polymorphic saleable_hsns -> hsn_codes)
        gst_query = text("""
            SELECT hc.igst 
            FROM saleable_hsns sh
            JOIN hsn_codes hc ON sh.hsn_code_id = hc.id
            WHERE sh.hsnable_id = :osp_id 
              AND sh.hsnable_type LIKE '%OnlineSellingProduct'
              AND sh.type = 'SALE'
            ORDER BY sh.wef DESC LIMIT 1
        """)
        gst_result = await self.session.execute(gst_query, {"osp_id": osp_id})
        gst_row = gst_result.fetchone()
        sale_gst = float(gst_row.igst) if gst_row else 18.0

        # Fetch Royalty (Polymorphic)
        royalty_query = text("""
            SELECT amount, is_percentage 
            FROM saleable_royalty_details 
            WHERE royaltyable_id = :osp_id 
              AND royaltyable_type LIKE '%OnlineSellingProduct'
            LIMIT 1
        """)
        royalty_result = await self.session.execute(royalty_query, {"osp_id": osp_id})
        royalty_row = royalty_result.fetchone()
        royalty_percentage = 0.0
        if royalty_row and royalty_row.is_percentage:
            royalty_percentage = float(royalty_row.amount)

        # Calculate true purchase cost from OSP combinations and POs
        purchase_cost = await self.get_purchase_cost_for_osp(osp_id)

        return ErpPricingContext(
            mrp=mrp,
            weight_grams=weight_grams,
            sale_gst_percentage=sale_gst,
            purchase_cost=purchase_cost,
            packaging_cost=packaging_charge,
            transport_per_kg_rate=transport_rate,
            advertisement_percentage=adv_charge,
            royalty_percentage=royalty_percentage
        )

    async def get_purchase_cost_for_osp(self, osp_id: int, now: datetime = None) -> float:
        """
        Purchase cost of an OSP = sum over its current combination's details of
        `EditionProductType.initialPurchasePrice() * detail.quantity * osp.moq`,
        faithfully replicating pulse_erp. The constituents live in
        `online_selling_product_details` (polymorphic -> EditionProductType), NOT in the
        `saleable_online_selling_product_combinations` link table.
        """
        now = now or datetime.now()

        # Current combination = latest wef <= now, not soft-deleted (currentOspCombinations).
        combo_row = (await self.session.execute(text("""
            SELECT id FROM online_selling_product_combinations
            WHERE online_selling_product_id = :osp_id AND wef <= :now AND deleted_at IS NULL
            ORDER BY wef DESC LIMIT 1
        """), {"osp_id": osp_id, "now": now})).fetchone()
        if not combo_row:
            return 0.0

        # Minimum order quantity multiplier (NULL -> 1).
        moq_row = (await self.session.execute(
            text("SELECT moq FROM online_selling_products WHERE id = :osp_id"), {"osp_id": osp_id}
        )).fetchone()
        moq = float(moq_row.moq) if moq_row and moq_row.moq else 1.0

        details = (await self.session.execute(text("""
            SELECT online_selling_productable_type AS ptype,
                   online_selling_productable_id   AS pid,
                   quantity
            FROM online_selling_product_details
            WHERE online_selling_product_combination_id = :combo_id AND deleted_at IS NULL
        """), {"combo_id": combo_row.id})).fetchall()

        total = 0.0
        for d in details:
            # OSP bundles for this ERP are composed of EditionProductType constituents.
            if d.ptype != EDITION_PRODUCT_TYPE:
                continue
            ept = (await self.session.execute(text("""
                SELECT id, edition_id, master_edition_product_type_id AS mept
                FROM edition_product_types WHERE id = :id
            """), {"id": d.pid})).fetchone()
            if not ept:
                continue
            base = await self._ept_initial_purchase_price(ept.id, ept.edition_id, ept.mept, now)
            total += base * float(d.quantity) * moq

        return round(total, 2)

    async def get_purchase_cost_breakdown_for_osp(self, osp_id: int, now: datetime = None) -> dict:
        """
        Purchase cost with the per-saleable breakdown, e.g.
        {"total": 80.37, "moq": 1, "items": [{"label": "BTB - Feb2023(V HINDI WB)",
        "unit_cost": 31.17, "quantity": 1, "line_cost": 31.17}, ...]}.
        """
        now = now or datetime.now()
        combo_row = (await self.session.execute(text("""
            SELECT id FROM online_selling_product_combinations
            WHERE online_selling_product_id = :osp_id AND wef <= :now AND deleted_at IS NULL
            ORDER BY wef DESC LIMIT 1
        """), {"osp_id": osp_id, "now": now})).fetchone()
        if not combo_row:
            return {"total": 0.0, "moq": 1.0, "items": []}

        osp_row = (await self.session.execute(
            text("SELECT osp_type, moq FROM online_selling_products WHERE id = :o"), {"o": osp_id})).fetchone()
        moq = float(osp_row.moq) if osp_row and osp_row.osp_type == "MOQ" and osp_row.moq else 1.0

        details = (await self.session.execute(text("""
            SELECT online_selling_productable_type AS ptype, online_selling_productable_id AS pid, quantity
            FROM online_selling_product_details
            WHERE online_selling_product_combination_id = :c AND deleted_at IS NULL
        """), {"c": combo_row.id})).fetchall()

        items, total = [], 0.0
        for d in details:
            if d.ptype != EDITION_PRODUCT_TYPE:
                continue
            ept = (await self.session.execute(text("""
                SELECT ept.id, ept.edition_id, ept.master_edition_product_type_id AS mept,
                       mept.name AS master, e.name AS edition_name, t.name AS title_name
                FROM edition_product_types ept
                JOIN editions e ON ept.edition_id = e.id
                JOIN titles t ON e.title_id = t.id
                JOIN master_edition_product_types mept ON ept.master_edition_product_type_id = mept.id
                WHERE ept.id = :i
            """), {"i": d.pid})).fetchone()
            if not ept:
                continue
            unit_cost = await self._ept_initial_purchase_price(ept.id, ept.edition_id, ept.mept, now)
            line_cost = unit_cost * float(d.quantity) * moq
            items.append({
                "label": f"{ept.master} - {ept.edition_name}({ept.title_name})",
                "unit_cost": round(unit_cost, 2),
                "quantity": float(d.quantity),
                "line_cost": round(line_cost, 2),
            })
            total += line_cost
        return {"total": round(total, 2), "moq": moq, "items": items}

    async def _ept_initial_purchase_price(self, ept_id: int, edition_id: int, mept_id: int,
                                          now: datetime, depth: int = 0) -> float:
        """Port of EditionProductType::initialPurchasePrice() (recency + JUP + previous-edition fallbacks)."""
        price = await self._ept_price_as_per_year(ept_id, edition_id, mept_id, now, less_than_year=True)
        if price <= 0:
            price = await self._ept_price_as_per_year(ept_id, edition_id, mept_id, now, less_than_year=False)
        if price == 0 and depth < 5:
            # Fall back to the previous BTB edition of the same title (id < current).
            prev = (await self.session.execute(text("""
                SELECT ept.id, ept.edition_id, ept.master_edition_product_type_id AS mept
                FROM edition_product_types ept
                JOIN editions e2 ON ept.edition_id = e2.id AND ept.master_edition_product_type_id = :btb
                WHERE e2.title_id = (SELECT title_id FROM editions WHERE id = :edition_id)
                  AND e2.id < :edition_id
                ORDER BY e2.id DESC LIMIT 1
            """), {"btb": BTB_MASTER_ID, "edition_id": edition_id})).fetchone()
            if prev:
                price = await self._ept_initial_purchase_price(prev.id, prev.edition_id, prev.mept, now, depth + 1)
        return price

    async def _ept_price_as_per_year(self, ept_id: int, edition_id: int, mept_id: int,
                                     now: datetime, less_than_year: bool) -> float:
        """Port of EditionProductType::purchasePriceAsPerYear() for one recency window."""
        year_ago = now - timedelta(days=365)
        op = ">=" if less_than_year else "<"

        # Received items (PO not cancelled, production cost, poi.created_at within window), latest first by id.
        received = (await self.session.execute(text(f"""
            SELECT poi.unit_price_without_tax AS uwt,
                   poi.old_pulse_final_unit_price AS ofup,
                   r.id AS recv_id
            FROM purchase_order_item_receiveds r
            JOIN purchase_order_items poi ON r.purchase_order_item_id = poi.id
            JOIN purchase_orders po ON poi.purchase_order_id = po.id
            WHERE poi.saleable_type = :t AND poi.saleable_id = :i
              AND po.state != 'CANCELLED' AND poi.is_production_cost = 1
              AND poi.created_at {op} :cut
            ORDER BY r.id DESC
        """), {"t": EDITION_PRODUCT_TYPE, "i": ept_id, "cut": year_ago})).fetchall()

        # Latest production-cost PO item in the window (regardless of receiving), by id.
        last_consider = (await self.session.execute(text(f"""
            SELECT poi.unit_price_without_tax AS uwt
            FROM purchase_order_items poi
            JOIN purchase_orders po ON poi.purchase_order_id = po.id
            WHERE poi.saleable_type = :t AND poi.saleable_id = :i
              AND poi.is_production_cost = 1 AND po.state != 'CANCELLED'
              AND poi.created_at {op} :cut
            ORDER BY poi.id DESC LIMIT 1
        """), {"t": EDITION_PRODUCT_TYPE, "i": ept_id, "cut": year_ago})).fetchone()

        price = 0.0
        if received:
            recv_ids = [r.recv_id for r in received]
            invoice = (await self.session.execute(text("""
                SELECT unit_price_without_tax AS v
                FROM purchase_order_invoice_items
                WHERE purchase_order_item_received_id IN :ids
                ORDER BY id DESC LIMIT 1
            """).bindparams(bindparam("ids", expanding=True)), {"ids": recv_ids})).fetchone()
            if invoice and invoice.v is not None:
                price = float(invoice.v)                                   # invoiced: highest-id invoice item
            else:
                top = received[0]                                          # latest received item by id
                price = float(top.ofup) if top.ofup is not None else float(top.uwt)
        elif last_consider is not None and last_consider.uwt is not None:
            price = float(last_consider.uwt)
        else:
            # initial_po_price only applies in the older-than-a-year branch.
            if not less_than_year:
                ipp = (await self.session.execute(text("""
                    SELECT ipp.po_price AS v
                    FROM editions e
                    JOIN initial_po_price ipp ON ipp.old_pulse_edition_id = e.pulse_edition_id
                    WHERE e.id = :e ORDER BY ipp.date DESC LIMIT 1
                """), {"e": edition_id})).fetchone()
                if ipp and ipp.v is not None:
                    price = float(ipp.v)
            # Final fallback: JUP price + cover (only for non-JUP product types).
            if price <= 0 and mept_id != JUP_MASTER_ID:
                jup = (await self.session.execute(text("""
                    SELECT id, edition_id, master_edition_product_type_id AS mept
                    FROM edition_product_types
                    WHERE edition_id = :e AND master_edition_product_type_id = :j LIMIT 1
                """), {"e": edition_id, "j": JUP_MASTER_ID})).fetchone()
                if jup:
                    jup_price = await self._ept_price_as_per_year(jup.id, jup.edition_id, jup.mept, now, less_than_year)
                    if jup_price > 0:
                        price = jup_price + ADD_PO_PRICE_FOR_COVER
        return price

    async def get_amazon_marketplace_id(self, marketplace_id: int) -> str:
        """Resolve an internal ERP marketplace id to Amazon's SP-API global marketplace id string."""
        row = (await self.session.execute(text("""
            SELECT c.name AS country_name
            FROM marketplaces m JOIN countries c ON m.country_id = c.id
            WHERE m.id = :marketplace_id
        """), {"marketplace_id": marketplace_id})).fetchone()
        if not row:
            raise ValueError(f"Marketplace with ID {marketplace_id} not found.")
        return resolve_amazon_marketplace_id(row.country_name)

    async def get_amazon_fee_masters(self, marketplace_id: int, node_id: int, fulfillment_meta_id: int) -> AmazonFeeMasters:
        """
        Fetches Amazon fee masters for a specific context.
        """
        # Referral Fees
        ref_query = text("""
            SELECT min_value, max_value, fee_percentage 
            FROM amazon_referral_fees 
            WHERE marketplace_id = :marketplace_id 
              AND node_id = :node_id
            ORDER BY with_effect_from DESC
        """)
        ref_result = await self.session.execute(ref_query, {"marketplace_id": marketplace_id, "node_id": node_id})
        referral_fees = [
            ReferralFeeBand(min_value=row.min_value, max_value=row.max_value, fee_percentage=float(row.fee_percentage))
            for row in ref_result.fetchall()
        ]
        if not referral_fees:
            # Fallback for testing
            referral_fees = [ReferralFeeBand(min_value=0, max_value=999999, fee_percentage=15.0)]

        # Closing Fees
        close_query = text("""
            SELECT min_value, max_value, fee 
            FROM amazon_closing_fees 
            WHERE fulfillment_type_meta_data_id = :fulfillment_meta_id
            ORDER BY with_effect_from DESC
        """)
        close_result = await self.session.execute(close_query, {"fulfillment_meta_id": fulfillment_meta_id})
        closing_fees = [
            ClosingFeeBand(min_value=row.min_value, max_value=row.max_value, fee=float(row.fee))
            for row in close_result.fetchall()
        ]
        if not closing_fees:
            closing_fees = [ClosingFeeBand(min_value=0, max_value=999999, fee=20.0)]

        # Weight Handling Fees (simplified, grouping by min/max weight)
        weight_query = text("""
            SELECT zone, min_weight_slab, max_weight_slab, weight_slab_in_grams, fee 
            FROM amazon_weight_handling_fees 
            WHERE fulfillment_type_meta_data_id = :fulfillment_meta_id
            ORDER BY with_effect_from DESC
        """)
        weight_result = await self.session.execute(weight_query, {"fulfillment_meta_id": fulfillment_meta_id})
        weight_handling_fees = [
            WeightHandlingSlab(
                zone=row.zone, 
                min_weight_slab=row.min_weight_slab, 
                max_weight_slab=row.max_weight_slab, 
                weight_slab_step=row.weight_slab_in_grams, 
                fee=float(row.fee)
            )
            for row in weight_result.fetchall()
        ]
        if not weight_handling_fees:
            weight_handling_fees = [WeightHandlingSlab(zone="NATIONAL", min_weight_slab=0, max_weight_slab=99999, weight_slab_step=500, fee=60.0)]

        return AmazonFeeMasters(
            referral_fees=referral_fees,
            closing_fees=closing_fees,
            weight_handling_fees=weight_handling_fees
        )

    async def get_amazon_sp_credentials(self) -> dict:
        """
        Fetches the latest SP-API credentials from amazon_sp_settings.
        Refreshes the token if expired.
        """
        query = text("""
            SELECT id, access_token, refresh_token, expiry_date 
            FROM amazon_sp_settings 
            ORDER BY created_at DESC 
            LIMIT 1
        """)
        result = await self.session.execute(query)
        row = result.fetchone()
        
        if not row:
            raise ValueError("No SP-API credentials found in amazon_sp_settings table.")
            
        access_token = row.access_token
        refresh_token = row.refresh_token
        expiry_date = row.expiry_date
        
        # Check if expired
        if not expiry_date or expiry_date < datetime.now():
            # Refresh token
            client_id = os.getenv("AWS_SP_CLIENT_ID")
            client_secret = os.getenv("AWS_SP_CLIENT_SECRET")
            
            if not client_id or not client_secret:
                raise ValueError("Missing AWS_SP_CLIENT_ID or AWS_SP_CLIENT_SECRET in environment variables.")
                
            async with httpx.AsyncClient() as client:
                token_response = await client.post("https://api.amazon.com/auth/o2/token", json={
                    "grant_type": "refresh_token",
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "refresh_token": refresh_token
                })
                
                if token_response.status_code != 200:
                    raise ValueError(f"AWS-SP: Something went wrong while generating token. Status: {token_response.status_code}")
                    
                token_data = token_response.json()
                access_token = token_data.get("access_token")
                refresh_token = token_data.get("refresh_token", refresh_token)
                expires_in = token_data.get("expires_in", 3600)
                
                new_expiry = datetime.now() + timedelta(seconds=expires_in - 60)
                
                # Update DB
                update_query = text("""
                    UPDATE amazon_sp_settings 
                    SET access_token = :access_token, 
                        refresh_token = :refresh_token, 
                        expiry_date = :expiry_date,
                        updated_at = NOW()
                    WHERE id = :id
                """)
                await self.session.execute(update_query, {
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "expiry_date": new_expiry,
                    "id": row.id
                })
                await self.session.commit()
                
        return {
            "access_token": access_token,
            "refresh_token": refresh_token
        }

    # ------------------------------------------------------------------
    # Listing / identifier resolution (for proactive input gathering)
    # ------------------------------------------------------------------

    async def find_listings_by_platform_unique_id(self, platform_unique_id: str) -> list[dict]:
        """Find every listing whose platform id (ASIN/SKU) matches. May span platforms."""
        rows = (await self.session.execute(text("""
            SELECT l.id AS listing_id, l.online_selling_product_id AS osp_id,
                   l.platform_id, p.name AS platform_name, l.platform_unique_id, l.state
            FROM listings l JOIN platforms p ON l.platform_id = p.id
            WHERE l.platform_unique_id = :pid AND l.deleted_at IS NULL
            ORDER BY (l.state = 'ACTIVE') DESC, l.id DESC
        """), {"pid": platform_unique_id})).fetchall()
        return [dict(r._mapping) for r in rows]

    async def get_listing(self, listing_id: int) -> dict | None:
        row = (await self.session.execute(text("""
            SELECT l.id AS listing_id, l.online_selling_product_id AS osp_id,
                   l.platform_id, p.name AS platform_name, l.platform_unique_id, l.state
            FROM listings l JOIN platforms p ON l.platform_id = p.id
            WHERE l.id = :lid AND l.deleted_at IS NULL
        """), {"lid": listing_id})).fetchone()
        return dict(row._mapping) if row else None

    async def get_listing_marketplaces(self, listing_id: int) -> list[dict]:
        """Distinct marketplaces (with category node) a listing is on; one row per marketplace, ACTIVE preferred."""
        rows = (await self.session.execute(text("""
            SELECT lm.marketplace_id, m.name AS marketplace_name, m.platform_id,
                   lm.node_id, n.name AS node_name, lm.state
            FROM listing_marketplaces lm
            JOIN marketplaces m ON lm.marketplace_id = m.id
            LEFT JOIN nodes n ON lm.node_id = n.id
            WHERE lm.listing_id = :lid AND lm.deleted_at IS NULL
            ORDER BY (lm.state = 'ACTIVE') DESC, lm.marketplace_id
        """), {"lid": listing_id})).fetchall()
        # Collapse ACTIVE/INACTIVE history to one row per marketplace (ACTIVE wins via ORDER BY).
        seen, out = set(), []
        for r in rows:
            if r.marketplace_id in seen:
                continue
            seen.add(r.marketplace_id)
            out.append(dict(r._mapping))
        return out

    async def get_fulfillment_options(self, marketplace_id: int) -> list[dict]:
        """Active fulfillment options available on a marketplace (FBA, EasyShip, ...)."""
        rows = (await self.session.execute(text("""
            SELECT ftm.id AS fulfillment_meta_id, ft.name AS fulfillment_type
            FROM fulfillment_type_meta_data ftm
            JOIN fulfillment_types ft ON ftm.fulfillment_type_id = ft.id
            WHERE ftm.marketplace_id = :mid AND ftm.deleted_at IS NULL AND ft.state = 'ACTIVE'
            ORDER BY ftm.id
        """), {"mid": marketplace_id})).fetchall()
        return [dict(r._mapping) for r in rows]

    async def get_listings_for_osp(self, osp_id: int) -> list[dict]:
        """All platform listings for an OSP (used to suggest choices when only osp_id is known)."""
        rows = (await self.session.execute(text("""
            SELECT l.id AS listing_id, l.platform_id, p.name AS platform_name,
                   l.platform_unique_id, l.state
            FROM listings l JOIN platforms p ON l.platform_id = p.id
            WHERE l.online_selling_product_id = :osp AND l.deleted_at IS NULL
            ORDER BY (l.state IN ('ACTIVE','UPLOADED')) DESC, l.id
        """), {"osp": osp_id})).fetchall()
        out = []
        for r in rows:
            d = dict(r._mapping)
            d["has_live_pricing"] = platform_has_live_pricing(d["platform_name"])
            out.append(d)
        return out

    async def get_marketplace_platform(self, marketplace_id: int) -> dict | None:
        """Platform behind a marketplace + whether we have live-pricing integration for it."""
        row = (await self.session.execute(text("""
            SELECT m.id AS marketplace_id, m.name AS marketplace_name,
                   p.id AS platform_id, p.name AS platform_name
            FROM marketplaces m JOIN platforms p ON m.platform_id = p.id
            WHERE m.id = :mid
        """), {"mid": marketplace_id})).fetchone()
        if not row:
            return None
        d = dict(row._mapping)
        d["has_live_pricing"] = platform_has_live_pricing(d["platform_name"])
        return d

    async def get_marketplace_for_fulfillment(self, fulfillment_meta_id: int) -> int | None:
        """Back-track a fulfillment_meta_id to its marketplace (and thus platform)."""
        row = (await self.session.execute(text("""
            SELECT marketplace_id FROM fulfillment_type_meta_data WHERE id = :fid
        """), {"fid": fulfillment_meta_id})).fetchone()
        return int(row.marketplace_id) if row else None

    async def get_rule_inputs(self, osp_id: int, marketplace_id: int = None, now: datetime = None) -> dict:
        """
        Inputs the deterministic Rule Engine needs: MRP, minimum listing price, HSN presence,
        royalty flag/presence, and title completeness for an OSP (optionally on a marketplace).
        """
        now = now or datetime.now()
        osp = (await self.session.execute(
            text("SELECT name, is_royalty FROM online_selling_products WHERE id = :o"), {"o": osp_id})).fetchone()

        mrp_row = (await self.session.execute(text("""
            SELECT mrp FROM saleable_mrps WHERE mrpable_id = :o AND mrpable_type LIKE '%OnlineSellingProduct'
            AND wef <= :now ORDER BY wef DESC LIMIT 1
        """), {"o": osp_id, "now": now})).fetchone()

        min_price = None
        if marketplace_id is not None:
            mp = (await self.session.execute(text("""
                SELECT lm.minimum_listing_price FROM listing_marketplaces lm
                JOIN listings l ON lm.listing_id = l.id
                WHERE l.online_selling_product_id = :o AND lm.marketplace_id = :m AND lm.deleted_at IS NULL
                ORDER BY (lm.state = 'ACTIVE') DESC LIMIT 1
            """), {"o": osp_id, "m": marketplace_id})).fetchone()
            min_price = float(mp.minimum_listing_price) if mp and mp.minimum_listing_price is not None else None

        hsn = (await self.session.execute(text("""
            SELECT 1 FROM saleable_hsns WHERE hsnable_id = :o AND hsnable_type LIKE '%OnlineSellingProduct'
            AND type = 'SALE' LIMIT 1
        """), {"o": osp_id})).fetchone()

        royalty = (await self.session.execute(text("""
            SELECT 1 FROM saleable_royalty_details WHERE royaltyable_id = :o
            AND royaltyable_type LIKE '%OnlineSellingProduct' LIMIT 1
        """), {"o": osp_id})).fetchone()

        return {
            "osp_id": osp_id,
            "name": osp.name if osp else None,
            "mrp": float(mrp_row.mrp) if mrp_row else None,
            "minimum_listing_price": min_price,
            "has_hsn": bool(hsn),
            "is_royalty": bool(osp.is_royalty) if osp else False,
            "has_royalty_detail": bool(royalty),
        }

    async def get_listing_erp_facts(self, platform_unique_id: str, now: datetime = None) -> dict | None:
        """
        ERP-side facts for an Amazon listing (by platform id / ASIN), for Listing Health & Sync:
        listing/verification state, OSP name, saleable MRP, dimensions (if recorded), and the
        marketplace/category it's listed under. Returns None if no listing matches.
        """
        now = now or datetime.now()
        listing = (await self.session.execute(text("""
            SELECT l.id AS listing_id, l.online_selling_product_id AS osp_id, l.state AS listing_state,
                   l.verification_state, l.inactive_status_reason_id, p.name AS platform_name,
                   osp.name AS osp_name
            FROM listings l
            JOIN platforms p ON l.platform_id = p.id
            JOIN online_selling_products osp ON l.online_selling_product_id = osp.id
            WHERE l.platform_unique_id = :pid AND l.deleted_at IS NULL
            ORDER BY (l.state IN ('ACTIVE','UPLOADED')) DESC, l.id DESC LIMIT 1
        """), {"pid": platform_unique_id})).fetchone()
        if not listing:
            return None
        osp_id = listing.osp_id

        mrp_row = (await self.session.execute(text("""
            SELECT mrp FROM saleable_mrps
            WHERE mrpable_id = :o AND mrpable_type LIKE '%OnlineSellingProduct' AND wef <= :now
            ORDER BY wef DESC LIMIT 1
        """), {"o": osp_id, "now": now})).fetchone()

        dims = (await self.session.execute(text("""
            SELECT length, width, height, weight FROM dimensions
            WHERE dimensionable_id = :o AND dimensionable_type LIKE '%OnlineSellingProduct' AND wef <= :now
            ORDER BY wef DESC LIMIT 1
        """), {"o": osp_id, "now": now})).fetchone()

        mkt = (await self.session.execute(text("""
            SELECT lm.marketplace_id, m.name AS marketplace_name, lm.node_id, n.name AS node_name
            FROM listing_marketplaces lm
            JOIN marketplaces m ON lm.marketplace_id = m.id
            LEFT JOIN nodes n ON lm.node_id = n.id
            WHERE lm.listing_id = :lid AND lm.deleted_at IS NULL
            ORDER BY (lm.state = 'ACTIVE') DESC LIMIT 1
        """), {"lid": listing.listing_id})).fetchone()

        return {
            "listing_id": listing.listing_id,
            "osp_id": osp_id,
            "platform_name": listing.platform_name,
            "osp_name": listing.osp_name,
            "listing_state": listing.listing_state,
            "verification_state": listing.verification_state,
            "inactive_status_reason_id": listing.inactive_status_reason_id,
            "mrp": float(mrp_row.mrp) if mrp_row else None,
            "dimensions": ({"length": dims.length, "width": dims.width, "height": dims.height,
                            "weight": dims.weight} if dims else None),
            "marketplace_id": mkt.marketplace_id if mkt else None,
            "marketplace_name": mkt.marketplace_name if mkt else None,
            "node_id": mkt.node_id if mkt else None,
            "node_name": mkt.node_name if mkt else None,
        }

    async def get_supported_marketplaces(self) -> list[dict]:
        """Marketplaces we can price for (i.e. that have fee masters configured)."""
        rows = (await self.session.execute(text("""
            SELECT DISTINCT m.id AS marketplace_id, m.name AS marketplace_name, p.name AS platform_name
            FROM amazon_referral_fees arf
            JOIN marketplaces m ON arf.marketplace_id = m.id
            JOIN platforms p ON m.platform_id = p.id
            ORDER BY m.id
        """))).fetchall()
        out = []
        for r in rows:
            d = dict(r._mapping)
            d["has_live_pricing"] = platform_has_live_pricing(d["platform_name"])
            out.append(d)
        return out

    async def get_purchase_gst_for_osp(self, osp_id: int, now: datetime = None) -> float:
        """
        Input GST on the purchase cost = Σ over current-combination details of
        `initialPurchasePrice() * quantity * moq * purchase_igst%`. Mirrors pulse_erp's
        getPurchaseGst() (only meaningful when the sale is GST-exempt).
        """
        now = now or datetime.now()
        combo_row = (await self.session.execute(text("""
            SELECT id FROM online_selling_product_combinations
            WHERE online_selling_product_id = :osp_id AND wef <= :now AND deleted_at IS NULL
            ORDER BY wef DESC LIMIT 1
        """), {"osp_id": osp_id, "now": now})).fetchone()
        if not combo_row:
            return 0.0
        osp_row = (await self.session.execute(
            text("SELECT osp_type, moq FROM online_selling_products WHERE id = :o"), {"o": osp_id})).fetchone()
        moq = float(osp_row.moq) if osp_row and osp_row.osp_type == "MOQ" and osp_row.moq else 1.0
        details = (await self.session.execute(text("""
            SELECT online_selling_productable_type AS ptype, online_selling_productable_id AS pid, quantity
            FROM online_selling_product_details
            WHERE online_selling_product_combination_id = :c AND deleted_at IS NULL
        """), {"c": combo_row.id})).fetchall()

        total = 0.0
        for d in details:
            if d.ptype != EDITION_PRODUCT_TYPE:
                continue
            ept = (await self.session.execute(text("""
                SELECT id, edition_id, master_edition_product_type_id AS mept FROM edition_product_types WHERE id = :i
            """), {"i": d.pid})).fetchone()
            if not ept:
                continue
            cost = await self._ept_initial_purchase_price(ept.id, ept.edition_id, ept.mept, now)
            igst_row = (await self.session.execute(text("""
                SELECT hc.igst FROM saleable_hsns sh JOIN hsn_codes hc ON sh.hsn_code_id = hc.id
                WHERE sh.hsnable_id = :eid AND sh.hsnable_type LIKE '%Edition%' AND sh.type = 'PURCHASE'
                ORDER BY sh.wef DESC LIMIT 1
            """), {"eid": ept.edition_id})).fetchone()
            igst = float(igst_row.igst) if igst_row and igst_row.igst is not None else 0.0
            total += cost * float(d.quantity) * moq * (igst / 100.0)
        return round(total, 2)

    async def get_category_nodes_for_marketplace(self, marketplace_id: int) -> list[dict]:
        """Category nodes that have referral-fee data on a marketplace (for pre-listing pricing)."""
        rows = (await self.session.execute(text("""
            SELECT DISTINCT arf.node_id, n.name AS node_name
            FROM amazon_referral_fees arf
            LEFT JOIN nodes n ON arf.node_id = n.id
            WHERE arf.marketplace_id = :mid
            ORDER BY arf.node_id
        """), {"mid": marketplace_id})).fetchall()
        return [dict(r._mapping) for r in rows]
