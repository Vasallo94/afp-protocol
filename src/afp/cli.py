import json
from pathlib import Path

import typer

from afp import __version__
from afp.discovery import discover
from afp.enums import FaultDomain, FrictionType, Severity
from afp.manifest import ManifestInvalid, load_manifest
from afp.models import FieldReport
from afp.redact import SecretDetected
from afp.sinks import SinkNotAllowed, deposit, route
from afp.validate import ReportInvalid, validate_report

app = typer.Typer(help="AFP — Agent Feedback Protocol CLI")
drafts_app = typer.Typer(help="Revisa y promueve drafts locales AFP.")
app.add_typer(drafts_app, name="drafts")


def _build_report(from_path: Path) -> dict:
    partial = json.loads(Path(from_path).read_text())
    if "report_id" in partial:
        fr = FieldReport.from_dict(partial)
    else:
        fr = FieldReport.create(**partial)
    data = fr.to_dict()
    validate_report(data)
    return data


def _submit_report(data: dict, *, dir_: Path, sink: str | None):
    decision = discover(dir_)
    chosen = route(sink, decision, report=data, base_dir=dir_)
    ref = deposit(chosen, data, base_dir=dir_)
    return chosen.name, ref


def _drafts_dir(dir_: Path) -> Path:
    return Path(dir_) / ".afp" / "drafts"


def _draft_paths(dir_: Path) -> list[Path]:
    drafts_dir = _drafts_dir(dir_)
    if not drafts_dir.exists():
        return []
    return sorted(drafts_dir.glob("*.json"))


def _resolve_draft(ref: str, *, dir_: Path) -> Path:
    path = Path(ref)
    if path.is_file():
        return path
    drafts_dir = _drafts_dir(dir_)
    candidates = [drafts_dir / ref, drafts_dir / f"{ref}.json"]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    for draft in _draft_paths(dir_):
        try:
            data = json.loads(draft.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if data.get("report_id") == ref or draft.stem == ref:
            return draft
    raise FileNotFoundError(f"draft no encontrado: {ref}")


def _render_report_markdown(report: dict) -> str:
    lines = [
        "## AFP Field Report",
        "",
        f"- Report: `{report.get('report_id', 'unknown')}`",
        f"- Subject: `{report.get('subject_uri', 'unknown')}`",
        f"- Type: `{report.get('friction_type', 'unknown')}`",
        f"- Fault domain: `{report.get('fault_domain', 'unknown')}`",
        f"- Severity: `{report.get('severity', 'unknown')}`",
    ]
    if report.get("timestamp"):
        lines.append(f"- Timestamp: `{report['timestamp']}`")
    for title, key in [
        ("Goal", "goal"),
        ("Expected", "expectation"),
        ("Observed", "observed"),
        ("Workaround", "workaround"),
    ]:
        value = report.get(key)
        if value:
            lines.extend(["", f"### {title}", "", str(value)])
    return "\n".join(lines)


def review_notice(dir_: Path) -> str | None:
    """Mensaje de revisión si hay drafts pendientes; None si no hay.

    Cuenta paths `*.json` bajo `.afp/drafts/` sin parsearlos: un draft inválido
    sigue siendo algo que el humano debe atender. El prefijo `AFP-REVIEW:` es el
    contrato de integración (humano + harness).
    """
    n = len(_draft_paths(dir_))
    if n == 0:
        return None
    noun = "draft pendiente" if n == 1 else "drafts pendientes"
    return (
        f"AFP-REVIEW: {n} {noun} de revisión humana → "
        f"afp drafts list --dir {str(Path(dir_))}"
    )


@app.command()
def report(
    from_: Path = typer.Option(..., "--from", help="JSON parcial con los campos del reporte"),
    out: Path = typer.Option(None, "--out", help="Dónde escribir el reporte completo"),
    submit_: bool = typer.Option(False, "--submit", help="Deposita el reporte tras construirlo"),
    dir_: Path = typer.Option(
        Path("."), "--dir", help="Directorio donde buscar afp.json al usar --submit"
    ),
    sink: str = typer.Option(None, "--sink", help="Sink solicitado al usar --submit"),
):
    """Construye un field report completo (añade id/timestamp/schema_version) y lo valida."""
    try:
        data = _build_report(from_)
    except (ReportInvalid, SecretDetected) as exc:
        typer.echo(f"ERROR: {exc}", err=True)
        raise typer.Exit(code=1)
    text = json.dumps(data, ensure_ascii=False, indent=2)
    if out:
        Path(out).write_text(text, encoding="utf-8")
        typer.echo(f"OK: reporte escrito en {out}")
    if submit_:
        try:
            sink_name, ref = _submit_report(data, dir_=dir_, sink=sink)
        except SinkNotAllowed as exc:
            typer.echo(f"ERROR: {exc}", err=True)
            raise typer.Exit(code=1)
        typer.echo(f"OK: depositado vía {sink_name} -> {ref}")
    elif not out:
        typer.echo(text)


@app.command()
def validate(path: Path = typer.Argument(..., help="Reporte JSON a validar")):
    """Valida un field report contra el JSON Schema + hard-block de secretos."""
    data = json.loads(Path(path).read_text())
    try:
        validate_report(data)
    except (ReportInvalid, SecretDetected) as exc:
        typer.echo(f"INVALID: {exc}", err=True)
        raise typer.Exit(code=1)
    typer.echo("OK: reporte válido")


@app.command("validate-manifest")
def validate_manifest(path: Path = typer.Argument(..., help="afp.json a validar")):
    """Valida un manifiesto afp.json."""
    try:
        load_manifest(path)
    except (ManifestInvalid, OSError, json.JSONDecodeError) as exc:
        typer.echo(f"INVALID: {exc}", err=True)
        raise typer.Exit(code=1)
    typer.echo("OK: manifiesto válido")


@app.command()
def submit(
    path: Path = typer.Argument(..., help="Reporte JSON ya validado"),
    dir_: Path = typer.Option(Path("."), "--dir", help="Directorio donde buscar afp.json"),
    sink: str = typer.Option(None, "--sink", help="Sink solicitado (local/draft/github_issues)"),
):
    """Descubre el buzón de la tool y deposita el reporte respetando la política de routing."""
    data = json.loads(Path(path).read_text())
    try:
        validate_report(data)
    except (ReportInvalid, SecretDetected) as exc:
        typer.echo(f"INVALID: {exc}", err=True)
        raise typer.Exit(code=1)
    decision = discover(dir_)
    try:
        chosen = route(sink, decision, report=data, base_dir=dir_)
    except SinkNotAllowed as exc:
        typer.echo(f"ERROR: {exc}", err=True)
        raise typer.Exit(code=1)
    ref = deposit(chosen, data, base_dir=dir_)
    typer.echo(f"OK: depositado vía {chosen.name} -> {ref}")


@drafts_app.command("list")
def drafts_list(
    dir_: Path = typer.Option(Path("."), "--dir", help="Repo/directorio con .afp/drafts"),
):
    """Lista drafts locales AFP en formato escaneable."""
    drafts = _draft_paths(dir_)
    if not drafts:
        typer.echo("No hay drafts AFP.")
        return
    typer.echo("report_id\tseverity\tfriction_type\tfault_domain\tsubject_uri\tgoal")
    for draft in drafts:
        try:
            data = json.loads(draft.read_text(encoding="utf-8"))
            validate_report(data)
        except (OSError, json.JSONDecodeError, ReportInvalid, SecretDetected) as exc:
            typer.echo(f"{draft.name}\tINVALID\t{exc}")
            continue
        typer.echo(
            "\t".join([
                data.get("report_id", draft.stem),
                data.get("severity", ""),
                data.get("friction_type", ""),
                data.get("fault_domain", ""),
                data.get("subject_uri", ""),
                data.get("goal", ""),
            ])
        )


@drafts_app.command("show")
def drafts_show(
    ref: str = typer.Argument(..., help="report_id, stem o ruta del draft"),
    dir_: Path = typer.Option(
        Path("."), "--dir", help="Repo/directorio con .afp/drafts"
    ),
):
    """Muestra un draft local en Markdown legible."""
    try:
        path = _resolve_draft(ref, dir_=dir_)
        data = json.loads(path.read_text(encoding="utf-8"))
        validate_report(data)
    except (OSError, json.JSONDecodeError, ReportInvalid, SecretDetected) as exc:
        typer.echo(f"ERROR: {exc}", err=True)
        raise typer.Exit(code=1)
    typer.echo(_render_report_markdown(data))


@drafts_app.command("promote")
def drafts_promote(
    ref: str = typer.Argument(..., help="report_id, stem o ruta del draft"),
    dir_: Path = typer.Option(
        Path("."), "--dir", help="Repo/directorio con .afp/drafts"
    ),
    sink: str = typer.Option(..., "--sink", help="Sink explícito: local/draft/github_issues"),
):
    """Promueve un draft revisado a un sink explícito."""
    try:
        path = _resolve_draft(ref, dir_=dir_)
        data = json.loads(path.read_text(encoding="utf-8"))
        validate_report(data)
        sink_name, submit_ref = _submit_report(data, dir_=dir_, sink=sink)
    except (OSError, json.JSONDecodeError, ReportInvalid, SecretDetected, SinkNotAllowed) as exc:
        typer.echo(f"ERROR: {exc}", err=True)
        raise typer.Exit(code=1)
    typer.echo(f"OK: depositado vía {sink_name} -> {submit_ref}")


@app.command()
def dogfood(
    goal: str = typer.Option(..., "--goal", help="Qué intentabas lograr usando AFP"),
    expectation: str = typer.Option(..., "--expectation", help="Qué esperabas que hiciera AFP"),
    observed: str = typer.Option(..., "--observed", help="Qué ocurrió realmente"),
    friction_type: FrictionType = typer.Option(..., "--friction-type", help="Tipo de fricción AFP"),
    fault_domain: FaultDomain = typer.Option(..., "--fault-domain", help="Dominio probable de la causa"),
    severity: Severity = typer.Option(..., "--severity", help="Impacto de la fricción"),
    dir_: Path = typer.Option(Path("."), "--dir", help="Directorio donde buscar afp.json"),
    sink: str | None = typer.Option(None, "--sink", help="Sink solicitado (default: draft)"),
    plan_step: str | None = typer.Option(None, "--plan-step", help="Paso del plan donde falló"),
    workaround: str | None = typer.Option(None, "--workaround", help="Solución temporal encontrada"),
):
    """Genera y deposita un field report sobre AFP mismo para dogfooding."""
    report = FieldReport.create(
        subject_uri=f"pkg:github/Vasallo94/afp-protocol@{__version__}",
        goal=goal,
        expectation=expectation,
        observed=observed,
        friction_type=friction_type.value,
        fault_domain=fault_domain.value,
        severity=severity.value,
        plan_step=plan_step,
        workaround=workaround,
        harness="afp-cli",
        tool_call_name="afp dogfood",
    ).to_dict()
    try:
        validate_report(report)
        decision = discover(dir_)
        chosen = route(sink, decision, report=report, base_dir=dir_)
    except (ReportInvalid, SecretDetected, SinkNotAllowed) as exc:
        typer.echo(f"ERROR: {exc}", err=True)
        raise typer.Exit(code=1)
    ref = deposit(chosen, report, base_dir=dir_)
    typer.echo(f"OK: dogfood report depositado vía {chosen.name} -> {ref}")
