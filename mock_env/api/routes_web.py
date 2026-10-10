from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from mock_env.api.database import get_db
from mock_env.api import models

router = APIRouter(prefix="/app", tags=["web"])
templates = Jinja2Templates(directory="mock_env/web/templates")


@router.get("/erp", response_class=HTMLResponse)
def erp_page(request: Request):
    return templates.TemplateResponse(
    request=request,
    name="erp.html",
    context={"message": None},
)


@router.post("/erp", response_class=HTMLResponse)
def erp_submit(
    request: Request,
    invoice_id: str = Form(...),
    vendor_id: str = Form(...),
    amount: float = Form(...),
    due_date: str = Form(""),
    po_number: str = Form(""),
    db: Session = Depends(get_db),
):
    existing = db.query(models.Invoice).filter_by(id=invoice_id).first()
    if existing:
        return templates.TemplateResponse(
            request=request,
            name="erp.html",
            context={
                "message": f"ERROR: Invoice {invoice_id} already exists"
            },
            status_code=409,
        )
    inv = models.Invoice(
        id=invoice_id,
        vendor_id=vendor_id,
        amount=amount,
        due_date=due_date or None,
        po_number=po_number or None,
        status="pending",
    )
    db.add(inv)
    db.commit()
    return templates.TemplateResponse(
        request=request,
        name="erp.html",
        context={
            "message": f"SUCCESS: Invoice {invoice_id} created"
        },
    )


@router.get("/crm", response_class=HTMLResponse)
def crm_page(request: Request, q: str = "", db: Session = Depends(get_db)):
    query = db.query(models.Vendor)
    if q:
        query = query.filter(models.Vendor.name.ilike(f"%{q}%"))
    vendors = query.all()
    return templates.TemplateResponse(
        request=request,
        name="crm.html",
        context={
            "vendors": vendors,
            "q": q,
        },
    )