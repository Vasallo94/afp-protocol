import json
from pathlib import Path

from afp.sinks.base import Sink


class LocalSink(Sink):
    name = "local"

    def __init__(self, base_dir: Path = Path(".")):
        self.spool = Path(base_dir) / ".afp" / "reports.jsonl"

    def submit(self, report: dict) -> str:
        self.spool.parent.mkdir(parents=True, exist_ok=True)
        with self.spool.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(report, ensure_ascii=False) + "\n")
        return f"local:{self.spool}"
