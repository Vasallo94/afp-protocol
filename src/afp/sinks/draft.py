import json
from pathlib import Path
from uuid import uuid4

from afp.sinks.base import Sink


class DraftSink(Sink):
    """Escribe un borrador para revisión humana ANTES de enviarse a ningún sitio."""

    name = "draft"

    def __init__(self, base_dir: Path = Path(".")):
        self.dir = Path(base_dir) / ".afp" / "drafts"

    def submit(self, report: dict) -> str:
        self.dir.mkdir(parents=True, exist_ok=True)
        report_id = report.get("report_id") or f"draft_{uuid4().hex}"
        path = self.dir / f"{report_id}.json"
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return f"draft:{path}"
