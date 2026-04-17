"""
Banco de preguntas para el plan Free.
4 dimensiones, 2 preguntas Likert (1-5) por dimensión.
"""

FREE_QUESTIONS: list[dict] = [
    # ── Liderazgo ──
    {
        "id": "free_lid_01",
        "dimension": "liderazgo",
        "texto": "Las decisiones importantes se toman de forma oportuna en esta organización.",
        "tipo": "likert",
    },
    {
        "id": "free_lid_02",
        "dimension": "liderazgo",
        "texto": "Los líderes son accesibles cuando se necesita su orientación.",
        "tipo": "likert",
    },
    # ── Comunicación ──
    {
        "id": "free_com_01",
        "dimension": "comunicacion",
        "texto": "La información fluye de manera clara entre las áreas de la organización.",
        "tipo": "likert",
    },
    {
        "id": "free_com_02",
        "dimension": "comunicacion",
        "texto": "Las personas saben a quién acudir cuando tienen dudas sobre su trabajo.",
        "tipo": "likert",
    },
    # ── Cultura ──
    {
        "id": "free_cul_01",
        "dimension": "cultura",
        "texto": "Existe confianza entre los miembros del equipo.",
        "tipo": "likert",
    },
    {
        "id": "free_cul_02",
        "dimension": "cultura",
        "texto": "Los valores de la organización se reflejan en las decisiones del día a día.",
        "tipo": "likert",
    },
    # ── Operación ──
    {
        "id": "free_op_01",
        "dimension": "operacion",
        "texto": "Los procesos internos permiten trabajar de forma eficiente.",
        "tipo": "likert",
    },
    {
        "id": "free_op_02",
        "dimension": "operacion",
        "texto": "Cuando algo falla, existe un mecanismo claro para resolverlo.",
        "tipo": "likert",
    },
]

FREE_DIMENSIONS = {
    "liderazgo": "Liderazgo",
    "comunicacion": "Comunicación",
    "cultura": "Cultura",
    "operacion": "Operación",
}

FREE_QUESTION_IDS = {q["id"] for q in FREE_QUESTIONS}
