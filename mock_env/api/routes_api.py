from fastapi import APIRouter, Depends, HTTPException,Request
from sqlalchemy.orm import Session
from mock_env.api.database import get_db
from mock_env.api import models, schemas
import time
from mock_env.chaos import load_chaos

router = APIRouter(prefix="/api", tags=["api"])


def _chaos_check(request: Request) -> None:
    """
    Raise an HTTPException if chaos says this endpoint should fail.
    Matches against the current request path.
    """
    chaos = load_chaos()
    path = request.url.path

    if chaos.get("api_500_on") == path:
        raise HTTPException(500, f"Simulated internal error on {path}")

    if chaos.get("timeout_on") == path:
        # Simulate a slow endpoint (2 seconds)
        time.sleep(2)
        raise HTTPException(504, f"Simulated timeout on {path}")

    # Duplicate-invoice chaos: only fires on POST /api/invoices
    # (handled inside create_invoice below)


# ---------- Vendors ----------
@router.get("/vendors", response_model=list[schemas.VendorOut])
def list_vendors(request: Request, db: Session = Depends(get_db)):
    _chaos_check(request)
    return db.query(models.Vendor).all()


@router.get("/vendors/{vendor_id}", response_model=schemas.VendorOut)
def get_vendor(vendor_id: str,request:Request, db: Session = Depends(get_db)):
    _chaos_check(request)
    v = db.query(models.Vendor).filter_by(id=vendor_id).first()
    if not v:
        raise HTTPException(404, "Vendor not found")
    return v


# ---------- Purchase Orders ----------
@router.get("/purchase_orders/{po_number}")
def get_po(po_number: str, request: Request , db: Session = Depends(get_db)):
    _chaos_check(request)
    po = db.query(models.PurchaseOrder).filter_by(po_number=po_number).first()
    if not po:
        raise HTTPException(404, "PO not found")
    return {
        "po_number": po.po_number,
        "vendor_id": po.vendor_id,
        "amount": po.amount,
        "status": po.status,
    }


# ---------- Invoices ----------
@router.get("/invoices", response_model=list[schemas.InvoiceOut])
def list_invoices(request:Request,db: Session = Depends(get_db)):
    _chaos_check(request)
    return db.query(models.Invoice).all()


@router.get("/invoices/{invoice_id}", response_model=schemas.InvoiceOut)
def get_invoice(invoice_id: str, request: Request, db: Session = Depends(get_db)):
    _chaos_check(request)
    inv = db.query(models.Invoice).filter_by(id=invoice_id).first()
    if not inv:
        raise HTTPException(404, "Invoice not found")
    return inv


@router.post("/invoices", response_model=schemas.InvoiceOut, status_code=201)
def create_invoice(payload: schemas.InvoiceCreate, request: Request, db: Session = Depends(get_db)):
    _chaos_check(request)


    chaos = load_chaos()

        
    if chaos.get("duplicate_invoice"):
        # Force the duplicate path regardless of DB state
        raise HTTPException(409, f"Duplicate invoice id: {payload.id}")

    existing = db.query(models.Invoice).filter_by(id=payload.id).first()
    if existing:
        raise HTTPException(409, "Duplicate invoice id")

    inv = models.Invoice(**payload.model_dump())
    db.add(inv)
    db.commit()
    db.refresh(inv)
    return inv


# ---------- Payments ----------
@router.post("/payments", response_model=schemas.PaymentOut, status_code=201)
def schedule_payment(payload: schemas.PaymentCreate, request: Request, db: Session = Depends(get_db)):
    _chaos_check(request)
    inv = db.query(models.Invoice).filter_by(id=payload.invoice_id).first()
    if not inv:
        raise HTTPException(404, "Invoice not found")
    payment_id = f"PAY-{payload.invoice_id}"
    existing = db.query(models.Payment).filter_by(id=payment_id).first()
    if existing:
        raise HTTPException(409, "Payment already exists")
    p = models.Payment(id=payment_id, invoice_id=payload.invoice_id, amount=payload.amount)
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


# ---------- Employees ----------
@router.get("/employees/{employee_id}")
def get_employee(employee_id: str, request: Request, db: Session = Depends(get_db)):
    _chaos_check(request)
    e = db.query(models.Employee).filter_by(id=employee_id).first()
    if not e:
        raise HTTPException(404, "Employee not found")
    return {"id": e.id, "name": e.name, "department": e.department}


@router.delete("/invoices/{invoice_id}")
def delete_invoice(invoice_id: str, db: Session = Depends(get_db)):
    inv = db.query(models.Invoice).filter_by(id=invoice_id).first()
    if not inv:
        raise HTTPException(404, "Invoice not found")
    db.delete(inv)
    db.commit()
    return {"deleted": invoice_id}


# ---------- Health ----------
@router.get("/health")
def health():
    return {"status": "ok"}



from mock_env.chaos import update_chaos, reset_chaos, load_chaos as _load

@router.post("/chaos/set")
def chaos_set(config: dict):
    return {"chaos": update_chaos(config)}


@router.post("/chaos/reset")
def chaos_clear():
    return {"chaos": reset_chaos()}


@router.get("/chaos")
def chaos_get():
    return {"chaos": _load()}