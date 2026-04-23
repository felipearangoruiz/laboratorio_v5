# Motor de Análisis — Contrato Técnico

> Fuente de verdad del pipeline de IA.
> Complementa el PRD v2.1 y CLAUDE.md sección 12.
> En caso de conflicto, este documento gana para decisiones de implementación del motor.

> **Nota sobre el término "node":** en este documento "node" se refiere conceptualmente a un respondiente individual (en el modelo actual: un `Node` con `type = "person"`). Desde Sprint 3 (migración `20260423_0012`) las tablas `node_analyses` y `group_analyses` usan la columna `node_id UUID FK nodes.id`, distinguiendo semánticamente qué tipo de nodo referencia cada una:
>
> - `node_analyses.node_id` → `nodes` con `type = 'person'` (respondiente, Paso 1 del pipeline).
> - `group_analyses.node_id` → `nodes` con `type = 'unit'` (grupo/área, Paso 2 del pipeline).
>
> Los UUIDs fueron preservados en la migración Sprint 1.2 (`Group.id → Node.id`, `Member.id → Node.id`), así que los análisis históricos siguen resolviéndose sin pérdida. Ver `docs/MODEL_PHILOSOPHY.md` §3 para la resolución completa de la ambigüedad de nomenclatura.

---

## 1. Pipeline

El motor **nunca envía datos crudos al LLM**. Siempre construye representaciones intermedias primero.

> **Encadenamiento entre pasos (Sprint 4.A — 2026-04-23).** Cada paso devuelve dos cosas: (a) el id persistido en BD y (b) el dict completo que produjo el LLM. El dict completo se acumula en memoria local del script (`state["node_analyses_full"]`, `state["group_analyses_full"]`, `state["org_analysis_full"]`) y se inyecta íntegro en el prompt del siguiente paso. Antes del Sprint 4.A el script solo propagaba los IDs, lo que dejaba al Paso 4 operando sobre un resumen filtrado del Paso 3 — los hallazgos resultantes no podían referenciar `key_quotes`, `signals_tension` o `patterns_internal` porque nunca llegaban al prompt. Los state files generados antes de 4.A no son retrocompatibles; un run interrumpido bajo el formato viejo debe reiniciarse desde cero.

### PASO 1 — Extracción por nodo (un prompt por persona/nodo)

**Input:**
- Respuestas cuantitativas (Likert por dimensión)
- Texto libre de respuestas abiertas
- Rol y nivel jerárquico del nodo
- `context_notes` del admin sobre ese nodo
- Documentos del nodo, si los hay

**Output:** `node_analysis` — objeto estructurado, **NO narrativa**

**Guardado en:** tabla `node_analyses`

---

### PASO 2 — Síntesis por grupo (un prompt por grupo)

**Input:**
- Todos los `node_analyses` del grupo
- Scores cuantitativos del grupo (con desviación estándar)
- Notas del admin sobre el grupo
- Documentos del grupo

**Output:** `group_analysis` con patrones internos identificados (convergencias y divergencias)

**Guardado en:** tabla `group_analyses`

---

### PASO 3 — Análisis organizacional (un prompt)

**Input:**
- Todos los `group_analyses`
- Estructura del organigrama (snapshot del grafo)
- Métricas de red (centralidad, nodos puente, nodos aislados)
- Documentos institucionales ya procesados (`document_extractions`)

**Output:** `org_analysis` con patrones transversales y contradicciones

**Guardado en:** tabla `org_analyses`

---

### PASO 4 — Síntesis ejecutiva (un prompt)

**Input:** Outputs de pasos 2 y 3 — **ya estructurados, NUNCA datos crudos**

**Output:** `findings` + `recommendations` + `narrative_md`

**Regla no negociable:** el LLM NO puede introducir hallazgos que no estén fundamentados en los pasos anteriores. Todo hallazgo debe tener `evidence_links` trazables a `node_analyses` o `group_analyses`.

---

## 2. Schema de tablas

### analysis_runs

| Campo | Tipo | Descripción |
|---|---|---|
| id | UUID PK | |
| org_id | UUID FK organizations | |
| status | VARCHAR | `'pending'`\|`'running'`\|`'completed'`\|`'failed'` |
| started_at | TIMESTAMP | |
| completed_at | TIMESTAMP nullable | |
| model_used | VARCHAR | |
| total_nodes | INT | |
| total_groups | INT | |
| error_message | TEXT nullable | |

---

### node_analyses

| Campo | Tipo | Descripción |
|---|---|---|
| id | UUID PK | |
| run_id | UUID FK analysis_runs | |
| org_id | UUID FK organizations | |
| node_id | UUID FK nodes | Respondiente (`nodes.type = 'person'`). Renombrada desde `group_id` en Sprint 3. |
| signals_positive | JSONB | Lista de strings |
| signals_tension | JSONB | Lista de strings |
| themes | JSONB | Lista de strings |
| dimensions_touched | JSONB | Lista de dimension names |
| evidence_type | VARCHAR | `'observacion'`\|`'juicio'`\|`'hipotesis'` |
| emotional_intensity | VARCHAR | `'baja'`\|`'media'`\|`'alta'` |
| key_quotes | JSONB | Lista de strings, anonimizados |
| context_notes_used | BOOLEAN | |
| confidence | FLOAT | 0.0 a 1.0 |
| created_at | TIMESTAMP | |

---

### group_analyses

| Campo | Tipo | Descripción |
|---|---|---|
| id | UUID PK | |
| run_id | UUID FK analysis_runs | |
| org_id | UUID FK organizations | |
| node_id | UUID FK nodes | Grupo/área (`nodes.type = 'unit'`). Renombrada desde `group_id` en Sprint 3. |
| patterns_internal | JSONB | Convergencias y divergencias dentro del grupo |
| dominant_themes | JSONB | Lista de strings |
| tension_level | VARCHAR | `'bajo'`\|`'medio'`\|`'alto'`\|`'critico'` |
| scores_by_dimension | JSONB | `{dimension: score}` |
| gap_leader_team | FLOAT nullable | Solo si hay nodo líder identificado |
| coverage | FLOAT | % de nodos del grupo con entrevista completada |
| confidence | FLOAT | |
| created_at | TIMESTAMP | |

---

### org_analyses

| Campo | Tipo | Descripción |
|---|---|---|
| id | UUID PK | |
| run_id | UUID FK analysis_runs | |
| org_id | UUID FK organizations | |
| cross_patterns | JSONB | Patrones que aparecen en múltiples grupos |
| contradictions | JSONB | Discurso formal vs. práctica reportada |
| structural_risks | JSONB | Basado en métricas de red + percepciones |
| dimension_scores | JSONB | `{dimension: {score, std, gap_leader_team}}` |
| network_metrics | JSONB | `{centrality, bridge_nodes, isolated_nodes}` |
| confidence | FLOAT | |
| created_at | TIMESTAMP | |

---

### document_extractions

| Campo | Tipo | Descripción |
|---|---|---|
| id | UUID PK | |
| run_id | UUID FK analysis_runs | |
| org_id | UUID FK organizations | |
| doc_id | UUID FK documents | |
| doc_type | VARCHAR | `'financial'`\|`'strategic'`\|`'operational'`\|`'hr'`\|`'other'` |
| extracted_structure | JSONB | Varía por doc_type |
| key_indicators | JSONB | |
| implicit_signals | JSONB | |
| injected_at_step | INT | 1, 2 o 3 |
| created_at | TIMESTAMP | |

---

### findings

| Campo | Tipo | Descripción |
|---|---|---|
| id | UUID PK | |
| run_id | UUID FK analysis_runs | |
| org_id | UUID FK organizations | |
| title | VARCHAR | |
| description | TEXT | |
| type | VARCHAR | `'observacion'`\|`'patron'`\|`'inferencia'`\|`'hipotesis'` |
| severity | VARCHAR | `'baja'`\|`'media'`\|`'alta'`\|`'critica'` |
| dimensions | JSONB | Lista de dimension names |
| node_ids | JSONB | Lista de `nodes.id` UUIDs afectados (units o persons según el hallazgo). UUIDs preservados desde Sprint 1.2 — siempre resolvieron contra `nodes`, la aclaración es post-Sprint 3. |
| confidence | FLOAT | |
| confidence_rationale | TEXT | |
| created_at | TIMESTAMP | |

---

### recommendations

| Campo | Tipo | Descripción |
|---|---|---|
| id | UUID PK | |
| run_id | UUID FK analysis_runs | |
| org_id | UUID FK organizations | |
| finding_id | UUID FK findings nullable | |
| title | VARCHAR | |
| description | TEXT | |
| priority | INT | 1 = más urgente |
| impact | VARCHAR | `'bajo'`\|`'medio'`\|`'alto'` |
| effort | VARCHAR | `'bajo'`\|`'medio'`\|`'alto'` |
| horizon | VARCHAR | `'inmediato'`\|`'corto'`\|`'mediano'`\|`'largo'` |
| node_ids | JSONB | Lista de `nodes.id` UUIDs afectados por la recomendación (ver nota en `findings.node_ids`). |
| created_at | TIMESTAMP | |

---

### evidence_links

| Campo | Tipo | Descripción |
|---|---|---|
| id | UUID PK | |
| finding_id | UUID FK findings | |
| node_analysis_id | UUID FK node_analyses nullable | |
| group_analysis_id | UUID FK group_analyses nullable | |
| quote | TEXT nullable | Cita específica que soporta el hallazgo |
| evidence_type | VARCHAR | `'quantitative'`\|`'qualitative'`\|`'documentary'` |

---

## 3. Contratos de prompts

### Prompt Paso 1 — Extracción por nodo

**Modelo:** `gpt-4o-mini` (barato, estructurado)

**Input JSON:**
```json
{
  "node_role": "string",
  "node_level": "int",
  "context_notes": "string|null",
  "quantitative_responses": {"dimension": "score"},
  "open_responses": ["string"],
  "documents": [{"type": "string", "key_content": "string"}]
}
```

**Output JSON esperado:**
```json
{
  "signals_positive": ["string"],
  "signals_tension": ["string"],
  "themes": ["string"],
  "dimensions_touched": ["string"],
  "evidence_type": "observacion|juicio|hipotesis",
  "emotional_intensity": "baja|media|alta",
  "key_quotes": ["string"],
  "confidence": "float"
}
```

---

### Prompt Paso 2 — Síntesis por grupo

**Modelo:** `gpt-4o-mini`

**Input JSON:**
```json
{
  "group_name": "string",
  "group_area": "string",
  "node_analyses": ["NodeAnalysis"],
  "quantitative_scores": {"dimension": {"score": 0, "std": 0}},
  "admin_notes": "string|null",
  "coverage": "float"
}
```

**Output JSON esperado:**
```json
{
  "patterns_internal": [{"pattern": "string", "frequency": "int"}],
  "dominant_themes": ["string"],
  "tension_level": "bajo|medio|alto|critico",
  "scores_by_dimension": {"dimension": "float"},
  "gap_leader_team": "float|null",
  "confidence": "float"
}
```

---

### Prompt Paso 3 — Análisis organizacional

**Modelo:** `gpt-4o`

**Input JSON:**
```json
{
  "org_name": "string",
  "org_structure_type": "string",
  "group_analyses": ["GroupAnalysis"],
  "dimension_scores": {"dimension": {"score": 0, "std": 0}},
  "network_metrics": {"centrality": {}, "bridge_nodes": [], "isolated_nodes": []},
  "document_extractions": ["DocumentExtraction"],
  "structure_snapshot": "OrgGraph"
}
```

**Output JSON esperado:**
```json
{
  "cross_patterns": [{"pattern": "string", "groups_affected": ["id"]}],
  "contradictions": [{"formal": "string", "real": "string", "evidence": "string"}],
  "structural_risks": [{"risk": "string", "nodes": ["id"], "severity": "string"}],
  "confidence": "float"
}
```

---

### Prompt Paso 4 — Síntesis ejecutiva

**Modelo:** `gpt-4o`

**Regla:** SOLO puede referenciar hallazgos de pasos anteriores. NO puede introducir información nueva.

**Input JSON:**
```json
{
  "org_analysis": "OrgAnalysis",
  "group_analyses": ["GroupAnalysis"],
  "top_patterns": ["string"],
  "top_contradictions": ["string"],
  "structural_risks": ["string"]
}
```

**Output JSON esperado:**
```json
{
  "findings": ["Finding"],
  "recommendations": ["Recommendation"],
  "narrative_md": "string",
  "executive_summary": "string"
}
```

---

## 4. Reglas de confianza

La confianza **NO la inventa el LLM**. El sistema la calcula así:

```
Base:                                        0.50
+ si el patrón aparece en más de un grupo:  +0.20
+ si hay convergencia cuanti + cuali:        +0.10
+ si coverage > 70%:                         +0.10
- si coverage < 40%:                         -0.20
- si alta dispersión (std > 1.5):            -0.10
- si solo un nodo lo reporta:               -0.20
────────────────────────────────────────────
Máximo: 0.95   Mínimo: 0.10
```

El campo `confidence_rationale` en `findings` debe documentar qué factores se aplicaron.

---

## 5. Timing de ejecución

| Paso | Cuándo se ejecuta |
|---|---|
| Scoring cuantitativo | En tiempo real cuando llegan respuestas |
| Paso 1 — node_analyses | On-demand al iniciar una corrida (`analysis_run`) |
| Paso 2 — group_analyses | Secuencialmente después del Paso 1 |
| Paso 3 — org_analyses | Secuencialmente después del Paso 2 |
| Paso 4 — findings + narrative | Secuencialmente después del Paso 3 |
| Documentos | Procesados en background al subirse; resultados guardados en `document_extractions` |

El estado de la corrida se persiste en `analysis_runs.status` para permitir reinicios parciales en caso de fallo.

---

## 6. Datos mock para testing

*Ver sección 7 — se genera con script separado.*

Script de referencia: `backend/scripts/generate_mock_analysis.py` (por crear).

El mock debe cubrir:
- Org con 3 grupos (≥2 nodos cada uno)
- Cobertura del 60% (algunos nodos sin entrevista)
- Al menos 1 contradicción entre grupos
- Al menos 1 hallazgo de tipo `'hipotesis'` con confidence < 0.4
- Al menos 1 recomendación con `horizon = 'inmediato'`

---

## 7. Criterio de calidad

El motor es correcto si puede responder **sin recalcular todo desde cero**:

1. ¿Dónde están las principales tensiones de coordinación?
2. ¿Qué grupos tienen más desalineación entre liderazgo y base?
3. ¿Qué hallazgos tienen baja confianza por cobertura insuficiente?
4. ¿Qué tres temas afectan más de una dimensión a la vez?

Si responder cualquiera de estas preguntas requiere re-ejecutar el pipeline completo, hay un problema de diseño en el schema de tablas intermedias.

---

## Registro de cambios

- **2026-04-23 — Sprint 4.B Ronda 1 (fundamentación).** Tres intervenciones anti-alucinación sin tocar modelos ni Paso 4:
  - **Grupos `size=1`:** el Paso 2 inyecta al prompt el `size` del grupo. Si `size == 1`, `patterns_internal=[]` por construcción (defensa en profundidad: el código lo fuerza además del prompt). Elimina la ilusión de "patrones" con `frequency=1` que eran copy-paste del único respondente.
  - **Paso 3 anti-alucinación:** tres reglas nuevas en `paso3_org.txt`: (A) toda afirmación numérica cita el valor exacto del input (no más "baja cobertura" cuando `coverage=1.0`); (B) los `cross_patterns` requieren evidencia en ≥2 grupos con al menos uno de `size≥2`; (C) grupos `size=1` son voz individual, no patrón grupal.
  - **Fix `_compute_confidence`:** el flag `has_quanti_quali_convergence` era `bool(f.get("dimensions"))` — siempre True. Ahora compara las `dimensions` del finding contra `dimension_scores` agregados del org_analysis (score<0.50 o std>0.25 → convergencia legítima).
- **2026-04-23 — Sprint 4.A.** Encadenamiento corregido: cada paso propaga el dict completo del LLM al siguiente, no solo su id. State file gana tres claves nuevas (`node_analyses_full`, `group_analyses_full`, `org_analysis_full`) y rompe retrocompatibilidad con state files anteriores. Payload de POST al backend en Pasos 1 y 2 pasa a usar `node_id` (antes enviaba el obsoleto `group_id`, deuda Sprint 3).
- **2026-04-22 — Sprint 3.** Rename `group_id` → `node_id` en tablas `node_analyses` y `group_analyses` (migración `20260423_0012`). FK ahora apunta a `nodes(id)`.

---

*Actualizado: Abril 2026 | Versión: 1.0*
*Referencia: PRD v2.1 | CLAUDE.md sección 12 | ARQUITECTURA_ANALISIS_RESULTADOS.md*
