import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.permissions import require_roles
from app.database.connection import get_db
from app.models.category import Category
from app.models.product import Product, ProductStatus
from app.models.user import User, UserRole
from app.services.auth_service import get_current_user
from app.schemas.product import CategoryCreate, CategoryOut

router = APIRouter(prefix="/api/categories", tags=["categories"])


@router.get("", response_model=list[CategoryOut])
def list_categories(db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    return db.query(Category).all()


@router.post("", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
def create_category(
    payload: CategoryCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles(UserRole.ADMIN, UserRole.INVENTORY_MANAGER)),
):
    category = Category(**payload.model_dump())
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@router.put("/{category_id}", response_model=CategoryOut)
def update_category(
    category_id: uuid.UUID,
    payload: CategoryCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles(UserRole.ADMIN, UserRole.INVENTORY_MANAGER)),
):
    category = db.query(Category).filter(Category.id == category_id).first()
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    category.name = payload.name
    category.parent_id = payload.parent_id
    db.commit()
    db.refresh(category)
    return category


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    category_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles(UserRole.ADMIN, UserRole.INVENTORY_MANAGER)),
):
    category = db.query(Category).filter(Category.id == category_id).first()
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    active_products = (
        db.query(Product).filter(Product.category_id == category_id, Product.status == ProductStatus.ACTIVE).count()
    )
    if active_products > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete a category with active products assigned — reassign them first",
        )
    db.delete(category)
    db.commit()
