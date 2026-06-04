from pathlib import Path
from urllib.parse import urlsplit

from afp.sinks.draft import DraftSink
from afp.sinks.github import GitHubIssuesSink
from afp.sinks.gitlab import GitLabIssuesSink
from afp.sinks.local import LocalSink

LOCAL_SINKS = {"local", "draft"}
# github_issues está implementado; gitlab_issues/file/http son placeholders de Fase 1b.
REMOTE_SINKS = {"github_issues", "gitlab_issues", "file", "http"}


class SinkNotAllowed(Exception):
    """Se pidió un sink remoto que la política de routing no permite."""


def _scheme_of(uri: str) -> str:
    if "://" in uri:
        return uri.split("://", 1)[0]
    if ":" in uri:
        return uri.split(":", 1)[0]
    return ""


def _purl_base(uri: str) -> str:
    """Base PURL poseída: sin `#fragment` (sub-tool) ni `@version`."""
    base = uri.split("#", 1)[0]
    if "@" in base:
        base = base.split("@", 1)[0]
    return base


def _segments(path: str) -> list[str]:
    return [p for p in path.split("/") if p]


def subject_is_owned_by(report_subject: str | None, manifest_subject: str | None) -> bool:
    """¿El subject del reporte cae bajo el subject que el manifiesto declara?

    Anti-spoofing (§8): comprueba PROPIEDAD, no igualdad literal, según el tipo:
    - **PURL**: misma base de paquete (la `@version` no cambia el dueño; el
      `#fragment` identifica una sub-tool del paquete poseído).
    - **http(s)/mcp**: mismo esquema, mismo **host/autoridad** (comparación
      exacta — `api.acme.com.evil.com` ≠ `api.acme.com`) y el path del reporte
      es el del manifiesto o un **sub-path por segmentos** (`/v1` posee
      `/v1/charges` pero no `/v1abc`). Query y fragment se ignoran. Esto permite
      que un API HTTP posea todos sus endpoints sin tener que enumerarlos, y
      que un host multi-tenant se acote por prefijo declarado.
    - **otros** (p.ej. `afp:`): igualdad de base sin `#fragment`.
    """
    if not report_subject or not manifest_subject:
        return False
    r_scheme, m_scheme = _scheme_of(report_subject), _scheme_of(manifest_subject)
    if r_scheme != m_scheme:
        return False
    if r_scheme == "pkg":
        return _purl_base(report_subject) == _purl_base(manifest_subject)
    if r_scheme in ("http", "https", "mcp"):
        r, m = urlsplit(report_subject), urlsplit(manifest_subject)
        if r.netloc.lower() != m.netloc.lower():
            return False
        r_seg, m_seg = _segments(r.path), _segments(m.path)
        return r_seg[: len(m_seg)] == m_seg
    return report_subject.split("#", 1)[0] == manifest_subject.split("#", 1)[0]


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
    if sink_type == "gitlab_issues":
        if manifest is None:
            raise ValueError("gitlab_issues requiere un manifest con repo")
        return GitLabIssuesSink(
            repo=manifest.sink["repo"],
            label=manifest.sink.get("label", "afp-report"),
            host=manifest.sink.get("host"),
        )
    raise ValueError(f"sink desconocido: {sink_type!r}")


def route(requested, decision, report=None, *, base_dir: Path = Path(".")):
    """Elige un sink respetando la decisión de routing.

    - requested None  -> 'draft' (siempre seguro).
    - requested no permitido por la política -> SinkNotAllowed.
    - sink remoto -> ANTI-SPOOFING (§8 threat model): el subject_uri del reporte
      debe caer bajo el subject que declara el manifest del dueño (ver
      `subject_is_owned_by`); si no, se bloquea.
    """
    chosen = requested or "draft"
    if chosen not in decision.allowed_sinks:
        raise SinkNotAllowed(
            f"sink {chosen!r} no permitido; permitidos: {decision.allowed_sinks}"
        )
    if chosen in REMOTE_SINKS:
        manifest = decision.manifest
        report_subject = (report or {}).get("subject_uri")
        manifest_subject = getattr(manifest, "subject_uri", None)
        if manifest is None or not subject_is_owned_by(report_subject, manifest_subject):
            raise SinkNotAllowed(
                "anti-spoofing: el subject_uri del reporte "
                f"({report_subject!r}) no cae bajo el del manifest "
                f"({manifest_subject!r})"
            )
    return get_sink(chosen, base_dir=base_dir, manifest=decision.manifest)
