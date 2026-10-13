
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.exceptions import BadRequestError, InvalidReferenceError, NotFoundError
from app.models import Category, Product
from app.schemas import ProductCreate, ProductUpdate


def get_product_or_404(db: Session, product_id: int) -> Product:
    product = db.get(Product, product_id)
    if product is None:
        raise NotFoundError(f"Product with id {product_id} not found")
    return product


def _ensure_category_exists(db: Session, category_id: int) -> None:
    if db.get(Category, category_id) is None:
        raise InvalidReferenceError(
            f"Invalid category_id: category with id {category_id} does not exist"
        )


def create_product(db: Session, data: ProductCreate) -> Product:
    _ensure_category_exists(db, data.category_id)
    product = Product(**data.model_dump())
    db.add(product)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise InvalidReferenceError("Invalid category reference")
    db.refresh(product)
    return product


def list_products(
    db: Session,
    category_id: int | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    search: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[Product]:
    if min_price is not None and max_price is not None and min_price > max_price:
        raise BadRequestError("min_price cannot be greater than max_price")

    stmt = select(Product)
    if category_id is not None:
        stmt = stmt.where(Product.category_id == category_id)
    if min_price is not None:
        stmt = stmt.where(Product.price >= min_price)
    if max_price is not None:
        stmt = stmt.where(Product.price <= max_price)
    if search:
        stmt = stmt.where(Product.name.ilike(f"%{search.strip()}%"))
    stmt = stmt.order_by(Product.id).offset(skip).limit(limit)
    return list(db.scalars(stmt))


def update_product(db: Session, product_id: int, data: ProductUpdate) -> Product:
    product = get_product_or_404(db, product_id)
    changes = data.model_dump(exclude_unset=True)
    
    for key in ("name", "category_id", "price", "quantity"):
        if key in changes and changes[key] is None:
            changes.pop(key)
    if "category_id" in changes:
        _ensure_category_exists(db, changes["category_id"])
    for field, value in changes.items():
        setattr(product, field, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise InvalidReferenceError("Invalid category reference")
    db.refresh(product)
    return product


def delete_product(db: Session, product_id: int) -> None:
    product = get_product_or_404(db, product_id)
    db.delete(product)
    db.commit()


def inventory_value(db: Session) -> dict:
    
    stmt = select(
        func.count(Product.id),
        func.coalesce(func.sum(Product.quantity), 0),
        func.coalesce(func.sum(Product.price * Product.quantity), 0.0),
    )
    count, qty, value = db.execute(stmt).one()
    return {
        "total_products": count,
        "total_quantity": int(qty),
        "total_inventory_value": round(float(value), 2),
    }
