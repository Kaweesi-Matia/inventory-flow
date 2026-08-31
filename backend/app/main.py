from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    admin,
    auth,
    categories,
    customer_orders,
    dashboard,
    inventory,
    products,
    purchase_orders,
    reports,
    suppliers,
    transfers,
    warehouses,
)
from app.core.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    description="B2B inventory and supply chain management platform",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_origin_regex=settings.CORS_ORIGIN_REGEX or None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Keep routes thin — every router below delegates business logic to app/services/*
app.include_router(auth.router)
app.include_router(products.router)
app.include_router(categories.router)
app.include_router(suppliers.router)
app.include_router(warehouses.router)
app.include_router(inventory.router)
app.include_router(transfers.router)
app.include_router(purchase_orders.router)
app.include_router(customer_orders.router)
app.include_router(customer_orders.customers_router)
app.include_router(reports.router)
app.include_router(dashboard.router)
app.include_router(admin.router)


@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": settings.APP_NAME}
