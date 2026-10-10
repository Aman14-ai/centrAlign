from agent.tools import files, browser, api,memory_tools

TOOLS = {
    # File tools
    "list_files": files.list_files,
    "read_file": files.read_file,

    # Browser tools
    "browser_open": browser.browser_open,
    "browser_fill": browser.browser_fill,
    "browser_click": browser.browser_click,
    "browser_read": browser.browser_read,
    "browser_screenshot": browser.browser_screenshot,

    # API tools
    "api_get": api.api_get,
    "api_post": api.api_post,
    "api_get_invoice": api.api_get_invoice,
    "api_create_invoice": api.api_create_invoice,
    "api_get_vendor": api.api_get_vendor,
    "api_get_po": api.api_get_po,
    "api_delete":api.api_delete,

    "remember":memory_tools.remember
}


TOOL_DESCRIPTIONS = """
FILE TOOLS:
1. list_files(directory: str) -> dict
   Lists files under mock_env/files/<directory>. Example: list_files("invoices")

2. read_file(path: str) -> dict
   Reads a file. Example: read_file("invoices/acme_inv_001.txt")

BROWSER TOOLS:
3. browser_open(url: str, page_name: str = "") -> dict
   Opens a URL in the shared browser. Use relative paths like "/app/erp".
   page_name: "erp", "crm", or "" — used for chaos routing.

4. browser_fill(selector: str, value: str, page_name: str = "") -> dict
   Fills an input field. Example: browser_fill("#invoice_id", "INV-001", page_name="erp")

5. browser_click(selector: str, page_name: str = "") -> dict
   Clicks an element. Example: browser_click("#submit-btn", page_name="erp")

6. browser_read(selector: str) -> dict
   Reads the visible text inside an element.

7. browser_screenshot(name: str) -> dict
   Saves a screenshot to screenshots/<name>.png. Use for evidence.

API TOOLS:
8. api_get(endpoint: str) -> dict
   GET request. Example: api_get("/api/vendors")

9. api_post(endpoint: str, data: dict) -> dict
   POST request with JSON body.

10. api_get_invoice(invoice_id: str) -> dict
    Fetches a single invoice by id.

11. api_create_invoice(invoice_id, vendor_id, amount, due_date="", po_number="") -> dict
    Creates an invoice via the API.

12. api_get_vendor(vendor_id: str) -> dict
13. api_get_po(po_number: str) -> dict

14. api_delete(endpoint: str)

15. remember(note: str) -> dict
    Save a reasoning note to the scratchpad. Use for decisions,
    partial observations, or plans that don't fit an entity.
    Example: remember("Chose V001 because PO-1001 matches")
"""