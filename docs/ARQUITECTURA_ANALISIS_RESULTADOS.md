# Arquitectura de Análisis y Resultados
## Canvas como ancla — Navegación bidireccional — Coordinación visual

> **Documento de referencia técnica para las capas Análisis y Resultados del canvas premium.**
> Complementa el PRD v2.1 (secciones 7.3, 7.9, 7.10) y las reglas de CLAUDE.md sección 3.
> En caso de conflicto, el PRD v2.1 gana.

---

## 1. Distinción fundamental: capas de captura vs. capas de lectura

El canvas tiene 4 capas. No son simétricas.

| Capa | Naturaleza | El admin... |
|---|---|---|
| **Estructura** | Captura | Construye, edita, conecta nodos |
| **Recolección** | Captura | Gestiona invitaciones, monitorea estado |
| **Análisis** | Lectura densa | Comprende patrones, filtra por dimensión |
| **Resultados** | Lectura densa | Explora hallazgos, lee narrativa, actúa |

Las capas de lectura densa son fundamentalmente distintas en su naturaleza de interacción:
- No hay formularios de edición.
- El canvas no es decorativo: es el mapa de orientación que hace comprensible la información densa.
- Toda información está anclada a nodo(s) específicos de la organización.

---

## 2. Principio rector: el canvas como ancla

**Regla no negociable:** durante las capas Análisis y Resultados, el canvas nunca desaparece. Siempre está visible —al menos en segundo plano— y siempre es reactivo.

¿Qué significa "reactivo"?
- Cuando el usuario selecciona una dimensión en el panel → el canvas resalta los nodos más afectados por esa dimensión.
- Cuando el usuario hace clic en un hallazgo en la narrativa → el canvas resalta los nodos relevantes para ese hallazgo.
- Cuando el usuario hace clic en un nodo del canvas → el panel navega al análisis correspondiente a ese nodo.

El canvas es el **sistema de referencia compartido** entre el análisis cuantitativo, la narrativa cualitativa y la estructura real de la organización.

---

## 3. Capa Análisis — Especificación

### Objetivo
Comprensión rápida y situada del estado de la organización. El admin ve dónde hay tensión, en qué dimensiones, en qué nodos.

### Canvas
- Nodos coloreados por nivel de tensión agregado:
  - 🟢 Verde: score ≥ 3.8 en el promedio de dimensiones
  - 🟡 Amarillo: score entre 2.5 y 3.8
  - 🔴 Rojo: score < 2.5
- Intensidad del color proporcional a la desviación estándar (alta dispersión = borde más grueso).
- Filtro por dimensión: al activar una dimensión, los colores se actualizan para reflejar solo esa dimensión.
- Los nodos sin suficiente evidencia (menos de 1 respondente) se muestran en gris neutro con tooltip explicativo.

### Panel lateral (al hacer clic en un nodo)
- Score por dimensión para ese nodo (barra o radar mini).
- Comparación con el promedio de la organización ("Este nodo está 0.8 puntos por debajo del promedio en Comunicación").
- Resumen de percepciones agregadas: 2-3 frases extraídas/sintetizadas de las respuestas abiertas de ese nodo.
- Acceso rápido: "Ver hallazgos relacionados" → navega a Capa Resultados con ese nodo activo.

### Coordinación visual
- Al filtrar por dimensión (panel o selector superior) → canvas actualiza colores instantáneamente.
- Al hacer clic en score de una dimensión en el panel → canvas resalta los 3 nodos con mayor tensión en esa dimensión.
- Al cerrar el panel → canvas vuelve a vista general.

### Antipatrones en esta capa
- ❌ Mostrar gráficas sin contexto de qué nodo(s) representan.
- ❌ Filtros que desconecten la visualización del canvas.
- ❌ Panel con datos agregados de toda la org sin posibilidad de navegar a nodo.

---

## 4. Capa Resultados — Especificación

### Objetivo
Exploración de hallazgos y recomendaciones. El admin entiende qué está pasando, por qué, y qué puede hacer.

### Canvas
- Nodos con **badges de insights**: íconos pequeños que indican cuántos hallazgos están asociados a ese nodo.
- Nodos sin hallazgos: sin badge, opacidad ligeramente reducida.
- Al hacer clic en badge → panel lateral muestra hallazgos específicos del nodo.
- Clustering visual sugerido: nodos con hallazgos relacionados pueden mostrarse con borde compartido (opcional, Fase 5).

### Panel lateral (al hacer clic en un nodo)
- Lista de hallazgos asociados a ese nodo (con título, score de confianza, dimensión).
- Por hallazgo: descripción breve + "Ver en diagnóstico completo" → abre panel narrativo expandido en la sección correspondiente.
- Recomendaciones asociadas al nodo: prioridad, descripción corta.
- Navegación: "← Nodo anterior con hallazgos" / "Nodo siguiente con hallazgos →".

### Panel narrativo expandido
- Se abre al hacer clic en "Ver diagnóstico completo" o al seleccionar un hallazgo que requiere contexto amplio.
- Ocupa el **60–70% del viewport** (panel lateral derecho expandido).
- El canvas permanece visible en el 30–40% restante izquierdo.
- El canvas es reactivo mientras el panel está abierto: scroll en el panel hacia una dimensión → canvas resalta nodos de esa dimensión.
- Estructura del contenido:
  1. Resumen ejecutivo (1 párrafo, 3 hallazgos más relevantes)
  2. Análisis por dimensión (score, interpretación, evidencia, tensiones)
  3. Hallazgos transversales (patrones que cruzan múltiples dimensiones)
  4. Recomendaciones (priorizadas por impacto y viabilidad)
  5. Advertencias (tasa de respuesta, sesgos potenciales, áreas con evidencia insuficiente)
- Modo lectura ampliado: disponible para gráficas complejas (radar chart, comparativas). En modo ampliado, el canvas se oculta temporalmente. Un botón "Volver al canvas" siempre visible.
- Se cierra con: clic en área del canvas, botón de cierre, tecla Escape.

### Navegación bidireccional (obligatoria)
La navegación debe funcionar en ambas direcciones sin excepción:

**Canvas → Panel:**
- Clic en nodo → panel lateral con hallazgos del nodo.
- Clic en badge → panel lateral en la pestaña de hallazgos.

**Panel → Canvas:**
- Clic en hallazgo (en panel lateral o panel narrativo) → canvas resalta los nodos relevantes para ese hallazgo.
- Clic en dimensión (en panel narrativo) → canvas actualiza colores para mostrar esa dimensión.
- Hover sobre nombre de nodo en el panel → canvas hace un suave pulso/highlight del nodo correspondiente.

---

## 5. Coordinación visual canvas-narrativa: reglas de implementación

### Qué desencadena coordinación visual

| Acción del usuario | Respuesta del canvas |
|---|---|
| Clic en hallazgo (panel) | Resaltar nodos relevantes, atenuar el resto |
| Clic en dimensión (panel narrativo) | Actualizar colores a modo dimensión activa |
| Scroll en panel narrativo llega a sección de área X | Pulso suave en nodos del área X |
| Hover sobre nombre de nodo en panel | Highlight del nodo en canvas |
| Cerrar panel | Canvas vuelve a vista general |

### Cómo implementar el resaltado

```tsx
// Estado global del canvas para coordinación
interface CanvasHighlight {
  type: 'node' | 'dimension' | 'area' | null;
  ids: string[];  // node IDs o dimension names
}

// Al recibir highlight desde el panel:
// - Nodos en ids: opacity 1.0, borde accent
// - Nodos fuera de ids: opacity 0.3
// - Transición: 200ms ease
```

### Scroll observado en panel narrativo

Para sincronizar scroll del panel con el canvas, el panel narrativo usa `IntersectionObserver` sobre cada sección de dimensión/área. Cuando una sección entra al viewport → dispatch del evento de highlight correspondiente.

---

## 6. Antipatrones explícitos (todo el equipo)

Además de los antipatrones generales del PRD:
- ❌ **NO crear rutas /results, /analysis, /dashboard** — toda esta información vive como capas del canvas.
- ❌ **NO presentar reportes sin contexto estructural** — cualquier hallazgo o score debe tener al menos un nodo asociado.
- ❌ **NO separar narrativa y organización** — el panel narrativo siempre tiene el canvas visible detrás.
- ❌ **NO convertir el canvas en elemento decorativo** — si el canvas no reacciona al contenido del panel, algo está mal.
- ❌ **NO construir un "modo reporte" sin canvas** — si la información no cabe en el panel con canvas visible, usar modo lectura ampliado con botón de retorno, nunca una página separada.

**Toda información debe ser trazable a nodo(s) específicos.** Si un hallazgo no puede vincularse a ningún nodo, hay un problema en el pipeline de análisis, no una razón para mostrarlo fuera del canvas.

---

## 7. Criterio de validación de diseño (7.10)

Antes de implementar cualquier elemento de UI en las capas Análisis o Resultados:

> **¿Esta información se puede ubicar en la organización (asignar a nodo(s) específicos)?**
>
> - **Si sí** → conectar al canvas: resaltar el/los nodos relevantes cuando se visualiza esa información.
> - **Si no** → puede vivir fuera del canvas, pero debe incluir un mecanismo de retorno claro al contexto estructural.

Este criterio aplica a: hallazgos, recomendaciones, scores por dimensión, gráficas comparativas y cualquier dato derivado del análisis.

El objetivo es que el usuario nunca pierda la conexión entre la información y la organización real que está diagnosticando.

---

## 8. Estados de la UI por capa (resumen técnico)

```
CAPA ANÁLISIS
├── Canvas: nodos coloreados por tensión (verde/amarillo/rojo)
├── Selector de dimensión: en LayerSelector o toolbar superior
├── Panel lateral (sin nodo seleccionado): vacío o instrucción contextual
└── Panel lateral (nodo seleccionado):
    ├── scores por dimensión del nodo
    ├── comparación con promedio org
    └── resumen de percepciones

CAPA RESULTADOS
├── Canvas: nodos con badges de insights
├── Panel lateral (sin nodo seleccionado): vacío
├── Panel lateral (nodo seleccionado):
│   ├── lista de hallazgos del nodo
│   └── recomendaciones asociadas
└── Panel narrativo expandido (trigger: "Ver diagnóstico completo"):
    ├── canvas visible en 30-40% izquierdo
    ├── panel en 60-70% derecho
    ├── coordinación visual activa (scroll → canvas)
    └── modo lectura ampliado disponible para gráficas
```

---

*Actualizado: Abril 2026 | Versión: 1.0*
*Referencia: PRD v2.1 secciones 7.3, 7.9, 7.10 | CLAUDE.md sección 3*
