import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.database as database
from app.database import Base, get_db
from app.main import app
from app.models import Product


@pytest.fixture()
def engine():
    eng = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture()
def client(engine):
    Testing = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    def override():
        db = Testing()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override
    yield TestClient(app)
    app.dependency_overrides.clear()


def mk_cat(client, name="Electronics"):
    return client.post("/categories", json={"name": name, "description": "d"})


def mk_prod(client, cid, name="Laptop", price=800, qty=10):
    return client.post(
        "/products",
        json={"name": name, "category_id": cid, "price": price, "quantity": qty},
    )


def test_category_crud(client):
    r = mk_cat(client)
    assert r.status_code == 201
    cid = r.json()["id"]
    assert client.get("/categories").json()[0]["name"] == "Electronics"
    assert client.get(f"/categories/{cid}").status_code == 200
    r = client.put(f"/categories/{cid}", json={"description": "new"})
    assert r.status_code == 200 and r.json()["description"] == "new"
    assert client.delete(f"/categories/{cid}").status_code == 204
    assert client.get(f"/categories/{cid}").status_code == 404


def test_duplicate_category(client):
    mk_cat(client)
    assert mk_cat(client).status_code == 409


def test_category_not_found(client):
    r = client.get("/categories/999")
    assert r.status_code == 404 and "not found" in r.json()["detail"]


def test_product_crud(client):
    cid = mk_cat(client).json()["id"]
    r = mk_prod(client, cid)
    assert r.status_code == 201
    pid = r.json()["id"]
    assert client.get(f"/products/{pid}").json()["name"] == "Laptop"
    r = client.put(f"/products/{pid}", json={"price": 900})
    assert r.status_code == 200 and r.json()["price"] == 900
    assert client.delete(f"/products/{pid}").status_code == 204
    assert client.get(f"/products/{pid}").status_code == 404


def test_product_validation(client):
    cid = mk_cat(client).json()["id"]
    assert mk_prod(client, cid, price=-5).status_code == 422
    assert mk_prod(client, cid, price=0).status_code == 422
    assert mk_prod(client, cid, qty=-1).status_code == 422
    assert mk_prod(client, cid, qty=0).status_code == 201  
    assert client.post("/products", json={"category_id": cid}).status_code == 422


def test_product_invalid_category(client):
    r = mk_prod(client, 999)
    assert r.status_code == 400 and "does not exist" in r.json()["detail"]


def test_update_invalid_category(client):
    cid = mk_cat(client).json()["id"]
    pid = mk_prod(client, cid).json()["id"]
    assert client.put(f"/products/{pid}", json={"category_id": 999}).status_code == 400


def test_product_not_found(client):
    r = client.get("/products/999")
    assert r.status_code == 404 and "not found" in r.json()["detail"]


def test_filters_search_and_category_products(client):
    c1 = mk_cat(client, "Electronics").json()["id"]
    c2 = mk_cat(client, "Books").json()["id"]
    mk_prod(client, c1, "Laptop", 800, 10)
    mk_prod(client, c1, "Gaming Laptop", 1500, 5)
    mk_prod(client, c1, "Mouse", 25, 100)
    mk_prod(client, c2, "Novel", 15, 50)

    assert len(client.get("/products", params={"category_id": c1}).json()) == 3
    r = client.get("/products", params={"min_price": 100, "max_price": 1000}).json()
    assert [p["name"] for p in r] == ["Laptop"]
    assert len(client.get("/products", params={"search": "laptop"}).json()) == 2
    assert len(client.get(f"/categories/{c1}/products").json()) == 3
    assert client.get("/categories/999/products").status_code == 404
    assert client.get("/products", params={"min_price": 10, "max_price": 5}).status_code == 400


def test_inventory_value(client):
    assert client.get("/products/inventory-value").json()["total_inventory_value"] == 0
    c = mk_cat(client).json()["id"]
    mk_prod(client, c, "A", 800, 10)  
    mk_prod(client, c, "B", 1500, 5)   
    mk_prod(client, c, "C", 25, 100)   
    body = client.get("/products/inventory-value").json()
    assert body["total_inventory_value"] == 18000
    assert body["total_products"] == 3


def test_cannot_delete_category_with_products(client):
    cid = mk_cat(client).json()["id"]
    mk_prod(client, cid)
    assert client.delete(f"/categories/{cid}").status_code == 409


def test_foreign_key_enforced_by_database(engine):
    
    with Session(engine) as db:
        db.add(Product(name="Orphan", category_id=12345, price=1, quantity=1))
        with pytest.raises(IntegrityError):
            db.commit()


def test_sessions_are_closed(engine, monkeypatch):
    closed = []

    class Tracked(Session):
        def close(self):
            closed.append(1)
            super().close()

    monkeypatch.setattr(
        database, "SessionLocal", sessionmaker(bind=engine, class_=Tracked)
    )
    c = TestClient(app)  
    assert c.get("/categories").status_code == 200
    assert c.get("/products/999").status_code == 404  
    assert c.post("/products", json={"name": "x"}).status_code == 422
    assert len(closed) >= 2  
