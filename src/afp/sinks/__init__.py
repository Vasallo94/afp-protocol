from pathlib import Path

from afp.sinks.draft import DraftSink
from afp.sinks.github import GitHubIssuesSink
from afp.sinks.local import LocalSink

LOCAL_SINKS = {"local", "draft"}
# github_issues está implementado; gitlab_issues/file/http son placeholders de Fase 1b.
REMOTE_SINKS = {"github_issues", "gitlab_issues", "file", "http"}


class SinkNotAllowed(Exception):
    """Se pidió un sink remoto que la política de routing no permite."""


def _owned_base(uri: str | None) -> str | None:
    """Reduce un subject_uri a la 'base poseída' por el manifiesto.

    El anti-spoofing comprueba propiedad, no igualdad literal:
    - El fragmento `#sub-tool` identifica una sub-herramienta DENTRO del
      subject que el manifiesto ya declara como propio, no un subject distinto.
    - En PURL, la versión `@x.y.z` no cambia la propiedad del paquete.

    Por eso comparamos la base (sin `#fragment` ni `@version` en PURL). El
    threat model (§8) se mantiene: un subject de OTRO dueño tiene otra base y
    sigue bloqueándose.
    """
    if uri is None:
        return None
    base = uri.split("#", 1)[0]
    if base.startswith("pkg:") and "@" in base:
        base = base.split("@", 1)[0]
    return base


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
    - sink remoto -> ANTI-SPOOFING (§8 threat model): la BASE del subject_uri
      del reporte (sin `#fragment` ni `@version` PURL) debe coincidir con la
      del manifest declarado por el dueño; si no, se bloquea.
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
        if manifest is None or _owned_base(report_subject) != _owned_base(manifest_subject):
            raise SinkNotAllowed(
                "anti-spoofing: la base del subject_uri del reporte "
                f"({_owned_base(report_subject)!r}) no coincide con la del "
                f"manifest ({_owned_base(manifest_subject)!r})"
            )
    return get_sink(chosen, base_dir=base_dir, manifest=decision.manifest)
