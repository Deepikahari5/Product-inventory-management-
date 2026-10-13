
import json
from pathlib import Path

items = []


def req(name, method, path, body=None, tests=""):
    r = {
        "name": name,
        "request": {
            "method": method,
            "header": [{"key": "Content-Type", "value": "application/json"}],
            "url": {"raw": "{{base_url}}" + path, "host": ["{{base_url}}"],
                    "path": [p for p in path.split("?")[0].split("/") if p]},
        },
        "event": [{"listen": "test", "script": {"type": "text/javascript",
                   "exec": tests.strip().split("\n")}}],
    }
    if "?" in path:
        q = path.split("?")[1]
        r["request"]["url"]["query"] = [
            {"key": kv.split("=")[0], "value": kv.split("=")[1]} for kv in q.split("&")
        ]
    if body is not None:
        r["request"]["body"] = {"mode": "raw", "raw": json.dumps(body, indent=2),
                                "options": {"raw": {"language": "json"}}}
    items.append(r)


def status(code, extra=""):
    return f'pm.test("Status is {code}", () => pm.response.to.have.status({code}));\n{extra}'


req("01 Create category", "POST", "/categories",
    {"name": "Electronics", "description": "Electronic items"},
    status(201, 'pm.collectionVariables.set("category_id", pm.response.json().id);'))
req("02 Create duplicate category (409)", "POST", "/categories",
    {"name": "Electronics", "description": "dup"},
    status(409, 'pm.test("Has message", () => pm.expect(pm.response.json().detail).to.include("already exists"));'))
req("03 Create product 1 - Laptop", "POST", "/products",
    {"name": "Laptop", "description": "Office laptop", "category_id": "{{category_id}}", "price": 800, "quantity": 10},
    status(201, 'pm.collectionVariables.set("product_id", pm.response.json().id);'))
req("04 Create product 2 - Mouse", "POST", "/products",
    {"name": "Mouse", "description": "Wireless mouse", "category_id": "{{category_id}}", "price": 25, "quantity": 100},
    status(201, 'pm.collectionVariables.set("product_id2", pm.response.json().id);'))
req("05 Create product 3 - Gaming Laptop", "POST", "/products",
    {"name": "Gaming Laptop", "description": "High-end", "category_id": "{{category_id}}", "price": 1500, "quantity": 5},
    status(201, 'pm.collectionVariables.set("product_id3", pm.response.json().id);'))
req("06 Get all categories", "GET", "/categories", None,
    status(200, 'pm.test("List not empty", () => pm.expect(pm.response.json().length).to.be.above(0));'))
req("07 Get category by id", "GET", "/categories/{{category_id}}", None, status(200))
req("08 Update category", "PUT", "/categories/{{category_id}}",
    {"description": "Updated description"},
    status(200, 'pm.test("Updated", () => pm.expect(pm.response.json().description).to.eql("Updated description"));'))
req("09 Get all products", "GET", "/products", None,
    status(200, 'pm.test("3 products", () => pm.expect(pm.response.json().length).to.eql(3));'))
req("10 Get product by id", "GET", "/products/{{product_id}}", None, status(200))
req("11 Update product (Mouse price 25 -> 30)", "PUT", "/products/{{product_id2}}",
    {"price": 30},
    status(200, 'pm.test("Price updated", () => pm.expect(pm.response.json().price).to.eql(30));'))
req("12 Filter products by category", "GET", "/products?category_id={{category_id}}", None,
    status(200, 'pm.test("3 products", () => pm.expect(pm.response.json().length).to.eql(3));'))
req("13 Filter products by price range", "GET", "/products?min_price=100&max_price=1000", None,
    status(200, 'pm.test("Only Laptop", () => { const b = pm.response.json(); pm.expect(b.length).to.eql(1); pm.expect(b[0].name).to.eql("Laptop"); });'))
req("14 Search products by name", "GET", "/products?search=laptop", None,
    status(200, 'pm.test("2 laptops", () => pm.expect(pm.response.json().length).to.eql(2));'))
req("15 Get products of a category", "GET", "/categories/{{category_id}}/products", None,
    status(200, 'pm.test("3 products", () => pm.expect(pm.response.json().length).to.eql(3));'))
req("16 Total inventory value", "GET", "/products/inventory-value", None,
    status(200, 'pm.test("800*10 + 30*100 + 1500*5 = 18500", () => pm.expect(pm.response.json().total_inventory_value).to.eql(18500));'))
req("17 Create product - non-existing category (400)", "POST", "/products",
    {"name": "Ghost", "category_id": 9999, "price": 10, "quantity": 1},
    status(400, 'pm.test("Message", () => pm.expect(pm.response.json().detail).to.include("does not exist"));'))
req("18 Create product - negative price (422)", "POST", "/products",
    {"name": "Bad", "category_id": "{{category_id}}", "price": -10, "quantity": 1}, status(422))
req("19 Create product - negative quantity (422)", "POST", "/products",
    {"name": "Bad", "category_id": "{{category_id}}", "price": 10, "quantity": -1}, status(422))
req("20 Create product - zero price (422)", "POST", "/products",
    {"name": "Bad", "category_id": "{{category_id}}", "price": 0, "quantity": 1}, status(422))
req("21 Get non-existing product (404)", "GET", "/products/9999", None,
    status(404, 'pm.test("Message", () => pm.expect(pm.response.json().detail).to.include("not found"));'))
req("22 Get non-existing category (404)", "GET", "/categories/9999", None,
    status(404, 'pm.test("Message", () => pm.expect(pm.response.json().detail).to.include("not found"));'))
req("23 FK check - delete category that has products (409)", "DELETE", "/categories/{{category_id}}", None, status(409))
req("24 Delete product 1", "DELETE", "/products/{{product_id}}", None, status(204))
req("25 Delete product 2", "DELETE", "/products/{{product_id2}}", None, status(204))
req("26 Delete product 3", "DELETE", "/products/{{product_id3}}", None, status(204))
req("27 Verify deleted product (404)", "GET", "/products/{{product_id}}", None, status(404))
req("28 Delete category (now empty)", "DELETE", "/categories/{{category_id}}", None, status(204))
req("29 Verify deleted category (404)", "GET", "/categories/{{category_id}}", None, status(404))

collection = {
    "info": {
        "name": "Product Inventory API",
        "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
        "description": "Run the whole collection in order with the Collection Runner on an EMPTY database.",
    },
    "variable": [
        {"key": "base_url", "value": "http://127.0.0.1:8000"},
        {"key": "category_id", "value": ""},
        {"key": "product_id", "value": ""},
        {"key": "product_id2", "value": ""},
        {"key": "product_id3", "value": ""},
    ],
    "item": items,
}
out = Path(__file__).parent / "Inventory_API.postman_collection.json"
out.write_text(json.dumps(collection, indent=2))
print("written", out, len(items), "requests")
