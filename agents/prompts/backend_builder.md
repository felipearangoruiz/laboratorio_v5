# BackendBuilder

B# BackendBuilder — Sprint S3-1: Preguntas de entrevista

## Contexto del proyecto

- Backend FastAPI en `backend/app/`
- La tabla `interviews` ya existe con columna `data: JSONB` (guarda las respuestas)
- La tabla `members` tiene `interview_token` (unique, indexed) y `token_status` (pending/in_progress/completed/expired)
- No existe todavía un modelo de preguntas. Las preguntas son fijas para el MVP.

## Tarea

Crear `backend/app/questions.py` con las preguntas fijas del instrumento de entrevista.

Define una lista `QUESTIONS: list[dict]` donde cada elemento tiene:

```python
{
    "id": str,        # ej: "q01" — identificador único, estable, nunca cambia
    "lente": str,     # una de: "actores", "procesos", "reglas", "incentivos", "episodios"
    "texto": str,     # el texto de la pregunta que ve el encuestado
    "tipo": str,      # "abierta" | "escala_5" | "seleccion"
    "opciones": list[str]  # solo para tipo "seleccion", lista vacía en otros casos
}
```

Incluir exactamente estas 15 preguntas distribuidas en las 5 lentes (3 por lente):

**LENTE actores:**

- q01 | abierta | "¿Quién crees que toma las decisiones más importantes en esta organización? No tiene que ser la persona con el cargo más alto."
- q02 | escala_5 | "¿Qué tan accesible es la dirección para resolver problemas operativos del día a día?" (1=Nada accesible, 5=Muy accesible)
- q03 | abierta | "¿Hay alguien cuya aprobación o visto bueno es necesario para que las cosas avancen, aunque no sea su responsabilidad formal?"

**LENTE procesos:**

- q04 | abierta | "Describe un proceso de tu trabajo diario que sientes que podría ser más rápido o más simple. ¿Dónde se detiene o complica?"
- q05 | escala_5 | "¿Con qué frecuencia tienes que esperar a otra persona o área para poder avanzar en tu trabajo?" (1=Casi nunca, 5=Casi siempre)
- q06 | abierta | "¿Cuándo fue la última vez que un proceso no funcionó como se esperaba? ¿Qué pasó?"

**LENTE reglas:**

- q07 | abierta | "¿Hay reglas o procedimientos formales que en la práctica nadie sigue? ¿Por qué crees que es así?"
- q08 | abierta | "¿Hay cosas que 'todos saben que se hacen así' aunque no estén escritas en ningún lado? ¿Cuál es la más importante?"
- q09 | escala_5 | "¿Qué tan claras son las reglas sobre quién puede tomar qué decisiones?" (1=Muy confusas, 5=Muy claras)

**LENTE incentivos:**

- q10 | abierta | "¿Qué comportamientos o resultados son los que realmente se reconocen o recompensan aquí, aunque no sean los declarados oficialmente?"
- q11 | abierta | "¿Hay situaciones en las que hacer lo correcto para la organización va en contra de lo que te conviene a ti personalmente? ¿Puedes dar un ejemplo?"
- q12 | escala_5 | "¿Sientes que tu esfuerzo y contribución se reconocen de forma justa?" (1=Para nada, 5=Completamente)

**LENTE episodios:**

- q13 | abierta | "Describe una situación reciente (últimos 6 meses) en la que algo salió bien gracias a cómo está organizado el trabajo aquí."
- q14 | abierta | "Describe una situación reciente en la que algo salió mal o generó fricción innecesaria. ¿Qué lo causó?"
- q15 | abierta | "Si pudieras cambiar una sola cosa de cómo funciona esta organización, ¿qué cambiarías y por qué?"

## Reglas obligatorias

- NO crear tabla en la base de datos. Las preguntas son constantes en código.
- NO crear router ni endpoints. Solo el archivo con los datos.
- NO tocar ningún otro archivo.

## Archivos que puedes tocar

- `backend/app/questions.py` (crear)