import uvicorn
from fastapi import FastAPI
from src.api.routes import router as pricing_router

app = FastAPI(
    title="Marketplace Intelligence Agent API",
    description="API for the Listing Intelligence Center, including Pricing Recommendations.",
    version="1.0.0"
)

app.include_router(pricing_router, prefix="/api/v1")

if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8001, reload=True)
