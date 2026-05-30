import json

from afp.sinks.local import LocalSink


def test_local_sink_appends_jsonl(tmp_path):
    sink = LocalSink(base_dir=tmp_path)
    ref1 = sink.submit({"report_id": "afp_1", "goal": "a"})
    ref2 = sink.submit({"report_id": "afp_2", "goal": "b"})
    spool = tmp_path / ".afp" / "reports.jsonl"
    assert spool.exists()
    lines = spool.read_text().strip().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["report_id"] == "afp_1"
    assert str(spool) in ref1 and str(spool) in ref2
