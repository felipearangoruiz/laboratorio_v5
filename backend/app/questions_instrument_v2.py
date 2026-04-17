"""
Instrumento v2 — Diagnóstico organizacional adaptativo.

Arquitectura de 3 capas por pregunta:
  CAPA BASE: señal categórica (selección / multi-select)
  CAPA GRADIENTE: frecuencia × impacto (aparece condicionalmente)
  CAPA NUMÉRICA: magnitud concreta (aparece condicionalmente)

Flujo adaptativo:
  1. Gerente responde 13 preguntas base + capas
  2. Sistema analiza respuestas del gerente → genera hipótesis
  3. Empleados responden 10 preguntas base + 3 adaptativas seleccionadas
  4. IA cruza todas las respuestas → dashboard cuantificado
"""

# ══════════════════════════════════════════════════════════════════════════════
# DIMENSIONES v2
# ══════════════════════════════════════════════════════════════════════════════

DIMENSIONS_V2 = {
    "centralizacion": "Centralización",
    "cuellos_botella": "Cuellos de botella",
    "flujo_informacion": "Flujo de información",
    "incentivos": "Incentivos y colaboración",
    "cultura_error": "Cultura de error",
    "alineacion_estrategica": "Alineación estratégica",
    "capacidad_cambio": "Capacidad de cambio",
    "visibilidad_financiera": "Visibilidad financiera",
}

# ══════════════════════════════════════════════════════════════════════════════
# PREGUNTAS DEL GERENTE (13)
# ══════════════════════════════════════════════════════════════════════════════

MANAGER_QUESTIONS: list[dict] = [
    # ── G1 — Distribución de tu tiempo ────────────────────────────────────
    {
        "id": "G1",
        "title": "Distribución de tu tiempo",
        "dimension": "centralizacion",
        "base": {
            "text": "¿Cuánto de tu tiempo en la semana se te va en resolver cosas del día a día que en teoría alguien más podría resolver?",
            "type": "single_select",
            "options": [
                "Casi nada",
                "Menos de la mitad",
                "Más o menos la mitad",
                "La mayor parte",
                "Prácticamente todo",
            ],
        },
        "layers": [
            {
                "id": "G1_L1",
                "type": "numeric_select",
                "condition": {"base_answer_index_gte": 2},
                "text": "¿Cuántas horas a la semana dirías que dedicas a cosas que alguien más podría resolver?",
                "options": ["Menos de 5", "5–10", "10–20", "20–30", "Más de 30"],
            },
        ],
        "output_template": "Dedica ~{hours} horas/semana a tareas delegables. Eso es {pct}% de una semana laboral de 45 horas.",
    },
    # ── G2 — Prueba de ausencia ───────────────────────────────────────────
    {
        "id": "G2",
        "title": "Prueba de ausencia",
        "dimension": "centralizacion",
        "base": {
            "text": "Si te fueras de vacaciones una semana sin poder contestar el teléfono, ¿qué pasaría con la operación?",
            "type": "single_select",
            "options": [
                "Todo seguiría funcionando normal",
                "Algunas cosas se retrasarían",
                "Varias decisiones quedarían en pausa",
                "Se frenaría significativamente",
                "No me puedo ir una semana",
            ],
        },
        "layers": [
            {
                "id": "G2_L1",
                "type": "text_short",
                "condition": {"base_answer_index_gte": 2},
                "text": "¿Cuál sería la primera cosa que se detendría?",
            },
        ],
    },
    # ── G3 — Autonomía del equipo ─────────────────────────────────────────
    {
        "id": "G3",
        "title": "Autonomía del equipo",
        "dimension": "centralizacion",
        "base": {
            "text": "¿Cuáles de estas decisiones puede tomar tu equipo SIN consultarte?",
            "type": "multi_select",
            "options": [
                "Ofrecer descuentos",
                "Resolver quejas de clientes",
                "Compras menores",
                "Cambiar un proceso",
                "Contratar ayuda temporal",
                "Negociar con proveedor",
                "Ninguna",
            ],
        },
        "layers": [
            {
                "id": "G3_L1",
                "type": "ranking_from_unselected",
                "condition": {"always": True},
                "text": "De las que SÍ requieren tu aprobación, ¿cuál es la que más tiempo o energía te consume?",
            },
        ],
    },
    # ── G4 — Cuellos de botella ───────────────────────────────────────────
    {
        "id": "G4",
        "title": "Cuellos de botella",
        "dimension": "cuellos_botella",
        "base": {
            "text": "¿Dónde se traban las cosas más seguido en tu negocio?",
            "type": "multi_select",
            "options": [
                "Aprobaciones que dependen de mí",
                "Coordinación entre áreas o sedes",
                "Falta de información",
                "Falta de herramientas",
                "Errores y retrabajo",
                "Proveedores",
                "Falta de personal",
                "No se traban",
            ],
        },
        "layers": [
            {
                "id": "G4_L1",
                "type": "gradient_per_selection",
                "condition": {"base_has_selections": True, "base_excludes": ["No se traban"]},
                "text": "Para cada uno que seleccionaste:",
                "frequency_options": ["Diario", "Varias veces por semana", "Semanal", "Mensual", "Rara vez"],
                "severity_options": [
                    "Bajo (molestia menor)",
                    "Medio (retrasa el trabajo)",
                    "Alto (frena la operación)",
                    "Crítico (perdemos plata o clientes)",
                ],
            },
            {
                "id": "G4_L2",
                "type": "ranking_from_selected",
                "condition": {"base_selection_count_gte": 3, "base_excludes": ["No se traban"]},
                "text": "De los que seleccionaste, ¿cuáles son los 3 peores? Ordénalos.",
                "max_items": 3,
            },
        ],
    },
    # ── G5 — Flujo de información ─────────────────────────────────────────
    {
        "id": "G5",
        "title": "Flujo de información",
        "dimension": "flujo_informacion",
        "base": {
            "text": "¿Cómo te enteras de lo que pasa en las diferentes áreas de tu negocio?",
            "type": "multi_select",
            "options": [
                "Reportes o dashboards",
                "Mi equipo me informa por WhatsApp o llamadas",
                "Me entero cuando hay un problema",
                "Reuniones periódicas",
                "Yo mismo reviso todo",
                "No tengo buena visibilidad",
            ],
        },
        "layers": [
            {
                "id": "G5_L1",
                "type": "numeric_select",
                "condition": {"base_excludes_all": ["Reportes o dashboards"]},
                "text": "¿Cuántas horas a la semana dedicas a buscar información?",
                "options": ["Menos de 1", "1–3", "3–5", "5–10", "Más de 10"],
            },
        ],
    },
    # ── G6 — Incentivos y colaboración ────────────────────────────────────
    {
        "id": "G6",
        "title": "Incentivos y colaboración",
        "dimension": "incentivos",
        "base": {
            "text": "Cuando alguien de tu equipo ayuda a otra área, ¿eso le beneficia o le quita tiempo?",
            "type": "single_select",
            "options": [
                "Le beneficia — está reconocido",
                "Se valora informalmente",
                "Ni beneficia ni perjudica",
                "Le perjudica",
                "No sé cómo lo percibe mi equipo",
            ],
        },
        "layers": [],
    },
    # ── G7 — Cultura de error ─────────────────────────────────────────────
    {
        "id": "G7",
        "title": "Cultura de error",
        "dimension": "cultura_error",
        "base": {
            "text": "Cuando alguien de tu equipo comete un error, ¿qué pasa normalmente?",
            "type": "single_select",
            "options": [
                "Se analiza y se ajusta el proceso",
                "Se corrige y se sigue",
                "Se le llama la atención",
                "Depende del error y de quién",
                "Me entero tarde o no me entero",
            ],
        },
        "layers": [
            {
                "id": "G7_L1",
                "type": "text_short",
                "condition": {"always": True},
                "text": "¿Cuál fue el último error que recuerdes? ¿Qué pasó?",
            },
        ],
    },
    # ── G8 — Alineación estratégica ───────────────────────────────────────
    {
        "id": "G8",
        "title": "Alineación estratégica",
        "dimension": "alineacion_estrategica",
        "base": {
            "text": "Si le preguntaras a cualquier persona de tu equipo 'qué hace diferente a esta empresa', ¿crees que sabrían responder?",
            "type": "single_select",
            "options": [
                "Sí, todos tienen claro",
                "Algunos sí, otros no",
                "Probablemente no sabrían",
                "No estoy seguro de que yo mismo lo tenga claro",
                "No tenemos un diferencial claro",
            ],
        },
        "layers": [],
    },
    # ── G9 — Amenazas externas ────────────────────────────────────────────
    {
        "id": "G9",
        "title": "Amenazas externas",
        "dimension": "alineacion_estrategica",
        "base": {
            "text": "¿Qué cambio de afuera te preocupa más para tu negocio en los próximos 12 meses?",
            "type": "single_select",
            "options": [
                "Competencia",
                "Clientes cambiando",
                "Tecnología",
                "Costos y márgenes",
                "Regulación",
                "No veo amenazas claras",
            ],
        },
        "layers": [],
    },
    # ── G10 — Capacidad de cambio ─────────────────────────────────────────
    {
        "id": "G10",
        "title": "Capacidad de cambio",
        "dimension": "capacidad_cambio",
        "base": {
            "text": "La última vez que intentaste cambiar algo importante, ¿qué pasó?",
            "type": "single_select",
            "options": [
                "Funcionó y se mantuvo",
                "Funcionó al principio pero volvimos a lo de antes",
                "Costó mucho pero se logró",
                "No funcionó",
                "No he intentado cambios importantes",
            ],
        },
        "layers": [],
    },
    # ── G11 — Visibilidad financiera ──────────────────────────────────────
    {
        "id": "G11",
        "title": "Visibilidad financiera",
        "dimension": "visibilidad_financiera",
        "base": {
            "text": "¿Sabes hoy cuál de tus áreas, productos o sedes es la más rentable y cuál la menos?",
            "type": "single_select",
            "options": [
                "Sí, con datos concretos",
                "Tengo idea aproximada sin datos exactos",
                "No lo sé con certeza",
                "Solo tengo una sede, no aplica",
            ],
        },
        "layers": [
            {
                "id": "G11_L1",
                "type": "numeric_input",
                "condition": {"base_answer_index_not": 3},
                "text": "¿Cuántas sedes, líneas de negocio o áreas de ingreso tienes?",
            },
        ],
    },
    # ── G12 — Presión de caja ─────────────────────────────────────────────
    {
        "id": "G12",
        "title": "Presión de caja",
        "dimension": "visibilidad_financiera",
        "base": {
            "text": "En los últimos 6 meses, ¿has tenido momentos donde la plata no alcanza para cubrir la operación?",
            "type": "single_select",
            "options": [
                "Nunca",
                "Una o dos veces",
                "Varias veces — tensión recurrente",
                "Es constante",
                "Prefiero no responder",
            ],
        },
        "layers": [
            {
                "id": "G12_L1",
                "type": "single_select",
                "condition": {"base_answer_index_gte": 2, "base_answer_index_not": 4},
                "text": "¿Cómo financias la operación cuando no alcanza?",
                "options": [
                    "Crédito bancario",
                    "Tarjeta de crédito personal",
                    "Plata del dueño",
                    "Retraso pagos a proveedores",
                    "Otro",
                ],
            },
        ],
    },
    # ── G13 — Pregunta abierta ────────────────────────────────────────────
    {
        "id": "G13",
        "title": "Pregunta abierta",
        "dimension": "capacidad_cambio",
        "base": {
            "text": "Si pudieras cambiar una sola cosa de cómo opera tu negocio hoy, ¿cuál sería?",
            "type": "text_open",
            "options": [],
        },
        "layers": [],
    },
]


# ══════════════════════════════════════════════════════════════════════════════
# PREGUNTAS DEL EMPLEADO (10 base)
# ══════════════════════════════════════════════════════════════════════════════

EMPLOYEE_QUESTIONS: list[dict] = [
    # ── E1 — Tiempo del jefe (par G1) ─────────────────────────────────────
    {
        "id": "E1",
        "title": "Tiempo del jefe",
        "dimension": "centralizacion",
        "paired_with": "G1",
        "base": {
            "text": "¿Tu jefe dedica su tiempo a decisiones importantes o se la pasa resolviendo cosas del día a día?",
            "type": "single_select",
            "options": [
                "Se enfoca en lo estratégico",
                "Hace de todo un poco",
                "Se la pasa apagando incendios",
                "No sé en qué se le va el tiempo",
            ],
        },
        "layers": [],
    },
    # ── E2 — Ausencia del jefe (par G2) ───────────────────────────────────
    {
        "id": "E2",
        "title": "Ausencia del jefe",
        "dimension": "centralizacion",
        "paired_with": "G2",
        "base": {
            "text": "Cuando tu jefe no está o no contesta, ¿qué pasa con el trabajo?",
            "type": "single_select",
            "options": [
                "Todo sigue normal",
                "Algunas cosas se retrasan",
                "Varias cosas quedan paradas",
                "Casi todo se frena",
                "Nunca pasa, siempre está disponible",
            ],
        },
        "layers": [
            {
                "id": "E2_L1",
                "type": "text_short",
                "condition": {"always": True},
                "text": "¿Qué fue lo último que quedó parado por no poder consultar a tu jefe?",
            },
        ],
    },
    # ── E3 — Autonomía real (par G3) ──────────────────────────────────────
    {
        "id": "E3",
        "title": "Autonomía real",
        "dimension": "centralizacion",
        "paired_with": "G3",
        "base": {
            "text": "¿Cuáles de estas cosas puedes decidir SIN pedirle permiso a tu jefe?",
            "type": "multi_select",
            "options": [
                "Ofrecer descuentos",
                "Resolver quejas de clientes",
                "Compras menores",
                "Cambiar un proceso",
                "Contratar ayuda temporal",
                "Negociar con proveedor",
                "Ninguna",
            ],
        },
        "layers": [],
    },
    # ── E4 — Cuellos de botella (par G4) ──────────────────────────────────
    {
        "id": "E4",
        "title": "Cuellos de botella",
        "dimension": "cuellos_botella",
        "paired_with": "G4",
        "base": {
            "text": "¿Dónde se traban las cosas más seguido en tu trabajo?",
            "type": "multi_select",
            "options": [
                "Aprobaciones que dependen de mi jefe",
                "Coordinación entre áreas o sedes",
                "Falta de información",
                "Falta de herramientas",
                "Errores y retrabajo",
                "Proveedores",
                "Falta de personal",
                "No se traban",
            ],
        },
        "layers": [
            {
                "id": "E4_L1",
                "type": "gradient_per_selection",
                "condition": {"base_has_selections": True, "base_excludes": ["No se traban"]},
                "text": "Para cada uno que seleccionaste:",
                "frequency_options": ["Diario", "Varias veces por semana", "Semanal", "Mensual", "Rara vez"],
                "severity_options": [
                    "Bajo (molestia menor)",
                    "Medio (retrasa el trabajo)",
                    "Alto (frena la operación)",
                    "Crítico (perdemos plata o clientes)",
                ],
            },
            {
                "id": "E4_L2",
                "type": "numeric_input",
                "condition": {"always": True},
                "text": "¿Cuántas veces la semana pasada tuviste que esperar una aprobación para avanzar?",
            },
        ],
    },
    # ── E5 — Flujo de información (par G5) ────────────────────────────────
    {
        "id": "E5",
        "title": "Flujo de información",
        "dimension": "flujo_informacion",
        "paired_with": "G5",
        "base": {
            "text": "Cuando necesitas información para hacer tu trabajo, ¿cómo la consigues?",
            "type": "single_select",
            "options": [
                "Disponible en sistema",
                "Le pregunto a mi jefe o compañero",
                "Busco por mi cuenta",
                "Trabajo sin info completa",
                "No sé dónde encontrarla",
            ],
        },
        "layers": [
            {
                "id": "E5_L1",
                "type": "numeric_select",
                "condition": {"always": True},
                "text": "¿Cuántas horas a la semana pierdes buscando información?",
                "options": ["Menos de 1", "1–3", "3–5", "5–10", "Más de 10"],
            },
        ],
    },
    # ── E6 — Incentivos (par G6) ──────────────────────────────────────────
    {
        "id": "E6",
        "title": "Incentivos",
        "dimension": "incentivos",
        "paired_with": "G6",
        "base": {
            "text": "Cuando ayudas a un compañero o a otra área, ¿qué pasa?",
            "type": "single_select",
            "options": [
                "Me lo reconocen",
                "Se valora informalmente",
                "Nadie se da cuenta",
                "Me quita tiempo",
                "Prefiero no ayudar",
            ],
        },
        "layers": [],
    },
    # ── E7 — Cultura de error (par G7) ────────────────────────────────────
    {
        "id": "E7",
        "title": "Cultura de error",
        "dimension": "cultura_error",
        "paired_with": "G7",
        "base": {
            "text": "Cuando cometes un error en tu trabajo, ¿qué pasa?",
            "type": "single_select",
            "options": [
                "Se analiza y se busca evitarlo",
                "Se corrige y no pasa nada",
                "Me llaman la atención",
                "Depende de si es visible",
                "Prefiero no reportar errores",
            ],
        },
        "layers": [],
    },
    # ── E8 — Alineación estratégica (par G8) ──────────────────────────────
    {
        "id": "E8",
        "title": "Alineación estratégica",
        "dimension": "alineacion_estrategica",
        "paired_with": "G8",
        "base": {
            "text": "Si alguien te preguntara qué hace diferente a esta empresa, ¿sabrías qué responder?",
            "type": "single_select",
            "options": [
                "Sí, lo tengo claro",
                "Más o menos",
                "No sabría qué decir",
                "Nunca me lo han explicado",
                "No tenemos diferencial claro",
            ],
        },
        "layers": [],
    },
    # ── E9 — Amenazas externas (par G9) ───────────────────────────────────
    {
        "id": "E9",
        "title": "Amenazas externas",
        "dimension": "alineacion_estrategica",
        "paired_with": "G9",
        "base": {
            "text": "¿Has notado cambios en lo que piden los clientes, en la competencia, o en algo de afuera?",
            "type": "multi_select",
            "options": [
                "Clientes piden cosas diferentes",
                "Competencia hace cosas que nosotros no",
                "Costos suben",
                "Tecnología cambia",
                "No he notado cambios",
                "No tengo visibilidad",
            ],
        },
        "layers": [],
    },
    # ── E10 — Pregunta abierta (par G13) ──────────────────────────────────
    {
        "id": "E10",
        "title": "Pregunta abierta",
        "dimension": "capacidad_cambio",
        "paired_with": "G13",
        "base": {
            "text": "Si pudieras cambiar una sola cosa de cómo funciona esta empresa, ¿cuál sería?",
            "type": "text_open",
            "options": [],
        },
        "layers": [],
    },
]


# ══════════════════════════════════════════════════════════════════════════════
# PREGUNTAS ADAPTATIVAS (banco — el sistema selecciona 3 según hipótesis)
# ══════════════════════════════════════════════════════════════════════════════

ADAPTIVE_QUESTIONS: list[dict] = [
    {
        "id": "A1",
        "title": "Centralización oculta",
        "hypothesis": "centralizacion_oculta",
        "dimension": "centralizacion",
        "activation_rule": {"question": "G2", "answer_index": 0},
        "base": {
            "text": "¿Qué pasó la última vez que tu jefe no respondió en 2 horas? ¿Qué hiciste?",
            "type": "text_short",
            "options": [],
        },
        "layers": [],
    },
    {
        "id": "A2",
        "title": "Autonomía inflada",
        "hypothesis": "autonomia_inflada",
        "dimension": "centralizacion",
        "activation_rule": {"question": "G3", "selected_count_gte": 5},
        "base": {
            "text": "¿Cuál fue la última decisión importante que tomaste sin consultar a tu jefe?",
            "type": "text_short",
            "options": [],
        },
        "layers": [
            {
                "id": "A2_L1",
                "type": "text_short",
                "condition": {"always": True},
                "text": "¿Y la última que tuviste que escalar?",
            },
        ],
    },
    {
        "id": "A3",
        "title": "Info no fluye",
        "hypothesis": "info_no_fluye",
        "dimension": "flujo_informacion",
        "activation_rule": {"question": "G5", "excludes_all": ["Reportes o dashboards"]},
        "base": {
            "text": "¿Qué hiciste ayer que dependía de información de otra persona? ¿Cuánto esperaste?",
            "type": "text_short",
            "options": [],
        },
        "layers": [
            {
                "id": "A3_L1",
                "type": "numeric_input",
                "condition": {"always": True},
                "text": "Horas de espera aproximadas:",
            },
        ],
    },
    {
        "id": "A4",
        "title": "Incentivos ciegos",
        "hypothesis": "incentivos_ciegos",
        "dimension": "incentivos",
        "activation_rule": {"question": "G6", "answer_index": 4},
        "base": {
            "text": "¿Qué tan frustrante es hacer tu trabajo hoy?",
            "type": "scale_1_5",
            "options": ["1 — Nada", "2", "3", "4", "5 — Muy frustrante"],
        },
        "layers": [
            {
                "id": "A4_L1",
                "type": "text_short",
                "condition": {"always": True},
                "text": "¿Qué es lo que más te frustra?",
            },
        ],
    },
    {
        "id": "A5",
        "title": "Errores ocultos",
        "hypothesis": "errores_ocultos",
        "dimension": "cultura_error",
        "activation_rule": {"question": "G7", "answer_index": 4},
        "base": {
            "text": "¿En el último mes, cuántas veces pasó algo mal que nadie reportó oficialmente?",
            "type": "numeric_input",
            "options": [],
        },
        "layers": [],
    },
    {
        "id": "A6",
        "title": "Desconexión financiera",
        "hypothesis": "desconexion_financiera",
        "dimension": "visibilidad_financiera",
        "activation_rule": {"question": "G11", "answer_index": 2},
        "base": {
            "text": "¿Sabes cuánto vende tu área/tienda al mes? ¿Sabes si eso es bueno o malo comparado con las demás?",
            "type": "single_select",
            "options": [
                "Sí con número",
                "Sí sin número",
                "No sé",
            ],
        },
        "layers": [],
    },
    {
        "id": "A7",
        "title": "Restricción llega abajo",
        "hypothesis": "restriccion_llega_abajo",
        "dimension": "visibilidad_financiera",
        "activation_rule": {"question": "G12", "answer_index_gte": 2, "answer_index_not": 4},
        "base": {
            "text": "En el último mes, ¿te faltó algo para hacer tu trabajo que no se compró por falta de presupuesto?",
            "type": "single_select",
            "options": ["Sí", "No"],
        },
        "layers": [
            {
                "id": "A7_L1",
                "type": "text_short",
                "condition": {"base_answer_index": 0},
                "text": "¿Qué fue lo que faltó?",
            },
        ],
    },
]


# ══════════════════════════════════════════════════════════════════════════════
# REGLAS DE HIPÓTESIS
# ══════════════════════════════════════════════════════════════════════════════

HYPOTHESIS_RULES: dict[str, dict] = {
    "centralizacion_oculta": {
        "trigger_question": "G2",
        "trigger_condition": "answer_index == 0",
        "description": "El gerente dice que todo funciona sin él, pero ¿es realmente así?",
    },
    "autonomia_inflada": {
        "trigger_question": "G3",
        "trigger_condition": "selected_count >= 5",
        "description": "El gerente dice que delega mucho, pero ¿los empleados lo perciben igual?",
    },
    "info_no_fluye": {
        "trigger_question": "G5",
        "trigger_condition": "not selected('Reportes o dashboards')",
        "description": "No hay sistemas formales de información — ¿cuánto tiempo se pierde?",
    },
    "incentivos_ciegos": {
        "trigger_question": "G6",
        "trigger_condition": "answer_index == 4",
        "description": "El gerente no sabe cómo percibe su equipo la colaboración.",
    },
    "errores_ocultos": {
        "trigger_question": "G7",
        "trigger_condition": "answer_index == 4",
        "description": "El gerente se entera tarde de los errores — ¿cuántos no se reportan?",
    },
    "desconexion_financiera": {
        "trigger_question": "G11",
        "trigger_condition": "answer_index == 2",
        "description": "No hay visibilidad financiera por área — ¿llega eso al equipo?",
    },
    "restriccion_llega_abajo": {
        "trigger_question": "G12",
        "trigger_condition": "answer_index >= 2 and answer_index != 4",
        "description": "Hay presión de caja recurrente — ¿impacta la operación diaria del equipo?",
    },
}


# ══════════════════════════════════════════════════════════════════════════════
# SUBCONJUNTO FREE (para flujo sin auth — onboarding)
# Usa solo las capas base de G1-G4 (gerente) y E1-E4 (empleado)
# ══════════════════════════════════════════════════════════════════════════════

FREE_MANAGER_QUESTION_IDS = ["G1", "G2", "G3", "G4"]
FREE_EMPLOYEE_QUESTION_IDS = ["E1", "E2", "E3", "E4"]

FREE_MANAGER_QUESTIONS = [q for q in MANAGER_QUESTIONS if q["id"] in FREE_MANAGER_QUESTION_IDS]
FREE_EMPLOYEE_QUESTIONS = [q for q in EMPLOYEE_QUESTIONS if q["id"] in FREE_EMPLOYEE_QUESTION_IDS]

# Dimensions used in free flow (subset)
FREE_DIMENSIONS_V2 = {
    "centralizacion": "Centralización",
    "cuellos_botella": "Cuellos de botella",
}

# All question IDs for validation
ALL_MANAGER_IDS = {q["id"] for q in MANAGER_QUESTIONS}
ALL_EMPLOYEE_IDS = {q["id"] for q in EMPLOYEE_QUESTIONS}
ALL_ADAPTIVE_IDS = {q["id"] for q in ADAPTIVE_QUESTIONS}
ALL_QUESTION_IDS = ALL_MANAGER_IDS | ALL_EMPLOYEE_IDS | ALL_ADAPTIVE_IDS

# Question lookup by ID
QUESTION_BY_ID: dict[str, dict] = {}
for q in MANAGER_QUESTIONS + EMPLOYEE_QUESTIONS + ADAPTIVE_QUESTIONS:
    QUESTION_BY_ID[q["id"]] = q


# ══════════════════════════════════════════════════════════════════════════════
# SECTIONS — grouped by dimension for UI display
# ══════════════════════════════════════════════════════════════════════════════

def build_sections(questions: list[dict]) -> list[dict]:
    """Group questions by dimension for sectioned display."""
    by_dim: dict[str, list[dict]] = {}
    for q in questions:
        dim = q["dimension"]
        by_dim.setdefault(dim, []).append(q)

    return [
        {
            "dimension": dim_id,
            "label": DIMENSIONS_V2.get(dim_id, dim_id),
            "questions": qs,
        }
        for dim_id, qs in by_dim.items()
    ]


MANAGER_SECTIONS = build_sections(MANAGER_QUESTIONS)
EMPLOYEE_SECTIONS = build_sections(EMPLOYEE_QUESTIONS)
