import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from sqlalchemy import asc, desc
from sqlalchemy.orm import Session

from app.core.permissions import require_roles
from app.database.connection import get_db
from app.models.product import Product, ProductStatus
from app.models.user import User, UserRole
from app.schemas.product import PaginatedProducts, ProductCreate, ProductOut, ProductUpdate
from app.services.auth_service import get_current_user
from app.utils.csv_import import import_products_csv

router = APIRouter(prefix="/api/products", tags=["products"])

SORTABLE_FIELDS = {"name": Product.name, "sku": Product.sku, "unit_price": Product.unit_price}


@router.get("", response_model=PaginatedProducts)
def list_products(
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
    search: str | None = Query(default=None, description="Matches SKU or name"),
    category_id: uuid.UUID | None = None,
    status_filter: ProductStatus | None = Query(default=None, alias="status"),
    sort_by: str = Query(default="name"),
    sort_dir: str = Query(default="asc", pattern="^(asc|desc)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
):
    query = db.query(Product)
    if search:
        like = f"%{search}%"
        query = query.filter((Product.sku.ilike(like)) | (Product.name.ilike(like)))
    if category_id:
        query = query.filter(Product.category_id == category_id)
    if status_filter:
        query = query.filter(Product.status == status_filter)

    total = query.count()

    sort_column = SORTABLE_FIELDS.get(sort_by, Product.name)
    query = query.order_by(asc(sort_column) if sort_dir == "asc" else desc(sort_column))
    items = query.offset((page - 1) * page_size).limit(page_size).all()

    return PaginatedProducts(items=items, total=total, page=page, page_size=page_size)


@router.post("", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
def create_product(
    payload: ProductCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles(UserRole.ADMIN, UserRole.INVENTORY_MANAGER)),
):
    existing = db.query(Product).filter(Product.sku == payload.sku).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A product with this SKU already exists")

    product = Product(**payload.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@router.post("/import")
async def bulk_import(
    file: UploadFile,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.INVENTORY_MANAGER)),
):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only .csv files are accepted")
    contents = await file.read()
    return import_products_csv(db, contents, imported_by_id=current_user.id)


@router.get("/{product_id}", response_model=ProductOut)
def get_product(product_id: uuid.UUID, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return product


@router.put("/{product_id}", response_model=ProductOut)
def update_product(
    product_id: uuid.UUID,
    payload: ProductUpdate,
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles(UserRole.ADMIN, UserRole.INVENTORY_MANAGER)),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(product, field, value)

    db.commit()
    db.refresh(product)
    return product


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_product(
    product_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles(UserRole.ADMIN, UserRole.INVENTORY_MANAGER)),
):
    """
    Soft-delete only: products with historical stock movements must never
    be hard-deleted, since that would corrupt the audit ledger's foreign
    keys. We flip status to INACTIVE instead.
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    product.status = ProductStatus.INACTIVE
    db.commit()
