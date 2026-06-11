# AFP Integration Manager

**Documento de diseño** · v0.1 · 2026-06-11

## 1. Contexto

AFP ya tiene las piezas centrales para funcionar:

- CLI global (`afp`).
- Manifiesto de adopción por repo/tool (`afp.json`).
- Skill para Claude Code (`integrations/claude-code/afp-report/`).
- Rule para Cursor (`integrations/cursor/afp-report.mdc`).
- Bloque genérico para harnesses custom (`integrations/generic/AFP-INSTRUCTIONS.md`).

La fricción actual es de adopción: un usuario o agente tiene que saber dónde
están esas integraciones, cómo copiarlas o enlazarlas, y cómo verificar que el
entorno quedó listo. Eso hace que AFP dependa demasiado de memoria local o de
tener el repo clonado.

## 2. Objetivo

Convertir la adopción de AFP en comandos operativos, repetibles y
harness-agnostic:

```bash
afp integrations list
afp integrations install codex --global
afp integrations install claude-code --global
afp integrations install cursor --project .
afp init
afp doctor
```

El camino normal debe funcionar desde un `uv tool install` o una instalación
PyPI, sin clonar `afp-protocol`.

## 3. Principios

1. **Package-first.** Las integraciones se instalan desde recursos incluidos en
   el paquete Python. Un checkout local del repo no es requisito.
2. **Draft-first.** Las integraciones enseñan a los agentes a emitir drafts
   AFP. La promoción a sinks remotos sigue siendo humana.
3. **Idempotente y verificable.** Reinstalar una integración no debe duplicar
   archivos ni dejar estados ambiguos. `afp doctor` debe explicar qué falta.
4. **Global cuando es del harness, local cuando es del proyecto.** Codex y
   Claude Code son globales por usuario; Cursor suele vivir en `.cursor/rules/`
   del repo.
5. **Symlink solo para desarrollo.** En modo normal se copian archivos
   empaquetados. `--mode symlink` queda reservado para dogfooding desde un
   checkout local.

## 4. CLI propuesta

### `afp integrations list`

Muestra integraciones soportadas y su estado detectado.

```text
name          scope      status
codex         global     installed
claude-code   global     missing
cursor        project    missing
generic       prompt     available
```

### `afp integrations install <name>`

Instala una integración desde recursos empaquetados.

```bash
afp integrations install codex --global
afp integrations install claude-code --global
afp integrations install cursor --project .
```

Opciones:

- `--global`: instala en la ubicación de usuario del harness.
- `--project PATH`: instala en el repo/proyecto indicado.
- `--mode copy|symlink`: `copy` por defecto; `symlink` solo si el origen es un
  checkout local disponible.
- `--force`: sobrescribe una instalación previa tras crear `.bak`.

Destinos iniciales:

| Integración | Destino |
|-------------|---------|
| `codex` | `~/.codex/skills/afp-report/` |
| `claude-code` | `~/.claude/skills/afp-report/` |
| `cursor` | `<project>/.cursor/rules/afp-report.mdc` |
| `generic` | no instala por defecto; imprime el bloque o permite `--out PATH` |

### `afp init`

Genera un `afp.json` para el repo/tool actual.

MVP:

```bash
afp init --subject mcp://github.com/Vasallo94/nadir-astro \
  --sink github_issues \
  --repo Vasallo94/nadir-astro
```

Comportamiento:

- Escribe `afp.json` en el directorio actual.
- Valida el manifiesto antes de terminar.
- Si existe `afp.json`, aborta salvo `--force`.
- No infiere sinks remotos sin parámetros explícitos.

### `afp doctor`

Comprueba si AFP está listo para usarse en el entorno actual.

Checks iniciales:

- `afp` CLI disponible y versión.
- `afp.json` encontrado y válido en el repo actual.
- Codex skill instalada.
- Claude Code skill instalada.
- Cursor rule instalada si existe `.cursor/`.
- `gh auth status` si el manifiesto usa `github_issues`.
- `glab auth status` si el manifiesto usa `gitlab_issues`.
- Drafts pendientes en `.afp/drafts/`.

La salida debe ser accionable:

```text
OK      CLI: afp 0.2.0
OK      manifest: ./afp.json
MISSING codex skill: run afp integrations install codex --global
WARN    drafts: 2 pending, review with afp drafts list --dir .
```

## 5. Packaging

Las integraciones deben incluirse como package data:

```text
src/afp/integrations/
  codex/afp-report/SKILL.md
  claude-code/afp-report/SKILL.md
  cursor/afp-report.mdc
  generic/AFP-INSTRUCTIONS.md
```

El repo puede seguir manteniendo los archivos fuente en `integrations/`, pero
la build debe copiarlos o incluirlos en `src/afp/integrations/`. Los tests deben
garantizar que ambas copias no divergen, igual que ya ocurre con los schemas.

## 6. Flujo esperado

### Usuario de Codex

```bash
uv tool install git+https://github.com/Vasallo94/afp-protocol
afp integrations install codex --global
afp doctor
```

Después de reiniciar Codex, la skill `afp-report` queda disponible globalmente.

### Mantenedor de una tool

```bash
afp init --subject mcp://github.com/acme/weather-mcp \
  --sink github_issues \
  --repo acme/weather-mcp
git add afp.json
```

### Agente durante uso real

La integración del harness instruye al agente a generar siempre drafts:

```bash
afp report --from /tmp/afp-partial.json --submit --dir <tool-repo> --sink draft
```

El humano revisa y promueve cuando corresponda.

## 7. Errores y seguridad

- Si el destino existe y no coincide con la versión empaquetada, el instalador
  debe abortar con una instrucción clara. `--force` crea backup antes de
  sobrescribir.
- `afp init` no debe crear manifiestos remotos implícitos. Un sink remoto exige
  `--sink` y `--repo`/`--host` explícitos.
- `afp doctor` nunca debe imprimir tokens ni secretos de `gh`/`glab`; solo
  estado resumido.
- Las integraciones instaladas deben conservar la regla: agentes emiten drafts;
  humanos promueven.

## 8. Testing

Tests unitarios:

- `integrations list` devuelve las integraciones esperadas.
- `integrations install codex --global` copia la skill a un HOME temporal.
- `integrations install claude-code --global` copia la skill a un HOME temporal.
- `integrations install cursor --project <tmp>` crea `.cursor/rules/`.
- `--force` crea backup cuando sobrescribe.
- `--mode symlink` crea enlace solo con origen local disponible.
- `afp init` escribe y valida `afp.json`.
- `afp doctor` detecta manifest válido, skill instalada y drafts pendientes.

Tests de sync:

- Los recursos empaquetados coinciden con `integrations/`.
- El wheel/sdist incluye las integraciones.

## 9. Fuera de alcance

- Harvester automático.
- Promoción automática de drafts.
- Descubrimiento universal de subject_uri desde cualquier binario instalado.
- Instaladores para Cline, Aider u otros harnesses no cubiertos por el MVP.

## 10. Decisiones abiertas

Ninguna para el MVP. La decisión de packaging queda fijada: `copy` desde
recursos empaquetados es el modo normal; `symlink` existe solo para desarrollo.
