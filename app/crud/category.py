
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.exceptions import ConflictError, DuplicateError, NotFoundError
from app.models import Category, Product
from app.schemas import CategoryCreate, CategoryUpdate


def get_category_or_404(db: Session, category_id: int) -> Category:
    category = db.get(Category, category_id)
    if category is None:
        raise NotFoundError(f"Category with id {category_id} not found")
    return category


def _name_exists(db: Session, name: str, exclude_id: int | None = None) -> bool:
    stmt = select(Category.id).where(Category.name == name)
    if exclude_id is not None:
        stmt = stmt.where(Category.id != exclude_id)
    return db.execute(stmt).first() is not None


def create_category(db: Session, data: CategoryCreate) -> Category:
    if _name_exists(db, data.name):
        raise DuplicateError(f"Category with name '{data.name}' already exists")
    category = Category(**data.model_dump())
    db.add(category)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise DuplicateError(f"Category with name '{data.name}' already exists")
    db.refresh(category)
    return category


def list_categories(db: Session, skip: int = 0, limit: int = 100) -> list[Category]:
    stmt = select(Category).order_by(Category.id).offset(skip).limit(limit)
    return list(db.scalars(stmt))


def update_category(db: Session, category_id: int, data: CategoryUpdate) -> Category:
    category = get_category_or_404(db, category_id)
    changes = data.model_dump(exclude_unset=True)
    if "name" in changes and changes["name"] is None:
        changes.pop("name")  
    if "name" in changes and _name_exists(db, changes["name"], exclude_id=category_id):
        raise DuplicateError(f"Category with name '{changes['name']}' already exists")
    for field, value in changes.items():
        setattr(category, field, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise DuplicateError("Category name already exists")
    db.refresh(category)
    return category


def delete_category(db: Session, category_id: int) -> None:
    category = get_category_or_404(db, category_id)
    has_products = db.execute(
        select(Product.id).where(Product.category_id == category_id).limit(1)
    ).first()
    if has_products:
        raise ConflictError(
            f"Cannot delete category {category_id}: it still has products. "
            "Delete or move the products first."
        )
    db.delete(category)
    db.commit()


def list_products_of_category(db: Session, category_id: int) -> list[Product]:
    get_category_or_404(db, category_id)
    stmt = select(Product).where(Product.category_id == category_id).order_by(Product.id)
    return list(db.scalars(stmt))
