"""Banco de preguntas para el plan Free — 4 dimensiones, encuesta rápida.

Estructura:
- 4 dimensiones: Liderazgo, Comunicación, Cultura, Operación
- 1-2 preguntas Likert por dimensión + 1 pregunta abierta general
- Duración objetivo: ~5 min para el líder, ~5-8 min para miembros
"""

DIMENSIONS_FREE = ["liderazgo", "comunicacion", "cultura", "operacion"]

# --- Encuesta del líder (respondida por quien crea la organización) ---
LEADER_QUESTIONS: list[dict] = [
    {
        "id": "lf01",
        "dimension": "liderazgo",
        "texto": "¿Qué tan claro es para tu equipo quién toma las decisiones importantes? (1=Nada claro, 5=Muy claro)",
        "tipo": "likert",
    },
    {
        "id": "lf02",
        "dimension": "liderazgo",
        "texto": "¿Qué tan accesible eres para tu equipo cuando necesitan resolver problemas? (1=Poco accesible, 5=Muy accesible)",
        "tipo": "likert",
    },
    {
        "id": "lf03",
        "dimension": "comunicacion",
        "texto": "¿Qué tan bien fluye la información entre las diferentes áreas o personas de tu organización? (1=Muy mal, 5=Muy bien)",
        "tipo": "likert",
    },
    {
        "id": "lf04",
        "dimension": "comunicacion",
        "texto": "¿Con qué frecuencia sientes que la información importante llega tarde o incompleta? (1=Casi siempre llega tarde, 5=Casi nunca)",
        "tipo": "likert",
    },
    {
        "id": "lf05",
        "dimension": "cultura",
        "texto": "¿Qué tanto crees que los valores declarados de tu organización se practican en el día a día? (1=Nada, 5=Completamente)",
        "tipo": "likert",
    },
    {
        "id": "lf06",
        "dimension": "cultura",
        "texto": "¿Qué tan cómoda se siente tu gente para expresar desacuerdos o ideas diferentes? (1=Nada cómoda, 5=Muy cómoda)",
        "tipo": "likert",
    },
    {
        "id": "lf07",
        "dimension": "operacion",
        "texto": "¿Qué tan eficientes son los procesos de trabajo en tu organización? (1=Muy ineficientes, 5=Muy eficientes)",
        "tipo": "likert",
    },
    {
        "id": "lf08",
        "dimension": "operacion",
        "texto": "¿Con qué frecuencia se presentan cuellos de botella o bloqueos que retrasan el trabajo? (1=Muy frecuente, 5=Casi nunca)",
        "tipo": "likert",
    },
    {
        "id": "lf09",
        "dimension": "general",
        "texto": "¿Cuál es el mayor desafío que enfrenta tu organización internamente en este momento?",
        "tipo": "abierta",
    },
]

# --- Encuesta de miembros (respondida por los 3-5 invitados) ---
MEMBER_QUESTIONS: list[dict] = [
    {
        "id": "mf01",
        "dimension": "liderazgo",
        "texto": "¿Qué tan claro es para ti quién toma las decisiones importantes en tu organización? (1=Nada claro, 5=Muy claro)",
        "tipo": "likert",
    },
    {
        "id": "mf02",
        "dimension": "liderazgo",
        "texto": "¿Qué tan accesible es la dirección cuando necesitas resolver un problema? (1=Poco accesible, 5=Muy accesible)",
        "tipo": "likert",
    },
    {
        "id": "mf03",
        "dimension": "comunicacion",
        "texto": "¿Qué tan bien fluye la información que necesitas para hacer tu trabajo? (1=Muy mal, 5=Muy bien)",
        "tipo": "likert",
    },
    {
        "id": "mf04",
        "dimension": "comunicacion",
        "texto": "¿Con qué frecuencia te enteras de cosas importantes por canales informales en lugar de comunicación oficial? (1=Casi siempre informal, 5=Casi siempre oficial)",
        "tipo": "likert",
    },
    {
        "id": "mf05",
        "dimension": "cultura",
        "texto": "¿Qué tanto se practican los valores declarados de la organización en el día a día? (1=Nada, 5=Completamente)",
        "tipo": "likert",
    },
    {
        "id": "mf06",
        "dimension": "cultura",
        "texto": "¿Qué tan cómodo te sientes para expresar desacuerdos o ideas diferentes? (1=Nada cómodo, 5=Muy cómodo)",
        "tipo": "likert",
    },
    {
        "id": "mf07",
        "dimension": "operacion",
        "texto": "¿Qué tan eficientes son los procesos de trabajo en tu área? (1=Muy ineficientes, 5=Muy eficientes)",
        "tipo": "likert",
    },
    {
        "id": "mf08",
        "dimension": "operacion",
        "texto": "¿Con qué frecuencia tienes que esperar a otra persona o área para avanzar en tu trabajo? (1=Casi siempre, 5=Casi nunca)",
        "tipo": "likert",
    },
    {
        "id": "mf09",
        "dimension": "general",
        "texto": "Si pudieras cambiar una cosa de cómo funciona tu organización, ¿cuál sería?",
        "tipo": "abierta",
    },
]

__all__ = ["DIMENSIONS_FREE", "LEADER_QUESTIONS", "MEMBER_QUESTIONS"]
