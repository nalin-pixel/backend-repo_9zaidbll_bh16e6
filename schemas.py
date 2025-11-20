"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
These schemas are used for data validation in your application.

Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- User -> "user" collection
- Product -> "product" collection
- BlogPost -> "blogs" collection
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List

# Core user schema (minimal for orders)
class User(BaseModel):
    """
    Users collection schema
    Collection name: "user" (lowercase of class name)
    """
    name: str = Field(..., description="Full name")
    email: EmailStr = Field(..., description="Email address")
    address: str = Field(..., description="Address")
    age: Optional[int] = Field(None, ge=0, le=120, description="Age in years")
    is_active: bool = Field(True, description="Whether user is active")

class Product(BaseModel):
    """
    Products collection schema
    Collection name: "product" (lowercase of class name)
    """
    title: str = Field(..., description="Product title")
    description: Optional[str] = Field(None, description="Product description")
    price: float = Field(..., ge=0, description="Price in dollars")
    category: str = Field(..., description="Product category")
    image: Optional[str] = Field(None, description="Image URL")
    in_stock: bool = Field(True, description="Whether product is in stock")

class OrderItem(BaseModel):
    product_id: str = Field(..., description="Referenced product id")
    quantity: int = Field(..., ge=1, description="Quantity ordered")

class Order(BaseModel):
    """
    Orders collection schema
    Collection name: "order"
    """
    customer_name: str = Field(...)
    customer_email: EmailStr = Field(...)
    customer_address: str = Field(...)
    items: List[OrderItem]
    subtotal: float = Field(..., ge=0)
    tax: float = Field(..., ge=0)
    total: float = Field(..., ge=0)
    status: str = Field("processing", description="Order status")

# Add your own schemas here:
# --------------------------------------------------

# Note: The Flames database viewer will automatically:
# 1. Read these schemas from GET /schema endpoint
# 2. Use them for document validation when creating/editing
# 3. Handle all database operations (CRUD) directly
# 4. You don't need to create any database endpoints!
