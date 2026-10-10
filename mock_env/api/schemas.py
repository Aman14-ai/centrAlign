from pydantic import BaseModel
from typing import Optional


class VendorOut(BaseModel):
    id: str
    name: str
    aliases: str
    email: Optional[str] = None

    class Config:
        from_attributes = True #Allows Pydantic to read SQLAlchemy database objects directly and automatically convert them into clean JSON responses for your API.


class InvoiceCreate(BaseModel):
    id: str
    vendor_id: str
    amount: float
    due_date: Optional[str] = None
    po_number: Optional[str] = None


class InvoiceOut(BaseModel):
    id: str
    vendor_id: str
    amount: float
    due_date: Optional[str] = None
    po_number: Optional[str] = None
    status: str

    class Config:
        from_attributes = True


class PaymentCreate(BaseModel):
    invoice_id: str
    amount: float


class PaymentOut(BaseModel):
    id: str
    invoice_id: str
    amount: float
    status: str

    class Config:
        from_attributes = True