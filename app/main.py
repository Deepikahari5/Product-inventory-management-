
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import models 
from app.database import Base, engine
from app.exceptions import register_exception_handlers
from app.routers import categories, products


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)  


app = FastAPI(
    title="Product Inventory Management API",
    description="FastAPI + SQLAlchemy ORM + SQLite",
    version="1.0.0",
    lifespan=lifespan,
)

register_exception_handlers(app)
app.include_router(categories.router)
app.include_router(products.router)


@app.get("/", tags=["Health"])
def root():
    return {"message": "Product Inventory API is running", "docs": "/docs"}
