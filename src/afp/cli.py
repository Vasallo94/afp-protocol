import json
from pathlib import Path

import typer

from afp import __version__
from afp.discovery import discover
from afp.manifest import ManifestInvalid, load_manifest
from afp.models import FieldReport
from afp.redact import SecretDetected
from afp.sinks import SinkNotAllowed, route
from afp.validate import ReportInvalid, validate_report

app = typer.Typer(help="AFP — Agent Feedback Protocol CLI")


@app.command()
def report(
    from_: Path = typer.Option(..., "--from", help="JSON parcial con los campos del reporte"),
    out: Path = typer.Option(None, "--out", help="Dónde escribir el reporte completo"),
):
    """Construye un field report completo (añade id/timestamp/schema_version) y lo valida."""
    partial = json.loads(Path(from_).read_text())
    if "report_id" in partial:
        fr = FieldReport.from_dict(partial)
    else:
        fr = FieldReport.create(**partial)
    data = fr.to_dict()
    try:
        validate_report(data)
    except (ReportInvalid, SecretDetected) as exc:
        typer.echo(f"ERROR: {exc}", err=True)
        raise typer.Exit(code=1)
    text = json.dumps(data, ensure_ascii=False, indent=2)
    if out:
        Path(out).write_text(text, encoding="utf-8")
        typer.echo(f"OK: reporte escrito en {out}")
    else:
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
    ref = chosen.submit(data)
    typer.echo(f"OK: depositado vía {chosen.name} -> {ref}")


@app.command()
def dogfood(
    goal: str = typer.Option(..., "--goal", help="Qué intentabas lograr usando AFP"),
    expectation: str = typer.Option(..., "--expectation", help="Qué esperabas que hiciera AFP"),
    observed: str = typer.Option(..., "--observed", help="Qué ocurrió realmente"),
    friction_type: str = typer.Option(..., "--friction-type", help="Tipo de fricción AFP"),
    fault_domain: str = typer.Option(..., "--fault-domain", help="Dominio probable de la causa"),
    severity: str = typer.Option(..., "--severity", help="Impacto de la fricción"),
    dir_: Path = typer.Option(Path("."), "--dir", help="Directorio donde buscar afp.json"),
    sink: str | None = typer.Option(None, "--sink", help="Sink solicitado (default: draft)"),
    plan_step: str | None = typer.Option(None, "--plan-step", help="Paso del plan donde falló"),
    workaround: str | None = typer.Option(None, "--workaround", help="Solución temporal encontrada"),
):
    """Genera y deposita un field report sobre AFP mismo para dogfooding."""
    report = FieldReport.create(
        subject_uri=f"pkg:pypi/afp@{__version__}",
        goal=goal,
        expectation=expectation,
        observed=observed,
        friction_type=friction_type,
        fault_domain=fault_domain,
        severity=severity,
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
    ref = chosen.submit(report)
    typer.echo(f"OK: dogfood report depositado vía {chosen.name} -> {ref}")
