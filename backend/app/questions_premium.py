"""
Banco de preguntas premium — 8 dimensiones.
Cada dimensión: 3-5 Likert + 1 abierta + 1 selección múltiple.
"""

PREMIUM_DIMENSIONS = {
    "liderazgo": "Liderazgo",
    "comunicacion": "Comunicación",
    "cultura": "Cultura",
    "procesos": "Procesos",
    "poder": "Poder",
    "economia": "Economía y Finanzas",
    "operacion": "Operación",
    "mision": "Misión",
}

PREMIUM_QUESTIONS: list[dict] = [
    # ══════════════════════════════════════════════════
    # LIDERAZGO
    # ══════════════════════════════════════════════════
    {
        "id": "p_lid_01", "dimension": "liderazgo", "tipo": "likert",
        "texto": "Las decisiones importantes se toman de forma oportuna.",
    },
    {
        "id": "p_lid_02", "dimension": "liderazgo", "tipo": "likert",
        "texto": "Los líderes comunican con claridad la dirección de la organización.",
    },
    {
        "id": "p_lid_03", "dimension": "liderazgo", "tipo": "likert",
        "texto": "Los líderes son accesibles cuando se necesita su orientación.",
    },
    {
        "id": "p_lid_04", "dimension": "liderazgo", "tipo": "likert",
        "texto": "Confío en las decisiones que toman los líderes de esta organización.",
    },
    {
        "id": "p_lid_05", "dimension": "liderazgo", "tipo": "abierta",
        "texto": "¿Quién crees que toma las decisiones más importantes aquí? ¿Por qué?",
    },
    {
        "id": "p_lid_06", "dimension": "liderazgo", "tipo": "seleccion_multiple",
        "texto": "¿Qué cualidades describes en los líderes de esta organización?",
        "opciones": ["Visionarios", "Accesibles", "Decisivos", "Empáticos", "Desconectados", "Autoritarios", "Ausentes"],
    },

    # ══════════════════════════════════════════════════
    # COMUNICACIÓN
    # ══════════════════════════════════════════════════
    {
        "id": "p_com_01", "dimension": "comunicacion", "tipo": "likert",
        "texto": "La información fluye de manera clara entre las áreas.",
    },
    {
        "id": "p_com_02", "dimension": "comunicacion", "tipo": "likert",
        "texto": "Las personas saben a quién acudir cuando tienen dudas.",
    },
    {
        "id": "p_com_03", "dimension": "comunicacion", "tipo": "likert",
        "texto": "Los canales de comunicación internos son efectivos.",
    },
    {
        "id": "p_com_04", "dimension": "comunicacion", "tipo": "abierta",
        "texto": "Describe una situación reciente donde la falta de comunicación generó un problema.",
    },
    {
        "id": "p_com_05", "dimension": "comunicacion", "tipo": "seleccion_multiple",
        "texto": "¿Cuáles son los principales canales de comunicación en tu día a día?",
        "opciones": ["Reuniones presenciales", "Videollamadas", "Email", "Chat/Slack", "Documentos compartidos", "Conversaciones informales", "No hay canales claros"],
    },

    # ══════════════════════════════════════════════════
    # CULTURA
    # ══════════════════════════════════════════════════
    {
        "id": "p_cul_01", "dimension": "cultura", "tipo": "likert",
        "texto": "Existe confianza entre los miembros del equipo.",
    },
    {
        "id": "p_cul_02", "dimension": "cultura", "tipo": "likert",
        "texto": "Los valores de la organización se reflejan en las decisiones del día a día.",
    },
    {
        "id": "p_cul_03", "dimension": "cultura", "tipo": "likert",
        "texto": "Me siento seguro(a) expresando opiniones diferentes a las de mis superiores.",
    },
    {
        "id": "p_cul_04", "dimension": "cultura", "tipo": "abierta",
        "texto": "¿Hay cosas que 'todos saben que se hacen así' aunque no estén escritas? Describe la más importante.",
    },
    {
        "id": "p_cul_05", "dimension": "cultura", "tipo": "seleccion_multiple",
        "texto": "¿Qué palabras describen mejor la cultura de esta organización?",
        "opciones": ["Colaborativa", "Competitiva", "Innovadora", "Burocrática", "Familiar", "Jerárquica", "Flexible", "Rígida"],
    },

    # ══════════════════════════════════════════════════
    # PROCESOS
    # ══════════════════════════════════════════════════
    {
        "id": "p_pro_01", "dimension": "procesos", "tipo": "likert",
        "texto": "Los procesos internos están documentados y son claros.",
    },
    {
        "id": "p_pro_02", "dimension": "procesos", "tipo": "likert",
        "texto": "Cuando un proceso no funciona, se mejora de forma oportuna.",
    },
    {
        "id": "p_pro_03", "dimension": "procesos", "tipo": "likert",
        "texto": "Las responsabilidades de cada rol están bien definidas.",
    },
    {
        "id": "p_pro_04", "dimension": "procesos", "tipo": "abierta",
        "texto": "Describe un proceso de tu trabajo diario que sientes que podría ser más rápido o simple.",
    },
    {
        "id": "p_pro_05", "dimension": "procesos", "tipo": "seleccion_multiple",
        "texto": "¿Dónde se generan los principales cuellos de botella?",
        "opciones": ["Aprobaciones", "Falta de información", "Herramientas inadecuadas", "Coordinación entre áreas", "Falta de recursos", "Cambio de prioridades", "No hay cuellos de botella"],
    },

    # ══════════════════════════════════════════════════
    # PODER
    # ══════════════════════════════════════════════════
    {
        "id": "p_pod_01", "dimension": "poder", "tipo": "likert",
        "texto": "Las decisiones se toman en los niveles apropiados de la organización.",
    },
    {
        "id": "p_pod_02", "dimension": "poder", "tipo": "likert",
        "texto": "Tengo suficiente autonomía para hacer bien mi trabajo.",
    },
    {
        "id": "p_pod_03", "dimension": "poder", "tipo": "likert",
        "texto": "La distribución de poder refleja las necesidades de la organización.",
    },
    {
        "id": "p_pod_04", "dimension": "poder", "tipo": "abierta",
        "texto": "¿Hay alguien cuya aprobación es necesaria para que las cosas avancen, aunque no sea su responsabilidad formal?",
    },
    {
        "id": "p_pod_05", "dimension": "poder", "tipo": "seleccion_multiple",
        "texto": "¿Qué tipo de poder es más influyente en esta organización?",
        "opciones": ["Cargo formal", "Antigüedad", "Conocimiento técnico", "Relaciones personales", "Control de recursos", "Carisma", "Información privilegiada"],
    },

    # ══════════════════════════════════════════════════
    # ECONOMÍA Y FINANZAS
    # ══════════════════════════════════════════════════
    {
        "id": "p_eco_01", "dimension": "economia", "tipo": "likert",
        "texto": "Los recursos se distribuyen de manera justa entre las áreas.",
    },
    {
        "id": "p_eco_02", "dimension": "economia", "tipo": "likert",
        "texto": "Siento que mi esfuerzo y contribución se reconocen de forma justa.",
    },
    {
        "id": "p_eco_03", "dimension": "economia", "tipo": "likert",
        "texto": "Los incentivos están alineados con los objetivos de la organización.",
    },
    {
        "id": "p_eco_04", "dimension": "economia", "tipo": "abierta",
        "texto": "¿Qué comportamientos se reconocen o recompensan realmente aquí, aunque no sean los declarados oficialmente?",
    },
    {
        "id": "p_eco_05", "dimension": "economia", "tipo": "seleccion_multiple",
        "texto": "¿Qué tipo de reconocimiento valoras más?",
        "opciones": ["Compensación económica", "Reconocimiento público", "Oportunidades de crecimiento", "Flexibilidad", "Autonomía", "Feedback directo", "Ninguno es efectivo aquí"],
    },

    # ══════════════════════════════════════════════════
    # OPERACIÓN
    # ══════════════════════════════════════════════════
    {
        "id": "p_ope_01", "dimension": "operacion", "tipo": "likert",
        "texto": "Los procesos internos permiten trabajar de forma eficiente.",
    },
    {
        "id": "p_ope_02", "dimension": "operacion", "tipo": "likert",
        "texto": "Cuando algo falla, existe un mecanismo claro para resolverlo.",
    },
    {
        "id": "p_ope_03", "dimension": "operacion", "tipo": "likert",
        "texto": "Las herramientas y tecnología que usamos son adecuadas para nuestro trabajo.",
    },
    {
        "id": "p_ope_04", "dimension": "operacion", "tipo": "abierta",
        "texto": "¿Con qué frecuencia tienes que esperar a otra persona o área para avanzar? Describe un ejemplo reciente.",
    },
    {
        "id": "p_ope_05", "dimension": "operacion", "tipo": "seleccion_multiple",
        "texto": "¿Cuáles son los principales desafíos operativos?",
        "opciones": ["Falta de personal", "Herramientas obsoletas", "Procesos manuales", "Falta de capacitación", "Sobrecarga de trabajo", "Coordinación deficiente", "Todo funciona bien"],
    },

    # ══════════════════════════════════════════════════
    # MISIÓN
    # ══════════════════════════════════════════════════
    {
        "id": "p_mis_01", "dimension": "mision", "tipo": "likert",
        "texto": "Conozco y entiendo la misión de esta organización.",
    },
    {
        "id": "p_mis_02", "dimension": "mision", "tipo": "likert",
        "texto": "Mi trabajo contribuye directamente a los objetivos estratégicos.",
    },
    {
        "id": "p_mis_03", "dimension": "mision", "tipo": "likert",
        "texto": "La organización está avanzando en la dirección correcta.",
    },
    {
        "id": "p_mis_04", "dimension": "mision", "tipo": "abierta",
        "texto": "Si pudieras cambiar una sola cosa de cómo funciona esta organización, ¿qué cambiarías y por qué?",
    },
    {
        "id": "p_mis_05", "dimension": "mision", "tipo": "seleccion_multiple",
        "texto": "¿Qué tan alineado sientes que está tu equipo con la misión?",
        "opciones": ["Totalmente alineado", "Mayormente alineado", "Parcialmente", "Poco alineado", "Cada quien va por su lado"],
    },
]

PREMIUM_QUESTION_IDS = {q["id"] for q in PREMIUM_QUESTIONS}

# Group questions by dimension for sectioned display
PREMIUM_SECTIONS: list[dict] = [
    {
        "dimension": dim_id,
        "label": label,
        "questions": [q for q in PREMIUM_QUESTIONS if q["dimension"] == dim_id],
    }
    for dim_id, label in PREMIUM_DIMENSIONS.items()
]
