import json
from pathlib import Path
from datetime import datetime


REPORT_DIR = Path("reports")
REPORT_DIR.mkdir(exist_ok=True)


def save_report(report: dict) -> Path:
    """Save a FinalReport dict to reports/<thread_id>.json."""
    thread_id = report.get("thread_id") or f"run-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
    path = REPORT_DIR / f"{thread_id}.json"
    path.write_text(json.dumps(report, indent=2, default=str))
    return path


def list_reports() -> list[Path]:
    return sorted(REPORT_DIR.glob("*.json"))


def load_report(path: str | Path) -> dict:
    return json.loads(Path(path).read_text())