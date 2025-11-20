import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import Product, Order, OrderItem

app = FastAPI(title="Ecommerce API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Ecommerce API running"}

@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    return response

# Utility to convert Mongo docs
class ProductOut(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    price: float
    category: str
    image: Optional[str] = None
    in_stock: bool

    class Config:
        from_attributes = True

@app.get("/api/products", response_model=List[ProductOut])
def list_products(category: Optional[str] = None, q: Optional[str] = None, limit: int = 50):
    filt = {}
    if category:
        filt["category"] = category
    if q:
        filt["title"] = {"$regex": q, "$options": "i"}
    docs = get_documents("product", filt, limit)
    out = []
    for d in docs:
        out.append(ProductOut(
            id=str(d.get("_id")),
            title=d.get("title"),
            description=d.get("description"),
            price=float(d.get("price", 0)),
            category=d.get("category"),
            image=d.get("image"),
            in_stock=bool(d.get("in_stock", True))
        ))
    return out

@app.post("/api/products", status_code=201)
def create_product(product: Product):
    new_id = create_document("product", product)
    return {"id": new_id}

# Seed some sample products (idempotent)
@app.post("/api/seed")
def seed_products():
    count = db["product"].count_documents({}) if db else 0
    if count > 0:
        return {"seeded": False, "message": "Products already exist", "count": count}
    sample = [
        {"title": "Wireless Headphones", "description": "Noise-cancelling over-ear headphones", "price": 129.99, "category": "Electronics", "image": "https://images.unsplash.com/photo-1518443155474-2d46acb2b3de?auto=format&fit=crop&w=800&q=60", "in_stock": True},
        {"title": "Smart Watch", "description": "Track fitness and notifications", "price": 199.0, "category": "Electronics", "image": "https://images.unsplash.com/photo-1516570161787-2fd917215a3d?auto=format&fit=crop&w=800&q=60", "in_stock": True},
        {"title": "Espresso Machine", "description": "Barista-quality coffee at home", "price": 349.0, "category": "Home", "image": "https://images.unsplash.com/photo-1470176519524-3cf9e6dccbad?auto=format&fit=crop&w=800&q=60", "in_stock": True},
        {"title": "Running Shoes", "description": "Lightweight and comfortable", "price": 89.99, "category": "Fashion", "image": "https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&w=800&q=60", "in_stock": True},
        {"title": "Backpack", "description": "Durable everyday carry", "price": 59.99, "category": "Accessories", "image": "https://images.unsplash.com/photo-1521093470119-a3acdc43374e?auto=format&fit=crop&w=800&q=60", "in_stock": True},
        {"title": "Bluetooth Speaker", "description": "Portable with deep bass", "price": 79.5, "category": "Electronics", "image": "https://images.unsplash.com/photo-1512446816042-444d641267d4?auto=format&fit=crop&w=800&q=60", "in_stock": True}
    ]
    res = db["product"].insert_many(sample)
    return {"seeded": True, "inserted": len(res.inserted_ids)}

class CartItem(BaseModel):
    product_id: str
    quantity: int

class CheckoutRequest(BaseModel):
    customer_name: str
    customer_email: str
    customer_address: str
    items: List[CartItem]

class CheckoutResponse(BaseModel):
    order_id: str
    total: float

@app.post("/api/checkout", response_model=CheckoutResponse)
def checkout(payload: CheckoutRequest):
    # Fetch products to compute totals
    ids = [ObjectId(i.product_id) for i in payload.items if ObjectId.is_valid(i.product_id)]
    if not ids:
        raise HTTPException(status_code=400, detail="Invalid product IDs")
    products = list(db["product"].find({"_id": {"$in": ids}}))
    price_map = {str(p["_id"]): float(p.get("price", 0)) for p in products}

    subtotal = 0.0
    for item in payload.items:
        pid = item.product_id
        if pid not in price_map:
            raise HTTPException(status_code=400, detail=f"Product not found: {pid}")
        subtotal += price_map[pid] * item.quantity
    tax = round(subtotal * 0.08, 2)
    total = round(subtotal + tax, 2)

    order = Order(
        customer_name=payload.customer_name,
        customer_email=payload.customer_email,
        customer_address=payload.customer_address,
        items=[OrderItem(product_id=i.product_id, quantity=i.quantity) for i in payload.items],
        subtotal=round(subtotal, 2),
        tax=tax,
        total=total,
    )
    order_id = create_document("order", order)
    return CheckoutResponse(order_id=order_id, total=total)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
