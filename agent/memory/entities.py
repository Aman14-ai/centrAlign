from pydantic import BaseModel, Field
from typing import Optional


class Vendor(BaseModel):
    id: str
    name: str
    aliases: list[str] = Field(default_factory=list)
    email: Optional[str] = None

    def matches_name(self, query: str) -> bool:
        q = query.lower().strip()
        if q in self.name.lower():
            return True
        return any(q in a.lower() for a in self.aliases)


class PurchaseOrder(BaseModel):
    po_number: str
    vendor_id: str
    amount: float
    status: str = "open"


class Invoice(BaseModel):
    id: str
    vendor_id: str
    amount: float
    due_date: Optional[str] = None
    po_number: Optional[str] = None
    status: str = "pending"


class Employee(BaseModel):
    id: str
    name: str
    department: Optional[str] = None


class ExpenseReport(BaseModel):
    id: str
    employee_id: str
    amount: float
    category: Optional[str] = None
    status: str = "pending"


class FileFacts(BaseModel):
    """Structured facts extracted from a document file."""
    path: str
    vendor: Optional[str] = None
    invoice_number: Optional[str] = None
    amount: Optional[float] = None
    due_date: Optional[str] = None
    po_number: Optional[str] = None
    source: str = "extractor"   # "extractor" | "regex" | "manual"

    def missing_fields(self) -> list[str]:
        fields = ["vendor", "invoice_number", "amount", "due_date", "po_number"]
        return [f for f in fields if getattr(self, f) is None]