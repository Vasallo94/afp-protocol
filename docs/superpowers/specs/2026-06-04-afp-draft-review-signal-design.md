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
- **Qué dice:** cuenta el **total** de drafts pendientes en `.afp/drafts/` (no
  solo el recién creado) + el comando exacto de revisión (`afp drafts list
  --dir <dir>`).
- **Singular/plural:** "1 draft pendiente" vs "N drafts pendientes".

## Estructura del código

- `review_notice(dir_) -> str | None` — función pura: cuenta los `*.json` de
  `.afp/drafts/` y formatea el mensaje; `None` si no hay drafts. Testeable sin
  typer.
- `_announce_review(dir_)` — helper del CLI que hace `typer.echo(msg, err=True)`
  si `review_notice` devuelve algo. Lo llaman `report`, `submit` y `dogfood`
  cuando el sink depositado fue `draft`.

## Tests

- `review_notice`: 0 drafts → `None`; 1 draft → wording singular; N → plural; el
  mensaje incluye el comando con el `--dir` correcto.
- Integración CLI: `dogfood --sink draft` emite una línea `AFP-REVIEW:` en
  stderr; con un sink no-draft (p.ej. `local`) no la emite.

## Fuera de alcance

- Modo `--json` / contrato máquina estructurado (se puede añadir encima después
  sin romper el prefijo).
- Hooks del harness o integración específica de Claude Code/Cursor.
- Cambios al spec normativo del protocolo (§4.2 ya cubre el draft como capa 2).
