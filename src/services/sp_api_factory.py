"""
Helper to build a read-only AmazonSpApiService for the marketplace-facing agents.

Per the multi-agent plan, these agents read Amazon SP-API directly (read-only). Credentials are
fetched from the ERP DB via ErpRepository (which owns the token refresh), and the internal
marketplace id is resolved to Amazon's global marketplace id string.
"""
from src.database.connection import async_session
from src.database.repository import ErpRepository
from src.services.amazon_sp_api_service import AmazonSpApiService

DEFAULT_MARKETPLACE_ID = 1  # Amazon-India


async def build_sp_api(marketplace_id: int = DEFAULT_MARKETPLACE_ID):
    """Return (AmazonSpApiService, amazon_marketplace_id_str). Read-only."""
    async with async_session() as session:
        repo = ErpRepository(session)
        creds = await repo.get_amazon_sp_credentials()
        amazon_marketplace_id = await repo.get_amazon_marketplace_id(marketplace_id)
    return AmazonSpApiService(creds), amazon_marketplace_id
