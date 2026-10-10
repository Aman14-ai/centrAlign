import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]  # project root
FILES_DIR = BASE_DIR / "mock_env" / "files"


def list_files(directory: str = "") -> dict:
    """
    List files in a subdirectory of mock_env/files.
    directory: relative path like 'invoices' or '' for all.
    """
    try:
        target = FILES_DIR / directory
        if not target.exists():
            return {"success": False, "error": f"Directory not found: {directory}"}

        files = []
        for p in sorted(target.rglob("*")):
            if p.is_file():
                files.append(str(p.relative_to(FILES_DIR)))

        return {
            "success": True,
            "result": {"directory": directory, "files": files},
            "error": None,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


from mock_env.chaos import load_chaos


def read_file(path: str) -> dict:
    try:
        target = FILES_DIR / path
        if not target.exists():
            return {"success": False, "result": {}, "error": f"file_not_found: {path}"}

        content = target.read_text(encoding="utf-8")

        # Chaos: omit a field
        chaos = load_chaos()
        field = chaos.get("missing_field")
        if field:
            import re
            content = re.sub(rf"^{field}:.*$", f"{field}:", content, flags=re.MULTILINE | re.IGNORECASE)

        return {
            "success": True,
            "result": {"path": path, "content": content},
            "error": None,
        }
    except Exception as e:
        return {"success": False, "result": {}, "error": str(e)}

    