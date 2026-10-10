from sqlalchemy import Column, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from mock_env.api.database import Base

# for database 

class Vendor(Base):
    __tablename__ = "vendors"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    aliases = Column(String, default="")   # comma-separated
    email = Column(String)


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"
    po_number = Column(String, primary_key=True)
    vendor_id = Column(String, ForeignKey("vendors.id"))
    amount = Column(Float, nullable=False)
    status = Column(String, default="open")
    vendor = relationship("Vendor")


class Invoice(Base):
    __tablename__ = "invoices"
    id = Column(String, primary_key=True)
    vendor_id = Column(String, ForeignKey("vendors.id"))
    amount = Column(Float, nullable=False)
    due_date = Column(String, nullable=True)
    po_number = Column(String, ForeignKey("purchase_orders.po_number"), nullable=True)
    status = Column(String, default="pending")
    vendor = relationship("Vendor")
    purchase_order = relationship("PurchaseOrder")


class Employee(Base):
    __tablename__ = "employees"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    department = Column(String)


class ExpenseReport(Base):
    __tablename__ = "expense_reports"
    id = Column(String, primary_key=True)
    employee_id = Column(String, ForeignKey("employees.id"))
    amount = Column(Float, nullable=False)
    category = Column(String)
    status = Column(String, default="pending")
    employee = relationship("Employee")


class Payment(Base):
    __tablename__ = "payments"
    id = Column(String, primary_key=True)
    invoice_id = Column(String, ForeignKey("invoices.id"))
    amount = Column(Float, nullable=False)
    status = Column(String, default="scheduled")
    invoice = relationship("Invoice")