from src.models.charges import Charges
from src.tools.base_tool import BaseTool
from src.utils.json_loader import load_json
class FetchChargesTool(BaseTool):
    """ Tool to fetch charges data."""

    def execute(self, listing_id:str) -> Charges:
        data = load_json("charges.json")
        return Charges(
            advertisement_charge=data["advertisement_charge"],
            packaging_charge=data["packaging_charge"],
            transport_charge=data["transport_charge"],
            delivery_charge_local=data["delivery_charge_local"],
            delivery_charge_regional=data["delivery_charge_regional"],
            delivery_charge_national=data["delivery_charge_national"],
            platform_charge_local=data["platform_charge_local"],
            platform_charge_regional=data["platform_charge_regional"],
            platform_charge_national=data["platform_charge_national"]
        )