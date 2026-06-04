import json

from afp.sinks import deposit


class _CountingSink:
    """Sink de prueba que cuenta envíos y devuelve una ref incremental."""

    def __init__(self, name):
        self.name = name
        self.calls = 0

    def submit(self, report):
        self.calls += 1
        return f"{self.name}:issue/{self.calls}"


def _report():
    return {"report_id": "afp_dedupe", "subject_uri": "pkg:npm/x", "goal": "g"}


def test_remote_resubmit_is_idempotent(tmp_path):
    sink = _CountingSink("github_issues")
    first = deposit(sink, _report(), base_dir=tmp_path)
    second = deposit(sink, _report(), base_dir=tmp_path)
    assert sink.calls == 1  # el segundo no vuelve a crear el issue
    assert first == second
    ledger = json.loads((tmp_path / ".afp" / "submitted.json").read_text())
    assert ledger["afp_dedupe"] == first


def test_remote_without_report_id_is_not_deduped(tmp_path):
    sink = _CountingSink("github_issues")
    deposit(sink, {"subject_uri": "pkg:npm/x", "goal": "g"}, base_dir=tmp_path)
    deposit(sink, {"subject_uri": "pkg:npm/x", "goal": "g"}, base_dir=tmp_path)
    assert sink.calls == 2


def test_local_sink_is_not_deduped(tmp_path):
    # local es un spool de append; no se deduplica.
    sink = _CountingSink("local")
    deposit(sink, _report(), base_dir=tmp_path)
    deposit(sink, _report(), base_dir=tmp_path)
    assert sink.calls == 2


def test_different_report_ids_create_separate_issues(tmp_path):
    sink = _CountingSink("gitlab_issues")
    a = deposit(sink, {"report_id": "afp_a", "goal": "g"}, base_dir=tmp_path)
    b = deposit(sink, {"report_id": "afp_b", "goal": "g"}, base_dir=tmp_path)
    assert sink.calls == 2
    assert a != b
