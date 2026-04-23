# Visión de Producto — Canvas como sistema nervioso
## Documento de horizonte post-Sprint 5.C

> Escrito por Martín Guzmán (PM), abril 2026, antes
> de la validación externa. Este documento NO es
> spec de implementación. Es norte de producto para
> decisiones post-pilot.

---

## Lo que el canvas actual ya resuelve bien

Hay una intuición de diseño muy correcta en lo que
existe: el organigrama no es decoración, es el índice
del diagnóstico. Cada nodo no solo representa un rol
—es el punto de entrada a su entrevista, y el punto
de salida hacia sus hallazgos. Eso es más inteligente
de lo que parece, porque convierte la estructura
formal en el esqueleto sobre el cual se cuelga todo
lo demás.

El flujo Estructura → Recolección → Análisis →
Resultados es limpio. Pero tiene un problema
fundamental: es lineal y terminal. El diagnóstico
llega al final como un evento, no como un estado
continuo. Y eso contradice exactamente lo que el
Laboratorio quiere ser.

## El insight central: el canvas como plano dual

El salto de genio no está en agregar pantallas. Está
en convertir el mismo canvas en dos capas simultáneas
que el usuario puede alternar.

**Capa Formal** — lo que existe hoy: el organigrama
que el usuario dibuja. Nodos, jerarquías, relaciones
oficiales.

**Capa Real** — lo que emerge de las entrevistas: el
mismo canvas, pero donde el grosor de las conexiones
representa frecuencia de interacción real, el color
de los nodos representa nivel de fricción o
alineación, y aparecen conexiones que no existen en
el organigrama pero sí en la práctica.

El usuario no dibuja la Capa Real. La IA la construye
sola a partir de las respuestas de las entrevistas.
El usuario solo tiene que hacer la pregunta correcta
en cada entrevista —"¿con quién resuelves realmente
los problemas de tu área?"— y el canvas se reescribe
solo.

Cuando el usuario alterna entre capas, la brecha
formal/real se vuelve visible de golpe. No como texto
en un reporte, sino como geometría: conexiones que
aparecen, conexiones que desaparecen, nodos que se
achican o se agrandan. La brecha no se lee, se ve.

## La segunda evolución: el canvas como sala de situación

Hoy el canvas es estático después de que termina la
recolección. La evolución es que el canvas respira.

Cada hallazgo del diagnóstico tiene un nodo origen
—los nodos que lo alimentan están marcados en el
canvas. Eso ya existe ("Ver en el mapa →"). Pero
puede ir mucho más lejos: cuando el usuario
implementa una recomendación y la marca como en
progreso, los nodos afectados cambian de estado
visualmente. El canvas deja de ser el mapa del
pasado y se convierte en el tablero del presente.

Esto resuelve el problema de retención de raíz. El
usuario no vuelve a la plataforma a "ver el
diagnóstico". Vuelve porque el canvas es el lugar
donde vive el estado real de su organización.

## La tercera evolución: el nodo como unidad de inteligencia acumulada

Hoy un nodo tiene: nombre del rol, miembros,
descripción, contexto. Eso es un formulario.

En el horizonte, un nodo es un repositorio de
inteligencia longitudinal. Contiene la entrevista
original, las respuestas clave, los hallazgos que lo
involucran, las recomendaciones que le aplican, y
—cuando hay re-diagnósticos— la evolución de ese
nodo en el tiempo. ¿Este rol se volvió más central o
más periférico? ¿La fricción que se detectó hace seis
meses mejoró o empeoró?

Cuando haces clic en un nodo, no abres un formulario.
Abres la historia de ese punto del sistema.

## La cuarta evolución: el canvas predictivo

Este es el más ambicioso y el que más tarda, pero
vale fijarlo como norte.

Con suficientes datos —de esta organización y de
otras— la plataforma puede detectar patrones de
riesgo antes de que se materialicen. Un nodo con
alta centralidad, entrevista que revela saturación,
y sin conexiones laterales fuertes es un cuello de
botella en formación. El canvas lo señala antes de
que colapse.

No como alerta genérica. Como geometría: ese nodo
empieza a parpadear suavemente. El usuario hace
clic y encuentra: "Este nodo concentra el 40% de
las decisiones críticas del área. Las últimas
respuestas sugieren sobrecarga. Si esta persona
falla o se va, estos tres procesos se detienen."

## Cómo se integra todo en la navegación actual

El flujo de cuatro pestañas no necesita romperse.
Necesita profundizarse:

- **Estructura** se vuelve el canvas dual. El usuario
  dibuja la capa formal; la IA construye la capa real
  a medida que llegan entrevistas. Desde el día uno
  ya hay algo que ver.
- **Recolección** se vuelve el motor que alimenta el
  canvas en tiempo real. Cada entrevista completada
  no solo sube el porcentaje —actualiza el canvas
  visualmente. El usuario ve cómo su organización se
  va revelando.
- **Análisis** desaparece como pestaña separada y se
  integra al canvas. Los hallazgos son capas de
  información sobre los nodos, no una pantalla
  aparte. El análisis no es un destino, es una
  dimensión del mapa.
- **Resultados** se transforma de reporte final a
  panel de seguimiento vivo. Las recomendaciones
  tienen estado. El canvas refleja ese estado. Y hay
  un índice de salud institucional —un número que
  cambia— que da razón de volver cada semana.

## La frase que lo resume

El canvas deja de ser la pantalla donde dibujas tu
organigrama antes de que empiece el diagnóstico. Se
convierte en el lugar donde tu organización existe
dentro de la plataforma —y donde puedes verla
cambiar, estancarse o mejorar en tiempo real.

Eso no es un diagnóstico organizacional. Es un
sistema nervioso digital para la organización. Y ese
es el producto que vale construir.

---

## Estado actual (referencia)

Sprint 5.C implementa la primera aproximación a
"canvas como sala de situación" — panel narrativo
sobre el canvas, hallazgos anclados a nodos,
coordinación bidireccional básica. Es Capa Formal
con diagnóstico acoplado.

Items de este documento que quedan para post-pilot:
Capa Real emergente, estado visual de
recomendaciones, nodo como repositorio longitudinal,
canvas predictivo.

La priorización de estos items se decidirá en base
al feedback del primer pilot externo.
