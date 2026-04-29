from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Boolean,
    ForeignKey, Text, Numeric, Date
)
from sqlalchemy.orm import DeclarativeBase, relationship
from datetime import datetime


class Base(DeclarativeBase):
    pass


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(200), unique=True, nullable=False)
    city = Column(String(100), nullable=False)
    signup_date = Column(Date, nullable=False)
    tier = Column(String(20), nullable=False, default="free")

    orders = relationship("Order", back_populates="customer")


class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    city = Column(String(100), nullable=False)
    rating = Column(Float, nullable=False)
    lead_time_days = Column(Integer, nullable=False)

    products = relationship("Product", back_populates="supplier")


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    category = Column(String(100), nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    cost = Column(Numeric(10, 2), nullable=False)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
    stock_quantity = Column(Integer, nullable=False, default=0)

    supplier = relationship("Supplier", back_populates="products")
    order_items = relationship("OrderItem", back_populates="product")


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    order_date = Column(DateTime, nullable=False)
    status = Column(String(50), nullable=False)
    total_amount = Column(Numeric(10, 2), nullable=False)
    delivery_city = Column(String(100), nullable=False)

    customer = relationship("Customer", back_populates="orders")
    items = relationship("OrderItem", back_populates="order")


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)
    discount_pct = Column(Float, nullable=False, default=0.0)

    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")


class QueryLog(Base):
    __tablename__ = "query_log"

    id = Column(Integer, primary_key=True, index=True)
    question = Column(Text, nullable=False)
    sql = Column(Text)
    explanation = Column(Text)
    row_count = Column(Integer)
    intent_type = Column(String(50))
    tables_used = Column(Text)
    latency_ms = Column(Float)
    tokens_used = Column(Integer)
    cost_usd = Column(Float)
    self_corrections = Column(Integer, default=0)
    clarification_requested = Column(Boolean, default=False)
    execution_error = Column(Boolean, default=False)
    error_message = Column(Text)
    sql_correct = Column(Boolean)
    result_correct = Column(Boolean)
    rating = Column(Integer)
    feedback_comment = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
