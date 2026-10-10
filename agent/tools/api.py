import httpx


BASE_URL = "http://localhost:8000"


def api_get(endpoint: str) -> dict:
    try:
        r = httpx.get(BASE_URL + endpoint, timeout=15)
        if r.status_code >= 400:
            return {
                "success": False,
                "result": {"status_code": r.status_code},
                "error": f"api_error_{r.status_code}: {r.text[:200]}",
            }
        return {"success": True, "result": r.json(), "error": None}
    except httpx.TimeoutException:
        return {"success": False, "result": {}, "error": f"timeout: {endpoint}"}
    except Exception as e:
        return {"success": False, "result": {}, "error": str(e)}


def api_post(endpoint: str, data: dict) -> dict:
    try:
        r = httpx.post(BASE_URL + endpoint, json=data, timeout=15)
        if r.status_code >= 400:
            return {
                "success": False,
                "result": {"status_code": r.status_code},
                "error": f"api_error_{r.status_code}: {r.text[:200]}",
            }
        return {"success": True, "result": r.json(), "error": None}
    except httpx.TimeoutException:
        return {"success": False, "result": {}, "error": f"timeout: {endpoint}"}
    except Exception as e:
        return {"success": False, "result": {}, "error": str(e)}


# Dedicated helpers stay the same
def api_get_invoice(invoice_id: str) -> dict:
    return api_get(f"/api/invoices/{invoice_id}")


def api_create_invoice(
    invoice_id: str,
    vendor_id: str,
    amount: float,
    due_date: str = "",
    po_number: str = "",
) -> dict:
    return api_post("/api/invoices", {
        "id": invoice_id,
        "vendor_id": vendor_id,
        "amount": amount,
        "due_date": due_date or None,
        "po_number": po_number or None,
    })


def api_get_vendor(vendor_id: str) -> dict:
    return api_get(f"/api/vendors/{vendor_id}")


def api_get_po(po_number: str) -> dict:
    return api_get(f"/api/purchase_orders/{po_number}")


def api_delete(endpoint: str) -> dict:
    try:
        r = httpx.delete(BASE_URL + endpoint, timeout=15)
        if r.status_code >= 400:
            return {
                "success": False,
                "result": {"status_code": r.status_code},
                "error": f"api_error_{r.status_code}: {r.text[:200]}",
            }
        return {"success": True, "result": r.json(), "error": None}
    except Exception as e:
        return {"success": False, "result": {}, "error": str(e)}