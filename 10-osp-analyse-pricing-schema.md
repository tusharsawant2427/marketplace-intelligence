# OSP `analyse()` Pricing Engine — Table Schemas

> **Scope.** Every database table read or joined by the **`analyse()`** flow in
> `OnlineSellingProductPlatformController` — the pricing simulator that takes an Online Selling
> Product (OSP) and returns, for each **platform × marketplace × node (category) × fulfillment type ×
> zone × candidate price**, a fully-costed row with fees, taxes and **profit margin**.
>
> **Companion to** [`08-listing-intelligence-center-agent-context.md`](./08-listing-intelligence-center-agent-context.md)
> (how the engine works) and [`09-listing-intelligence-center-schema.md`](./09-listing-intelligence-center-schema.md)
> (LIC data layer). This doc is the **data layer for the pricing engine itself**.
>
> **Provenance.** Columns were dumped from the live `pulse_erp` MySQL schema, except the three
> `saleable_*` tables (not present in the local dataset) which are transcribed from their create
> migrations and flagged as such.
>
> **Important — nothing here is written.** `analyse()` is **read-only**. Every table below is a
> *master* or *product* table it reads; the result rows (`OnlineSellingProductPlatformAnalysisDTO`)
> are computed in memory and returned as JSON. There is **no analyse-result table**. Selected rows
> are persisted only later via `store()` → `createListingFromOsp` into the `listings` family
> (see doc 09 §4).

---

## 0. The call tree → which tables each stage touches

```
analyse(OnlineSellingProduct, request.lpa[])
│
├─ OnlineSellingProductDTO::fromModel($osp, true)          → §A  online_selling_products (+combination, details, dimensions, products/variants/editions)
│    ├─ ->getCurrentSaleableHsnDTO()                       → §B  saleable_hsns → hsn_codes         (sale GST rate)
│    └─ ->getCurrentSaleableMrpDTO()                       → §B  saleable_mrps                      (MRP)
│
├─ Caster::castFromArray()  (own-fulfillment / B2C)        → §C  platforms, marketplaces, nodes,
│    │                                                            fulfillment_types, fulfillment_type_meta_data
│    └─ per candidate price → LpaCalculation::handle()
│         ├─ AmazonCharges  → §D  amazon_referral_fees, amazon_weight_handling_fees,
│         │                        amazon_pick_and_pack_fees, amazon_storage_fees, amazon_closing_fees,
│         │                        amazon_item_types, amazon_step_program_levels, platform_seller_types
│         ├─ FlipkartCharges→ §E  flipkart_* (6 fee tables) + flipkart_seller_types, flipkart_storage_types
│         ├─ JiomartCharges → §F  jiomart_* (7 fee tables)
│         ├─ MeeshoCharges  → §G  meesho_shipping_fees
│         ├─ sale/purchase GST → §B  saleable_hsns/hsn_codes (via product HSN loop)
│         └─ royalty          → §B  saleable_royalty_details
│
└─ Caster::castFromDistributorArray()  (B2B)               → §H  marketplace_distributors  (+ marketplaces w/ has('marketplaceDistributors'))
```

**Two cross-cutting conventions to internalize:**
- **Time-effective masters.** Fee/tax/price tables carry `with_effect_from` (fee masters) or `wef`
  (OSP/tax/price rows). The engine always resolves the **latest row ≤ `Carbon::now()`**. A price
  is never a single value — it's "the row in effect on the analysis date."
- **Polymorphic (`morphs`) attachment.** MRP, HSN, royalty and dimensions attach to *any* saleable
  (`OnlineSellingProduct`, `Product`, `ProductVariant`, `EditionProductType`) via a
  `{name}able_type` + `{name}able_id` pair. That's how the same tax/MRP machinery serves the OSP and
  its constituent products.

---

## A. The subject: OSP and its product composition

### `online_selling_products`
The sellable unit being analysed (route-model-bound `{onlineSellingProduct}`).

| Column | Type | Null | Notes |
|--------|------|------|-------|
| `id` | bigint unsigned PK | no | |
| `name` | varchar(255) | no | |
| `osp_type` | enum(`SINGLE`,`BUNDLED`,`MOQ`) | no | drives quantity multipliers |
| `moq` | int | yes | minimum order qty (for MOQ type) |
| `pages` | int | no | |
| `sku` | varchar(255) | yes | unique; base of synthesized analyse SKU |
| `advertisement_charge` | varchar(255) | yes | **% of MRP** (stored as string) |
| `transport_per_kg_rate` | varchar(255) | yes | ₹/kg for transport cost |
| `packaging_charges` | varchar(255) | yes | ₹ packing cost |
| `state` | enum(`ACTIVE`,`INACTIVE`,`HOLD`,`LISTING_PENDING`,`DETAILS_PENDING`,`ANALYSIS_PENDING`) | no | `DETAILS_PENDING` blocks `create()` |
| `inactive_status_reason_id` | bigint unsigned | yes | |
| `is_royalty` | tinyint(1) | no | triggers royalty math |
| `selling_zone` | enum(`LOCAL`,`REGIONAL`,`NATIONAL`) | yes | zone fan-out driver |
| `is_e_learning` | tinyint(1) | no | |
| `is_set_off_allowed` | tinyint | no | GST input set-off |
| `last_student_data_mining_sync` | datetime | yes | |
| `created_by` / `updated_by` | bigint unsigned | no/yes | |
| `created_at` / `updated_at` / `deleted_at` | timestamp | yes | soft-deletes |

### `online_selling_product_combinations`
Versioned composition of an OSP (`currentOspCombinations` = latest `wef ≤ now`).

| Column | Type | Null | Notes |
|--------|------|------|-------|
| `id` | bigint unsigned PK | no | |
| `online_selling_product_id` | bigint unsigned | no | FK → `online_selling_products` |
| `wef` | datetime | no | with-effect-from; latest wins |
| `created_at`/`updated_at`/`deleted_at` | timestamp | yes | soft-deletes |

### `online_selling_product_details`
The constituent products in a combination (polymorphic). Loop source for `no_of_item` and the
purchase-GST calculation.

| Column | Type | Null | Notes |
|--------|------|------|-------|
| `id` | bigint unsigned PK | no | |
| `online_selling_product_combination_id` | bigint unsigned | no | FK → combination |
| `online_selling_productable_type` | varchar(255) | no | polymorphic target class |
| `online_selling_productable_id` | bigint unsigned | no | → `products` / `product_variants` / `edition_product_types` |
| `quantity` | int unsigned | no | default 1 |
| `created_at`/`updated_at`/`deleted_at` | timestamp | yes | |
| `flag_created_at` / `flag_mrp_changed_at` / `flag_dimension_changed_at` | timestamp | yes | change-tracking flags |

### `dimensions`
Weight & L/W/H for any saleable (polymorphic). Feeds transport, weight-handling, pick-pack and
storage fees.

| Column | Type | Null | Notes |
|--------|------|------|-------|
| `id` | bigint unsigned PK | no | |
| `length` / `width` / `height` / `weight` | double | no | weight in grams |
| `wef` | datetime | no | latest ≤ now |
| `type` | enum(`WITH_PACKAGE`,`WITHOUT_PACKAGE`) | yes | |
| `dimensionable_type` / `dimensionable_id` | varchar / bigint | no | polymorphic owner |
| `created_at`/`updated_at` | timestamp | yes | |

### `products`, `product_variants`, `edition_product_types`
The three concrete types an OSP detail can point at. The engine reads them (via
`currentPurchaseableSaleHsn`) only during the **purchase-GST** loop, and for royalty flags. Key
columns:

**`products`** — `id`, `name`, `brand_id`, `has_variant`, `is_royalty`, `type` (large enum of
product categories), `state`(ACTIVE/INACTIVE), `online_product_category_id`, `is_set_off_allowed`,
`pulse_edition_id`, timestamps.

**`product_variants`** — `id`, `product_id`, `variant_name`, `variantable_type`/`variantable_id`
(polymorphic), `unit` (UNIT/GRAMS/MILLILITER), `unit_of_measure` decimal, `is_set_off_allowed`,
`state`, `pulse_edition_id`, timestamps.

**`edition_product_types`** — `id`, `edition_id`, `ref_code` (unique), `master_edition_product_type_id`,
`reorder_level`, `purchase_average_tat`, timestamps. Its `edition.currentPurchaseableSaleHsn` yields
the HSN for e-learning/book editions.

---

## B. Tax, MRP & Royalty (polymorphic "saleable" layer)

### `saleable_hsns`  *(from migration — not in local dataset)*
Attaches an HSN (tax code) to a saleable, split by sale vs purchase.

| Column | Type | Null | Notes |
|--------|------|------|-------|
| `id` | bigint unsigned PK | no | |
| `hsn_code_id` | bigint unsigned | no | FK → `hsn_codes` |
| `wef` | datetime | no | latest ≤ now |
| `type` | enum(`SALE`,`PURCHASE`) | no | `SALE_TYPE` → sale GST; `PURCHASE_TYPE` → input GST |
| `hsnable_type` / `hsnable_id` | varchar / bigint | no | polymorphic owner (OSP/product/…) |
| `created_at`/`updated_at` | timestamp | yes | |

### `hsn_codes`
The tax-rate master. `igst` is the rate the engine backs GST out of the (inclusive) listing price.

| Column | Type | Null | Notes |
|--------|------|------|-------|
| `id` | bigint unsigned PK | no | |
| `hsn_code` | varchar(20) | no | |
| `sgst` / `cgst` / `igst` | decimal(8,2) | no | **`igst`** = GST % used by engine |
| `sale_type` | enum(`SALE_OF_BOOKS`,`SALE_OF_GOODS`) | no | |
| `with_effect_from` | date | no | latest ≤ now |
| `created_at`/`updated_at`/`deleted_at` | timestamp | yes | |

### `saleable_mrps`  *(from migration — not in local dataset)*
MRP per saleable; `mrp` is the profit-% denominator and advertisement-cost base.

| Column | Type | Null | Notes |
|--------|------|------|-------|
| `id` | bigint unsigned PK | no | |
| `mrp` | double | no | Maximum Retail Price |
| `mrp_profitability` | double | yes | |
| `wef` | datetime | no | latest ≤ now |
| `mrpable_type` / `mrpable_id` | varchar / bigint | no | polymorphic owner |
| `created_by` | bigint unsigned | — | added by later migration |
| `created_at`/`updated_at` | timestamp | yes | |

### `saleable_royalty_details`  *(from migration — not in local dataset)*
Royalty terms per saleable (books / e-learning). `getRoyaltyAmount($price)` reads these.

| Column | Type | Null | Notes |
|--------|------|------|-------|
| `id` | bigint unsigned PK | no | |
| `vendor_id` | bigint unsigned | no | FK → `vendors` |
| `amount` | double | no | flat ₹ or % |
| `is_percentage` | boolean | no | if true, `amount` is % of price |
| `start_date` / `end_date` | datetime | no | validity window (end nullable via later migration) |
| `created_by` / `updated_by` | bigint unsigned | no/yes | FK → `users` |
| `royaltyable_type` / `royaltyable_id` | varchar / bigint | no | polymorphic owner |
| `created_at`/`updated_at` | timestamp | yes | |

---

## C. Channel dimension masters (the fan-out axes)

### `platforms`
| Column | Type | Null | Notes |
|--------|------|------|-------|
| `id` | bigint unsigned PK | no | Amazon=1, Flipkart=2, Jiomart=5, Meesho=8, Amazon-RT=12, Amazon-LBE=31… |
| `name` | varchar(255) | no | unique |
| `advertisement_charge` | decimal(8,2) | no | default 0 |
| `discount_percentage_for_lpa` | decimal(10,2) unsigned | no | default discount applied in LPA |
| `state` | enum(`ACTIVE`,`INACTIVE`) | no | only ACTIVE expanded |
| `created_by`/`updated_by`/timestamps | | | |

### `marketplaces`
| Column | Type | Null | Notes |
|--------|------|------|-------|
| `id` | bigint unsigned PK | no | |
| `name` | varchar(255) | no | |
| `platform_id` | bigint unsigned | no | FK → `platforms` |
| `country_id` / `currency_id` | bigint unsigned | no | |
| `state` | enum(`ACTIVE`,`INACTIVE`) | no | |
| `created_by`/`updated_by`/timestamps | | | |

### `nodes` (category / Amazon browse-node)
Self-referencing tree (`parent_id`, `node_id`); drives referral & closing-fee lookups.

| Column | Type | Null | Notes |
|--------|------|------|-------|
| `id` | bigint unsigned PK | no | |
| `name` | varchar(255) | no | |
| `platform_id` | bigint unsigned | yes | FK → `platforms` |
| `marketplace_id` | bigint unsigned | no | FK → `marketplaces` |
| `node_id` | bigint unsigned | yes | external browse-node id |
| `parent_id` | bigint unsigned | yes | self-FK (tree) |
| `is_exception_category_in_amazon` | tinyint(1) | no | picks `fee_for_exception_category` in closing fee |
| `state` | enum(`ACTIVE`,`INACTIVE`) | no | |
| `created_by`/`updated_by`/timestamps | | | |

### `fulfillment_types`
| Column | Type | Null | Notes |
|--------|------|------|-------|
| `id` | bigint unsigned PK | no | |
| `name` | varchar(255) | no | FBA, EasyShip, EShipPrime, Seller-Flex… |
| `abbr` | varchar(255) | yes | first-3 used in synthesized SKU |
| `platform_id` | bigint unsigned | no | FK → `platforms` |
| `state` | enum(`ACTIVE`,`INACTIVE`) | no | |
| `created_by`/`updated_by`/timestamps | | | |

### `fulfillment_type_meta_data`
Join of a fulfillment type to a marketplace. **All fee masters key their fulfillment on
`fulfillment_type_meta_data_id`, not `fulfillment_type_id`.**

| Column | Type | Null | Notes |
|--------|------|------|-------|
| `id` | bigint unsigned PK | no | referenced as `fulfillment_type_meta_data_id` everywhere |
| `fulfillment_type_id` | bigint unsigned | no | FK → `fulfillment_types` |
| `marketplace_id` | bigint unsigned | no | FK → `marketplaces` |
| `created_at`/`updated_at`/`deleted_at` | timestamp | yes | soft-deletes |

### Tier / type lookups
- **`amazon_item_types`** — `id`, `marketplace_id`, `name`, `state`. Resolves the item-type used by
  weight-handling & pick-pack fees (from volumetric weight/girth).
- **`amazon_step_program_levels`** — `id`, `marketplace_id`, `name`, `state`. The Amazon STEP tier
  (`level_id`) that indexes weight-handling & pick-pack fees.
- **`flipkart_seller_types`** — `id`, `name`(unique), `state`. Flipkart program tier
  (`seller_type_id`).
- **`flipkart_storage_types`** — `id`, `name`(unique), `min_storage_month`, `state`. Indexes storage fee.
- **`platform_seller_types`** — polymorphic, time-effective assignment of a seller type to a model:
  `id`, `model_type`, `model_id`, `wef`. Resolves the *current* seller type for a platform/listing.

---

## D. Amazon fee masters

All time-effective (`with_effect_from`, latest ≤ now). Amazon platform ids: 1, 12 (RT), 31 (LBE).

### `amazon_referral_fees` — commission %
| Column | Type | Null | Notes |
|--------|------|------|-------|
| `id` | bigint unsigned PK | no | |
| `node_id` | bigint unsigned | no | FK → `nodes` (category) |
| `marketplace_id` | bigint unsigned | no | FK → `marketplaces` |
| `min_value` / `max_value` | int | no | listing-price band |
| `fee_percentage` | double(8,2) unsigned | no | referral % |
| `with_effect_from` | date | no | |
| `created_by`/`updated_by`/timestamps | | | |

### `amazon_weight_handling_fees` — fulfillment (weight/dimensional)
| Column | Type | Null | Notes |
|--------|------|------|-------|
| `id` | bigint unsigned PK | no | |
| `level_id` | bigint unsigned | no | FK → `amazon_step_program_levels` |
| `fulfillment_type_meta_data_id` | bigint unsigned | no | FK → fulfillment meta |
| `item_type_id` | bigint unsigned | no | FK → `amazon_item_types` |
| `node_id` | bigint unsigned | yes | FK → `nodes` |
| `zone` | enum(`LOCAL`,`REGIONAL`,`NATIONAL`,`IXD`) | no | |
| `weight_slab_in_grams` | int | no | slab step |
| `min_weight_slab` / `max_weight_slab` | int | no | slab bounds |
| `min_price` / `max_price` | double(10,2) unsigned | no | price band |
| `fee` | double(8,2) unsigned | no | ₹ handling fee |
| `with_effect_from` | date | no | |
| `created_by`/`updated_by`/timestamps | | | |

### `amazon_pick_and_pack_fees`
| Column | Type | Null | Notes |
|--------|------|------|-------|
| `id` | bigint unsigned PK | no | |
| `level_id` | bigint unsigned | no | FK → step level |
| `item_type_id` | bigint unsigned | no | FK → item type |
| `fulfillment_type_meta_data_id` | bigint unsigned | no | FK |
| `fee` | double(8,2) | no | ₹ |
| `weight_slab_in_grams` / `min_weight_slab` / `max_weight_slab` | double | no | slab |
| `with_effect_from` | date | no | |
| `created_by`/`updated_by`/timestamps | | | |

### `amazon_storage_fees`
| Column | Type | Null | Notes |
|--------|------|------|-------|
| `id` | bigint unsigned PK | no | |
| `fulfillment_type_meta_data_id` | bigint unsigned | no | FK |
| `cost_per_cubic_foot` | double(8,2) | no | × volumetric size |
| `with_effect_from` | date | no | |
| `created_by`/`updated_by`/timestamps | | | |

### `amazon_closing_fees` — collection/closing fee
| Column | Type | Null | Notes |
|--------|------|------|-------|
| `id` | bigint unsigned PK | no | |
| `fulfillment_type_meta_data_id` | bigint unsigned | no | FK |
| `node_id` | bigint unsigned | yes | FK → `nodes` |
| `min_value` / `max_value` | int | no | price band |
| `fee` | double(8,2) unsigned | no | standard closing fee |
| `fee_for_exception_category` | double(8,2) unsigned | no | used when node `is_exception_category_in_amazon` |
| `with_effect_from` | date | no | |
| `created_by`/`updated_by`/timestamps | | | |

---

## E. Flipkart fee masters
`with_effect_from` default `2022-01-03`. `is_percentage` toggles ₹ vs % on `rate`.

### `flipkart_commission_fees`
`id`, `fulfillment_type_meta_data_id`(nullable), `node_id`, `marketplace_id`,
`minimum_order_item_value` double, `rate` double, `is_percentage` tinyint, `with_effect_from`, audit.

### `flipkart_shipping_fees`
`id`, `fulfillment_type_meta_data_id`, `zone`(LOCAL/REGIONAL/NATIONAL), `seller_type_id`, `node_id`(nullable),
`weight_slab_in_grams`, `min_weight_slab`, `max_weight_slab`, `rate` (all double), `with_effect_from`, audit.

### `flipkart_fixed_fees`
`id`, `fulfillment_type_meta_data_id`, `minimum_order_item_value`, `is_percentage`, `rate`,
`node_id`(nullable), `seller_type_id`(nullable), `with_effect_from`, audit.

### `flipkart_collection_fees`
`id`, `payment_type`(POSTPAID/PREPAID), `marketplace_id`, `minimum_order_item_value`, `rate`,
`is_percentage`, `with_effect_from`, audit.

### `flipkart_pick_pack_fees`
`id`, `fulfillment_type_meta_data_id`, `seller_type_id`, `node_id`(nullable), `is_percentage`,
`weight_slab_in_grams`(def 1000), `min_weight_slab`, `max_weight_slab`, `rate`, `with_effect_from`, audit.

### `flipkart_storage_fees`
`id`, `storage_type_id`(→`flipkart_storage_types`), `seller_type_id`, `fulfillment_type_meta_data_id`,
`is_flat_rate`, `rate`, `unit_slab_in_grams`, `with_effect_from`, audit.

---

## F. Jiomart fee masters
`rate` decimal(8,2); `is_percentage` toggles ₹ vs %.

### `jiomart_commission_fees`
`id`, `node_id`, `marketplace_id`, `minimum_order_item_value`, `maximum_order_item_value`(nullable),
`rate`, `is_percentage`, `with_effect_from`, audit.

### `jiomart_shipping_fees`
`id`, `fulfillment_type_meta_data_id`, `zone` varchar, `min_weight_slab`, `max_weight_slab`(nullable),
`weight_slab_in_grams`, `rate`, `with_effect_from`, audit.

### `jiomart_fixed_fees`
`id`, `marketplace_id`, `fulfillment_type_meta_data_id`, `minimum_order_item_value`,
`maximum_order_item_value`(nullable), `rate`, `is_percentage`, `with_effect_from`, audit.

### `jiomart_collection_fees`
`id`, `marketplace_id`, `minimum_order_item_value`, `maximum_order_item_value`(nullable), `rate`,
`is_percentage`, `with_effect_from`, audit.

### `jiomart_pick_pack_fees`
`id`, `fulfillment_type_meta_data_id`, `rate`, `is_percentage`, `with_effect_from`, audit.

### `jiomart_storage_fees`
`id`, `fulfillment_type_meta_data_id`, `cost_per_cubic_foot`, `with_effect_from`, audit.

### `jiomart_labelling_fees`
`id`, `fulfillment_type_meta_data_id` (int), `rate`, `with_effect_from`, audit.

---

## G. Meesho fee master

### `meesho_shipping_fees`
Price-banded shipping with its own GST column (Meesho fee model has no fulfillment/zone fan-out).

| Column | Type | Null | Notes |
|--------|------|------|-------|
| `id` | bigint unsigned PK | no | |
| `min_value` / `max_value` | decimal(8,2) | no | listing-price band |
| `gst_on_shipping` | decimal(8,2) | no | GST % on the shipping charge |
| `shipping_charges` | double | no | ₹ |
| `with_effect_from` | date | no | |
| `created_by`/`updated_by`/timestamps | | | |

---

## H. Distributor (B2B) path

`castFromDistributorArray()` only fires for `lpa` items carrying a `distributors[]` array, and loads
marketplaces that `has('marketplaceDistributors')`.

### `marketplace_distributors`
| Column | Type | Null | Notes |
|--------|------|------|-------|
| `id` | bigint unsigned PK | no | |
| `name` | varchar(255) | no | unique; overwrites `platform_name` on B2B rows |
| `marketplace_id` | bigint unsigned | no | FK → `marketplaces` |
| `conflicting_distributors` | varchar(255) | yes | |
| `state` | enum(`ACTIVE`,`INACTIVE`) | no | |
| `created_by`/`updated_by`/timestamps | | | |

> The distributor **prices/discounts** are not read from a table here — they arrive in the request
> (`lpa[i].distributors[].price_details[]`). On B2B rows commission = `marketplace_mrp −
> distributor_selling_price`, fulfillment fees are skipped, and the zone collapses to national.
> (The persisted counterparts `listing_marketplace_distributors` /
> `listing_marketplace_distributors_pricings` belong to the *listing* flow, not `analyse()`.)

---

## Appendix — full table inventory (41)

| # | Table | Group | Role |
|---|-------|-------|------|
| 1 | `online_selling_products` | A | subject OSP |
| 2 | `online_selling_product_combinations` | A | versioned composition |
| 3 | `online_selling_product_details` | A | constituent products |
| 4 | `dimensions` | A | weight/L·W·H (poly) |
| 5 | `products` | A | constituent |
| 6 | `product_variants` | A | constituent |
| 7 | `edition_product_types` | A | constituent |
| 8 | `saleable_hsns` | B | sale/purchase HSN link (poly) † |
| 9 | `hsn_codes` | B | GST-rate master |
| 10 | `saleable_mrps` | B | MRP (poly) † |
| 11 | `saleable_royalty_details` | B | royalty terms (poly) † |
| 12 | `platforms` | C | channel |
| 13 | `marketplaces` | C | channel |
| 14 | `nodes` | C | category tree |
| 15 | `fulfillment_types` | C | fulfillment |
| 16 | `fulfillment_type_meta_data` | C | fulfillment × marketplace (fee key) |
| 17 | `amazon_item_types` | C | item-type tier |
| 18 | `amazon_step_program_levels` | C | STEP tier |
| 19 | `flipkart_seller_types` | C | seller tier |
| 20 | `flipkart_storage_types` | C | storage tier |
| 21 | `platform_seller_types` | C | current seller type (poly, wef) |
| 22 | `amazon_referral_fees` | D | commission |
| 23 | `amazon_weight_handling_fees` | D | fulfillment |
| 24 | `amazon_pick_and_pack_fees` | D | pick/pack |
| 25 | `amazon_storage_fees` | D | storage |
| 26 | `amazon_closing_fees` | D | closing/collection |
| 27 | `flipkart_commission_fees` | E | commission |
| 28 | `flipkart_shipping_fees` | E | shipping |
| 29 | `flipkart_fixed_fees` | E | fixed |
| 30 | `flipkart_collection_fees` | E | collection |
| 31 | `flipkart_pick_pack_fees` | E | pick/pack |
| 32 | `flipkart_storage_fees` | E | storage |
| 33 | `jiomart_commission_fees` | F | commission |
| 34 | `jiomart_shipping_fees` | F | shipping |
| 35 | `jiomart_fixed_fees` | F | fixed |
| 36 | `jiomart_collection_fees` | F | collection |
| 37 | `jiomart_pick_pack_fees` | F | pick/pack |
| 38 | `jiomart_storage_fees` | F | storage |
| 39 | `jiomart_labelling_fees` | F | labelling |
| 40 | `meesho_shipping_fees` | G | shipping (+GST) |
| 41 | `marketplace_distributors` | H | B2B distributor |

† Columns from create migrations; table not present in the local dataset (verify against production
before relying on exact types).
