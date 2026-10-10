import os
from pathlib import Path
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from agent.tools.browser_session import BrowserSession
from mock_env.chaos import load_chaos

SCREENSHOT_DIR = Path("screenshots")
SCREENSHOT_DIR.mkdir(exist_ok=True)

BASE_URL = "http://localhost:8000"


def _resolve_selector(page_name: str, selector: str) -> str:
    """Apply any active selector overrides for this page."""
    chaos = load_chaos()
    overrides = chaos.get("selector_override", {}).get(page_name, {})
    return overrides.get(selector, selector)

def browser_open(url:str,page_name:str="") -> dict:
    try:
        session=BrowserSession.get()
        full_url = BASE_URL + url if url.startswith("/") else url
        page = session.page()
        page.goto(full_url,wait_until='domcontentloaded')
        return {
            "success":True,
            "result": {"url": full_url, "title": session.page().title()},
            "error": None,
        }
    except Exception as e:
        return {"success": False, "result": {}, "error": str(e)}

def browser_fill(selector:str,value:str,page_name:str="")->dict:
    try:
        session=BrowserSession.get()
        resolved = _resolve_selector(page_name, selector)
        session.page().wait_for_selector(resolved, timeout=5000)
        session.page().fill(resolved, value)
        return {
            "success": True,
            "result": {"selector": resolved, "value": value},
            "error": None,
        }
    except PlaywrightTimeoutError:
        return {
            "success": False,
            "result": {},
            "error": f"selector_not_found: {selector} (tried {_resolve_selector(page_name, selector)})",
        }
    except Exception as e:
        return {"success": False, "result": {}, "error": str(e)}


def browser_click(selector:str,page_name:str="")->dict:
    try:
        session = BrowserSession.get()
        resolved = _resolve_selector(page_name, selector)
        session.page().wait_for_selector(resolved, timeout=5000)
        session.page().click(resolved)
        session.page().wait_for_load_state("domcontentloaded")
        return {
            "success": True,
            "result": {"selector": resolved},
            "error": None,
        }
    except PlaywrightTimeoutError:
        return {
            "success": False,
            "result": {},
            "error": f"selector_not_found: {selector} (tried {_resolve_selector(page_name, selector)})",
        }
    except Exception as e:
        return {"success": False, "result": {}, "error": str(e)}


def browser_read(selector: str) -> dict:
    try:
        session = BrowserSession.get()
        session.page().wait_for_selector(selector, timeout=5000)
        text = session.page().inner_text(selector)
        return {
            "success": True,
            "result": {"selector": selector, "text": text},
            "error": None,
        }
    except PlaywrightTimeoutError:
        return {"success": False, "result": {}, "error": f"selector_not_found: {selector}"}
    except Exception as e:
        return {"success": False, "result": {}, "error": str(e)}


def browser_screenshot(name: str) -> dict:
    try:
        session = BrowserSession.get()
        path = SCREENSHOT_DIR / f"{name}.png"
        session.page().screenshot(path=str(path))
        return {
            "success": True,
            "result": {"path": str(path)},
            "error": None,
        }
    except Exception as e:
        return {"success": False, "result": {}, "error": str(e)}

