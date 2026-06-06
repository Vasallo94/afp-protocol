# AFP — Señal de revisión de drafts (diseño)

**Documento de diseño** · 2026-06-04 · resuelve issue [#4](https://github.com/Vasallo94/afp-protocol/issues/4)

## Contexto

Cuando un envío se deposita como `draft` (`afp report --submit`, `afp submit`,
`afp dogfood` con sink `draft` — el default sin manifiesto), AFP solo escribe el
`.json` en `.afp/drafts/` y muestra `OK: depositado vía draft -> draft:/ruta`. El
humano **no se entera** de que tiene drafts pendientes de revisar y promover a
issue. El field report #4 (dogfooding) lo registró como `missing_capability` /
`degraded`: falta una señal explícita de "revisa esto".

## Decisión

Al depositar un draft, el CLI emite —además del `OK:`— una **línea-notice** con
un prefijo estable que sirve a la vez para el humano y para un harness agéntico:

```
AFP-REVIEW: 2 drafts pendientes de revisión humana → afp drafts list --dir .
```

El prefijo `AFP-REVIEW:` es el **contrato documentado**: *al crear un draft, AFP
emite en stderr una línea que empieza por `AFP-REVIEW:`*. Un harness se configura
una vez ("si ves `AFP-REVIEW:`, muéstraselo al humano") y un humano la lee
directamente. No requiere modo máquina aparte ni cambios al protocolo.

## Detalles

- **Canal: `stderr`.** El `OK: ... -> draft:/ruta` permanece en stdout (no rompe
  pipes que capturan la ref); el notice va a stderr (convención de "atención
  requerida"). El harness ve ambos.
- **Cuándo:** solo cuando el sink resuelto es `draft`. No en `local` (spool) ni
  en sinks remotos. Cubre las 3 rutas que usa un agente: `report --submit`,
  `submit`, `dogfood`. **No** en `drafts promote` (ahí el humano ya revisa).
- **Orden:** solo después de un depósito exitoso. Si falla validación, routing o
  `deposit`, no se emite `AFP-REVIEW:`.
- **Qué dice:** cuenta el **total** de drafts pendientes en `.afp/drafts/` (no
  solo el recién creado) + el comando exacto de revisión (`afp drafts list
  --dir <dir>`).
- **Cómo cuenta:** cuenta paths `*.json` bajo `.afp/drafts/`; no parsea ni valida
  cada draft. Un draft inválido sigue siendo pendiente de atención humana.
- **`--dir`:** el comando usa el `dir_` recibido por el CLI renderizado como
  string (`str(Path(dir_))`). Si el usuario pasó `.` muestra `.`, si pasó una ruta
  absoluta muestra esa ruta.
- **Singular/plural:** "1 draft pendiente" vs "N drafts pendientes".
- **Contrato estable:** el contrato de integración es el prefijo
  `AFP-REVIEW:` en stderr. El texto posterior puede evolucionar, pero debe seguir
  incluyendo el conteo y el comando de revisión.

## Estructura del código

- `review_notice(dir_) -> str | None` — función pura: cuenta los `*.json` de
  `.afp/drafts/` y formatea el mensaje; `None` si no hay drafts. Testeable sin
  typer.
- `_announce_review(dir_)` — helper del CLI que hace `typer.echo(msg, err=True)`
  si `review_notice` devuelve algo. Lo llaman `report`, `submit` y `dogfood`
  cuando el sink depositado fue `draft`.
- **No enganchar en `_submit_report`:** `drafts promote` reutiliza ese helper y
  está explícitamente fuera de alcance. El aviso debe vivir en los comandos que
  crean drafts para que cada call-site decida si aplica.

## Tests

- `review_notice`: 0 drafts → `None`; 1 draft → wording singular; N → plural; el
  mensaje incluye el comando con el `--dir` correcto; drafts inválidos pero con
  extensión `.json` también cuentan.
- Integración CLI: `submit --sink draft`, `report --submit --sink draft` y
  `dogfood` emiten una línea `AFP-REVIEW:` en `result.stderr`; con un sink
  no-draft (p.ej. `local`) no la emite.
- Regresión de canal: los tests deben mirar `result.stderr` para el notice y
  `result.stdout` para el `OK:`. `result.output` mezcla ambos en `CliRunner` y no
  prueba el contrato de canal.

## Documentación

- Actualizar el README en la sección de drafts para mencionar que todo depósito a
  `draft` emite `AFP-REVIEW:` en stderr y que los harnesses pueden detectar ese
  prefijo para enseñar la revisión pendiente al humano.

## Fuera de alcance

- Modo `--json` / contrato máquina estructurado (se puede añadir encima después
  sin romper el prefijo).
- Hooks del harness o integración específica de Claude Code/Cursor.
- Cambios al spec normativo del protocolo (§4.2 ya cubre el draft como capa 2).
