# ADR-0001: Política de extensibilidad del schema y versionado del protocolo

**Status:** Accepted
**Date:** 2026-06-04
**Deciders:** mantenedor de afp-protocol (@Vasallo94)
**Relacionado:** evaluación de arquitectura [`docs/reviews/2026-06-04-architecture-evaluation.md`](../reviews/2026-06-04-architecture-evaluation.md) (hallazgos #1 y #8) · issue [#7](https://github.com/Vasallo94/afp-protocol/issues/7)

## Context

AFP se posiciona como un **protocolo** ("mil navegadores distintos hablan HTTP"):
distintos agentes, en harness distintos y versiones distintas, deben poder producir y
consumir field reports sin coordinarse. Esa interoperabilidad depende de cómo se traten
los **campos desconocidos** y las **versiones de schema**.

La implementación de Fase 1a era **estricta en dos capas**:

1. `field_report.schema.json` tenía `additionalProperties: false` → cualquier campo no
   declarado invalidaba el reporte.
2. `FieldReport.from_dict` hacía `cls(**data)` → un campo extra lanzaba `TypeError`.
3. `schema_version` era `"const": "afp/0.2"` → solo esa versión exacta validaba.

**Fuerza en juego:** un reporte `afp/0.3` con una extensión nueva fallaba contra una
librería `afp/0.2`. Un Harvester escrito contra esta lib **rechazaría reportes de agentes
más nuevos** — justo el escenario que un protocolo debe soportar. La política de
campos-desconocidos y la de versionado son, en la práctica, **la misma decisión**.

## Decision

Adoptar un modelo **tolerante / forward-compatible** (opción A):

- **Campos desconocidos se preservan, no se descartan ni rompen.** El schema del field
  report pasa a `additionalProperties: true`; `FieldReport` captura los campos no
  declarados en `extra` y los re-emite intactos en `to_dict()` (round-trip íntegro).
- **Versionado semántico con compatibilidad por *major* y tolerancia por *minor*.**
  `schema_version` valida contra `^afp/0\.\d+$`: esta librería (major 0) acepta cualquier
  *minor* (`afp/0.2`, `afp/0.99`…) y rechaza un *major* distinto (`afp/1.0`). Cuando el
  major cambie, se actualiza el schema y se documenta la migración.

Regla operativa (camino a RFC 2119 en Fase 1.5):
- Un cambio **aditivo** (campo opcional nuevo) → bump de **minor**. Los consumidores
  antiguos lo preservan sin entenderlo; los nuevos lo aprovechan.
- Un cambio **incompatible** (renombrar/eliminar campo core, cambiar semántica) → bump de
  **major**. Rompe compat a propósito y exige migración.

## Options Considered

### Opción A: Tolerante (preservar) — ELEGIDA

| Dimensión | Evaluación |
|-----------|------------|
| Complejidad | Baja (un campo `extra` + relajar schema) |
| Interoperabilidad | **Alta** — productor/consumidor evolucionan a ritmos distintos |
| Riesgo de pérdida de datos | Ninguno (se preservan) |
| Familiaridad | Patrón estándar: HTTP, protobuf, OpenTelemetry |

**Pros:** coherente con vender AFP como protocolo; un `afp/0.3` funciona contra una lib
`0.2`; sin pérdida de información; cambio mínimo.
**Cons:** un consumidor antiguo no *entiende* los campos nuevos (sí los conserva); acepta
campos basura sin avisar (mitigado: siguen pasando por el hard-block de secretos §5).

### Opción B: Warn & drop

| Dimensión | Evaluación |
|-----------|------------|
| Complejidad | Media (logging + descarte) |
| Interoperabilidad | Media |
| Riesgo de pérdida de datos | **Alto** (descarta extensiones) |

**Pros:** seguro, simple, nunca aborta.
**Cons:** **lossy** — un Harvester viejo tira en silencio (tras warning) las extensiones
nuevas; el dato muere en el primer salto entre versiones.

### Opción C: Estricto + bump de major

| Dimensión | Evaluación |
|-----------|------------|
| Complejidad | Baja |
| Interoperabilidad | **Baja** |
| Control | Alto y explícito |

**Pros:** control total; nada entra sin estar declarado.
**Cons:** rígido; rompe interoperabilidad entre versiones cercanas — el escenario que el
protocolo debería soportar. Obliga a coordinar despliegues de productor y consumidor.

## Trade-off Analysis

El eje decisivo es **interoperabilidad vs. control**. Para un *formato de aplicación
interna* C sería razonable. Para un *protocolo descentralizado* —donde no controlas quién
produce ni con qué versión— la tolerancia de A es la que hace que el ecosistema funcione,
exactamente como HTTP ignora cabeceras que no entiende en vez de rechazar la petición. B
conserva la seguridad de A pero sacrifica el dato, que es justamente "el centro del
protocolo" según el principio rector del spec. Por eso A.

## Consequences

- **Más fácil:** evolucionar el schema de forma aditiva sin coordinar versiones; que
  Harvesters y agentes de distinta edad interoperen.
- **Más difícil / a vigilar:** un typo en un nombre de campo ya no se detecta por schema
  (pasa como extensión silenciosa). Mitigación parcial: el detector de secretos sigue
  recorriendo *todos* los strings, incluidos los de `extra`.
- **A revisitar:** cuando se redacte la spec normativa (Fase 1.5, RFC 2119 + test
  vectors), formalizar esta regla de major/minor y añadir vectores de compat. El manifiesto
  (`afp.json`) sigue siendo **estricto** a propósito (`additionalProperties: false`): es
  configuración del dueño, no dato en tránsito entre versiones — endurecer el objeto `sink`
  queda en el backlog (§10b del spec).

## Action Items

1. [x] `additionalProperties: true` en `field_report.schema.json`.
2. [x] `schema_version` → patrón `^afp/0\.\d+$` (compat por major, tolerancia por minor).
3. [x] `FieldReport` preserva campos desconocidos en `extra` con round-trip íntegro.
4. [x] Tests: preservación de extensión, aceptación de campo extra, minor nuevo aceptado,
   major distinto rechazado.
5. [ ] Fase 1.5: formalizar la regla en la spec normativa (RFC 2119) + test vectors de
   compatibilidad entre versiones.
