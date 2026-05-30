from pathlib import Path

from afp.sinks.draft import DraftSink
from afp.sinks.github import GitHubIssuesSink
from afp.sinks.local import LocalSink

LOCAL_SINKS = {"local", "draft"}
# github_issues está implementado; gitlab_issues/file/http son placeholders de Fase 1b.
REMOTE_SINKS = {"github_issues", "gitlab_issues", "file", "http"}


class SinkNotAllowed(Exception):
    """Se pidió un sink remoto que la política de routing no permite."""


def get_sink(sink_type: str, *, base_dir: Path = Path("."), manifest=None):
    if sink_type == "local":
        return LocalSink(base_dir=base_dir)
    if sink_type == "draft":
        return DraftSink(base_dir=base_dir)
    if sink_type == "github_issues":
        if manifest is None:
            raise ValueError("github_issues requiere un manifest con repo/label")
        return GitHubIssuesSink(
            repo=manifest.sink["repo"],
            label=manifest.sink.get("label", "afp-report"),
        )
    raise ValueError(f"sink desconocido: {sink_type!r}")


def route(requested, decision, report=None, *, base_dir: Path = Path(".")):
    """Elige un sink respetando la decisión de routing.

    - requested None  -> 'draft' (siempre seguro).
    - requested no permitido por la política -> SinkNotAllowed.
    - sink remoto -> ANTI-SPOOFING (§8 threat model): el subject_uri del
      reporte debe coincidir con el del manifest declarado por el dueño;
      si no, se bloquea.
    """
    chosen = requested or "draft"
    if chosen not in decision.allowed_sinks:
        raise SinkNotAllowed(
            f"sink {chosen!r} no permitido; permitidos: {decision.allowed_sinks}"
        )
    if chosen in REMOTE_SINKS:
        manifest = decision.manifest
        report_subject = (report or {}).get("subject_uri")
        if manifest is None or report_subject != manifest.subject_uri:
            raise SinkNotAllowed(
                "anti-spoofing: subject_uri del reporte "
                f"({report_subject!r}) no coincide con el del manifest "
                f"({getattr(manifest, 'subject_uri', None)!r})"
            )
    return get_sink(chosen, base_dir=base_dir, manifest=decision.manifest)
