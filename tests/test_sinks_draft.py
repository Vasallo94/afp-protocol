import json

from afp.sinks.draft import DraftSink


def test_draft_sink_writes_one_file_per_report(tmp_path):
    sink = DraftSink(base_dir=tmp_path)
    ref = sink.submit({"report_id": "afp_abc", "goal": "x"})
    draft = tmp_path / ".afp" / "drafts" / "afp_abc.json"
    assert draft.exists()
    assert json.loads(draft.read_text())["goal"] == "x"
    assert "afp_abc" in ref


def test_draft_sink_handles_missing_report_id(tmp_path):
    sink = DraftSink(base_dir=tmp_path)
    ref = sink.submit({"goal": "sin id"})
    drafts = list((tmp_path / ".afp" / "drafts").glob("*.json"))
    assert len(drafts) == 1
    assert "draft" in ref.lower() or drafts[0].stem in ref
