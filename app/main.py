from fastapi import FastAPI
from app.api import items_router, adjustments_router, stock_import_router, settings_router

app = FastAPI(
    title="Shared Inventory Service API",
    version="1.0.0",
    description="Multi-tenant backend API for shared inventory across organizations with location-based permissions, concurrency safety, and audit history."
)

app.include_router(items_router)
app.include_router(adjustments_router)
app.include_router(stock_import_router)
app.include_router(settings_router)

@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok", "service": "Shared Inventory Service"}
